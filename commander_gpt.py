import time
import threading
import sys
import pygame
import random
from lib.utils import read_config_file, wait_until_key
from lib.azure_speech_to_text import SpeechToTextManager
from lib.openai_chat import OpenAiManager
from lib.eleven_labs import ElevenLabsManager
from lib.audio_player import AudioManager
from rich import print
# height of the window showing the character
SCREEN_HEIGHT = 720
SCREEN_WIDTH = 1280

class CommanderGPT:
    

    def __init__(self):
        # read token_config file
        self.token_config = read_config_file("configs/token_config.json")
        
        # read character_config file
        self.character_config = read_config_file("configs/character_config.json")
        if len(sys.argv) < 2:
            exit("You must provide a character defined in character_config.json. EG: commander_gpt.py commander")
        
        # get character based on name from command line args
        self.character_config_key = sys.argv[1]

        # retrieve character config based on character name
        self.character_info = self.character_config.get(self.character_config_key, None)
        if self.character_info is None:
            exit("The provided character name was not defind in character_config.json")

        self.chat_history_filepath = f"chat_history/{self.character_config_key}_history.txt"
        self.use_elevenlabs_voice = self.character_info.get("use_elevenlabs_voice", True)
        self.elevenlabs_voice = self.character_info.get("elevenlabs_voice", None)
        self.azure_voice_name = self.character_info.get("azure_voice_name", "en-US-AvaMultilingualNeural")

        self.hide_character_when_idle = self.character_info.get("hide_character_when_idle", True)

        # setup our libraries
        if self.use_elevenlabs_voice and self.elevenlabs_voice is not None:
            self.elevenlabs_manager = ElevenLabsManager(elevenlabs_api_key=self.token_config.get("elevenlabs_api_key", None))
        
        self.speechtotext_manager = SpeechToTextManager(azure_tts_key=self.token_config.get("azure_tts_key", None), azure_tts_region=self.token_config.get("azure_tts_region", None))
        self.openai_manager = OpenAiManager(openai_api_key=self.token_config.get("openai_api_key", None))
        self.audio_manager = AudioManager()

        # determine what keys we'll listen for to start and stop mic recording
        self.mic_start_key = self.character_info.get("input_voice_start_button", "Key.home")
        self.mic_stop_key = self.character_info.get("input_voice_end_button", "Key.end")
        self.mic_start_with_screenshot_key = self.character_info.get("input_voice_start_button_with_screenshot", "Key.f4")
        self.monitor_to_screenshot = self.character_info.get("monitor_to_screenshot", -1)
        print("mic_start_key", self.mic_start_key)
        print("mic_stop_key", self.mic_stop_key)
        print("mic_start_with_screenshot_key", self.mic_start_with_screenshot_key)
        
        if self.use_elevenlabs_voice and self.elevenlabs_voice is None:
            exit("No elevenlabs voice was provided.")
        
        first_system_message = self.character_info.get("first_system_message", None)
        if first_system_message is not None:
            first_system_message_stringified= "\n".join(first_system_message["content"])
            system_message_formated = {"role": "system", "content": [{"type": "text", "text": first_system_message_stringified}]}
            print("first_system_message:", system_message_formated)
            self.openai_manager.chat_history.append(system_message_formated)

        self.message_replacements = self.character_info.get("message_replacements", None)
        self.supported_prefixes = self.character_info.get("supported_prefixes", None)
        
        self.max_history_length_messages = self.character_info.get("max_history_length_messages", 100)

        with open(self.chat_history_filepath, "w") as file:
            file.write("")

        self.image_idle_path = self.character_info.get("image_idle", None)
        self.image_talking_path = self.character_info.get("image_talking", None)
        self.image_listening_path = self.character_info.get("image_listening", None)
        self.image_thinking_path = self.character_info.get("image_thinking", None)
        self.image_error_path = self.character_info.get("image_error", None)
        
        self.image_azure_voice_style_root_path = self.character_info.get("image_azure_voice_style_root_path", None)
        self.character_pos = (0, SCREEN_HEIGHT)
        self.subtitles = None
        self.voice_style = None
        self.voice_image = None
        self.azure_voice_style_images = {

        }
        if self.image_idle_path and self.image_talking_path:
            self.idle_image = pygame.image.load(f"assets/images/{self.image_idle_path}")
            self.talking_image = pygame.image.load(f"assets/images/{self.image_talking_path}")
            self.listening_image = pygame.image.load(f"assets/images/{self.image_listening_path}")
            self.thinking_image = pygame.image.load(f"assets/images/{self.image_thinking_path}")
            self.error_image = pygame.image.load(f"assets/images/{self.image_error_path}")
            if self.image_azure_voice_style_root_path and self.supported_prefixes:
                for prefix in self.supported_prefixes:
                    prefix_no_brackets = prefix.replace("(","").replace(")","")
                    file_name = f"{prefix_no_brackets}.png"
                    voice_style = self.supported_prefixes[prefix]
                    self.azure_voice_style_images[voice_style] = pygame.image.load(f"assets/images/{self.image_azure_voice_style_root_path}{file_name}")

            pygame.init()
            pygame.display.set_caption('gpt')
            #self.font = pygame.freetype.Font("assets/fonts/NotoSerifCJK-Regular.ttc", 14)
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.update_screen(None, self.character_pos)
        
        
        self.state = None
        if not self.hide_character_when_idle:
            self.state = "idle"

        self.screen_shot_enabled = False
        
        # Create thread to handle the AI stuff, they will terminate if the main process terminates
        thread_chatgpt = threading.Thread(target=self.handle_chatgpt, daemon=True)
        non_blocking_toggles = threading.Thread(target=self.handle_non_blocking_toggles, daemon=True)

        # Start the thread
        thread_chatgpt.start()
        non_blocking_toggles.start()

    def handle_non_blocking_toggles(self):
        while True:
            # Wait until user presses the mic_start_key
            wait_until_key(key_to_match=self.mic_start_with_screenshot_key)
            self.screen_shot_enabled = not self.screen_shot_enabled
            print("Send screenshot with next message? ", self.screen_shot_enabled)

    def update_screen(self, image, pos=(0,0), voice_image=None):
        self.screen.fill((0, 255, 0))
        
        if voice_image:
            self.screen.blit(voice_image, pos)
        elif image:
            self.screen.blit(image, pos)
        
        #if self.subtitles:
        #    self.font.render_to(self.screen, (20, 1024-40), self.subtitles, (0, 0, 0))
        pygame.display.update()
    
    
    def handle_chatgpt(self):

        # start logic loops
        print(f"[green]\nStarting the loop, press num {self.mic_start_key} to begin")
        while True:
            print("[green]\nWaiting")
            # Wait until user presses the mic_start_key
            wait_until_key(key_to_match=self.mic_start_key)

            print("[yellow]\nListening to mic")
            self.state = "listening"
            # get mic result
            mic_result = self.speechtotext_manager.speechtotext_from_mic_continuous(stop_key=self.mic_stop_key)
            self.subtitles = mic_result
            print("[green]\nDone listening to mic")
            self.state = "thinking"

            # send question to openai
            monitor_number = -1
            if self.screen_shot_enabled:
                monitor_number = self.monitor_to_screenshot
            openai_result = self.openai_manager.chat_with_history(prompt=mic_result, monitor_to_screenshot=monitor_number, max_history_length_messages=self.max_history_length_messages)
            
            if openai_result is None:
                print("[red]\nThe AI had nothing to say or something went wrong.")
                self.state="error"
                continue

            if self.message_replacements is not None and openai_result is not None:
                for replacement_info in self.message_replacements:
                    to_replace = replacement_info.get("to_replace", None)
                    replace_with = replacement_info.get("replace_with", None)
                    if to_replace and replace_with:
                        openai_result = openai_result.replace(to_replace, replace_with)
            
            self.subtitles = openai_result

            # write the results to chat_history as a backup
            with open(self.chat_history_filepath, "w") as file:
                file.write(str(self.openai_manager.chat_history))
            
            # submit to 11labs to get audio
            if self.use_elevenlabs_voice:
                print("convert text to audio")
                elevenlabs_output = self.elevenlabs_manager.text_to_audio(input_text=openai_result, voice=self.elevenlabs_voice, save_as_wave=True, subdirectory="assets/audio")
            
            self.state = "talking"
            
            # play the audio
            if self.use_elevenlabs_voice:
                print("play audio")
                self.audio_manager.play_audio(file_path=elevenlabs_output, sleep_during_playback=True, delete_file=True, play_using_music=False)
            else:
                print("play audio using azure tts")
                self.voice_style = None
                self.voice_image = None
                if openai_result.startswith("(") and ")" in openai_result:
                    for prefix in self.supported_prefixes:
                        if openai_result.startswith(prefix):
                            self.voice_style = self.supported_prefixes.get(prefix, None)
                            self.voice_image = self.azure_voice_style_images.get(self.voice_style, None)
                            openai_result = openai_result.removeprefix(prefix)
                self.speechtotext_manager.texttospeech_from_text(azure_voice_name=self.azure_voice_name, azure_voice_style=self.voice_style, text_to_speak=openai_result)
            
            self.state="idle"

            print("[green]\n---\nFinished processing dialogue.\nReady for next input.\n---\n")
            
if __name__ == '__main__':
    commander_gpt = CommanderGPT()
    # main thread will handle visuals and minor events
    pop_up_speed = 30
    while True:
        if commander_gpt.state == "talking":
            # show talking image
            if commander_gpt.character_pos[1] >= pop_up_speed:
                commander_gpt.character_pos = (commander_gpt.character_pos[0], commander_gpt.character_pos[1]-pop_up_speed)
            else:
                commander_gpt.character_pos = (0, random.randint(0,10))
            if random.randrange(0,100) < 5:
                commander_gpt.update_screen(commander_gpt.talking_image, commander_gpt.character_pos, commander_gpt.voice_image)
            elif random.randrange(0,100) < 5:
                commander_gpt.update_screen(commander_gpt.idle_image, commander_gpt.character_pos, None)
            
        elif commander_gpt.state == "idle":
            if commander_gpt.hide_character_when_idle:
                if commander_gpt.character_pos[1] <= SCREEN_HEIGHT-pop_up_speed:
                    commander_gpt.character_pos = (commander_gpt.character_pos[0], commander_gpt.character_pos[1]+pop_up_speed)
                else:
                    commander_gpt.character_pos = (0, SCREEN_HEIGHT)
            else:
                commander_gpt.character_pos = (0, 0)
            commander_gpt.update_screen(commander_gpt.idle_image, commander_gpt.character_pos, None)
        elif commander_gpt.state == "listening":
            commander_gpt.update_screen(commander_gpt.listening_image, commander_gpt.character_pos, None)
        elif commander_gpt.state == "thinking":
            commander_gpt.update_screen(commander_gpt.thinking_image, commander_gpt.character_pos, None)
        elif commander_gpt.state == "error":
            commander_gpt.update_screen(commander_gpt.error_image, commander_gpt.character_pos, None)
        else:
            # remove character from screen
            commander_gpt.update_screen(None)
        time.sleep(0.03)
