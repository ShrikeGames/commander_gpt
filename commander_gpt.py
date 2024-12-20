import tkinter as tk
import tkinter.font as tkFont
from PIL import Image, ImageTk
import threading
import sys
from lib.utils import (
    read_config_file,
    wait_until_key,
    write_json_file,
)
from lib.azure_speech_to_text import SpeechToTextManager
from lib.openai_chat import OpenAiManager
from lib.eleven_labs import ElevenLabsManager
from lib.audio_player import AudioManager
from rich import print
from os.path import exists

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720


class CommanderGPTApp:
    def __init__(self, root, args):
        """Initializes the app with a canvas, a background image, and subtitle text.

        Sets up the main window, initializes the canvas, loads an image, and draws text with an outline.

        Args:
            root (tk.Tk): The root Tkinter window.
        """
        self.init_configs(args)
        self.init_libs()
        self.init_chat_history()
        self.init_visuals(root)
        self.init_ai_connections()
        # start updating main thread
        self.update()

    def init_configs(self, args):
        """Initializes configuration settings for the app.

        Loads configuration files, sets up character settings, chat history, voice settings, and other app preferences.

        Args:
            args (list): Command-line arguments, used to determine the character for the app.
        """
        print("[yellow]\nLoading Configs")
        # read token_config file
        self.token_config = read_config_file("configs/token_config.json")

        # read character_config file
        self.character_config = read_config_file("configs/character_config.json")
        if len(args) < 2:
            exit(
                "You must provide a character defined in character_config.json. EG: commander_gpt.py commander"
            )

        # get character based on name from command line args
        self.character_config_key = args[1]

        # retrieve character config based on character name
        self.character_info = self.character_config.get(self.character_config_key, None)
        if self.character_info is None:
            exit("The provided character name was not defined in character_config.json")
        self.chat_history_filepath = (
            f"chat_history/{self.character_config_key}_history.json"
        )
        # what model to use with openai
        self.openai_model_name = self.character_info.get("openai_model_name", "gpt-4o")

        # 11labs configs
        self.use_elevenlabs_voice = self.character_info.get(
            "use_elevenlabs_voice", True
        )
        self.elevenlabs_voice = self.character_info.get("elevenlabs_voice", None)
        self.azure_voice_name = self.character_info.get(
            "azure_voice_name", "en-US-AvaMultilingualNeural"
        )
        if self.use_elevenlabs_voice and self.elevenlabs_voice is None:
            exit("No elevenlabs voice was provided.")

        # key bindings configs
        # determine what keys we'll listen for to start and stop mic recording
        self.mic_start_key = self.character_info.get(
            "input_voice_start_button", "Key.home"
        )
        self.mic_stop_key = self.character_info.get("input_voice_end_button", "Key.end")
        self.mic_start_with_screenshot_key = self.character_info.get(
            "input_voice_start_button_with_screenshot", "Key.f4"
        )

        # screenshot configs
        # whether to be enabled by default or not
        self.screen_shot_enabled = self.character_info.get("screen_shot_enabled", False)
        self.monitor_to_screenshot = self.character_info.get(
            "monitor_to_screenshot", -1
        )

        # character personality configs
        self.first_system_message = self.character_info.get(
            "first_system_message", None
        )

        self.message_replacements = self.character_info.get(
            "message_replacements", None
        )

        # chat history configs
        self.max_history_length_messages = self.character_info.get("history", {}).get(
            "max_history_length_messages", 100
        )
        self.restore_previous_history = self.character_info.get("history", {}).get(
            "restore_previous_history", False
        )

        # subtitles configs
        self.show_subtitles = self.character_info.get("subtitles", {}).get(
            "show_subtitles", False
        )
        self.user_text_color = self.character_info.get("subtitles", {}).get(
            "user_text_color", False
        )
        self.character_text_color = self.character_info.get("subtitles", {}).get(
            "character_text_color", False
        )
        self.text_outline_color = self.character_info.get("subtitles", {}).get(
            "text_outline_color", False
        )
        self.text_outline_width = self.character_info.get("subtitles", {}).get(
            "text_outline_width", 2
        )
        self.font_size = self.character_info.get("subtitles", {}).get("font_size", 32)

        # character visuals configs
        self.hide_character_when_idle = self.character_info.get(
            "hide_character_when_idle", True
        )
        self.background_colour = self.character_info.get("background_colour", "#00FF00")

        self.supported_prefixes = self.character_info.get("supported_prefixes", {})
        self.image_paths = self.character_info.get("images", {})
        self.image_azure_voice_style_root_path = self.character_info.get(
            "image_azure_voice_style_root_path", ""
        )
        # all of the default states (supported by both Azure TTS and 11labs)
        self.images_by_state = {}
        for state, image_path in self.image_paths.items():
            self.images_by_state[state] = f"assets/images/{image_path}"

        # if using Azure TTS (not 11labs) then also add the images for each voice style/emotion
        if not self.use_elevenlabs_voice:
            for prefix, voice_style in self.supported_prefixes.items():
                prefix_no_brackets = prefix.replace("(", "").replace(")", "")
                file_name = f"{prefix_no_brackets}.png"
                self.images_by_state[prefix_no_brackets] = (
                    f"assets/images/{self.image_azure_voice_style_root_path}{file_name}"
                )
        # 1 for down, -1 for up
        self.image_offset_y = 0
        self.movement_direction = 1
        self.movement_speed = 3
        self.image_max_offset = 9
        self.image_min_offset = 0

        # global state
        self.state = "idle"
        self.subtitles = None
        self.voice_style = None
        self.voice_image = None
        self.voice_color = "white"

    def init_chat_history(self):
        """Initializes chat history by reading or clearing history.

        If restoring from a previous history file, it will load it. If not, it clears the history and enters the first system message if available.
        """
        print("[yellow]\nInit Chat History")
        try:
            if self.restore_previous_history and exists(self.chat_history_filepath):
                # read the existing file and use it
                self.openai_manager.chat_history = read_config_file(
                    self.chat_history_filepath
                )
                return
        except Exception as e:
            print(f"[red]\nFailed to read chat history, will create a new one. {e}")

        # otherwise wipe it if it exists
        with open(self.chat_history_filepath, "w") as file:
            file.write("")
        # and enter the first system message if provided
        if self.first_system_message is not None:
            first_system_message_stringified = "\n".join(
                self.first_system_message["content"]
            )
            system_message_formated = {
                "role": "system",
                "content": [{"type": "text", "text": first_system_message_stringified}],
            }
            print("first_system_message:", system_message_formated)
            self.openai_manager.chat_history.append(system_message_formated)

    def init_libs(self):
        """Initializes the necessary libraries for the app.

        Sets up the speech-to-text, OpenAI, ElevenLabs, and audio manager libraries with the respective API keys.
        """
        print("[yellow]\nInit Libraries")
        # setup our libraries
        if self.use_elevenlabs_voice and self.elevenlabs_voice is not None:
            self.elevenlabs_manager = ElevenLabsManager(
                elevenlabs_api_key=self.token_config.get("elevenlabs_api_key", None)
            )
        # Used for transcribing the mic to text, and optionally for TTS as well if not using 11labs
        self.speechtotext_manager = SpeechToTextManager(
            azure_tts_key=self.token_config.get("azure_tts_key", None),
            azure_tts_region=self.token_config.get("azure_tts_region", None),
        )
        # Use to communicate with chatGPT through OpenAI
        self.openai_manager = OpenAiManager(
            openai_api_key=self.token_config.get("openai_api_key", None)
        )
        self.audio_manager = AudioManager()

    def init_visuals(self, root):
        """Initializes the main window and canvas for visual display.

        Sets up the root window size, title, and the canvas for drawing. Initializes the font used for text display.

        Args:
            root (tk.Tk): The root Tkinter window where the app will be displayed.
        """
        print("[yellow]\nInit Main Window")
        self.root = root
        self.root.title("GPT")
        self.root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")

        # Create a canvas to draw text with outline
        self.canvas = tk.Canvas(
            root, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, bg=self.background_colour
        )
        self.canvas.pack()

        self.font = tkFont.Font(
            family="assets/fonts/NotoSerifCJK-Regular.ttc",
            size=self.font_size,
            weight="bold",
        )

    def update_visuals(self):
        """Updates the visuals on the canvas.

        Clears the canvas, updates the character image and the subtitles based on the current state, and applies the necessary offsets for movement.
        """
        self.canvas.delete("all")
        # Show character image
        if self.state != "idle" or not self.hide_character_when_idle:
            if self.state == "talking":
                self.image_offset_y += (
                    self.movement_direction * self.movement_speed
                )  # Adjust speed of movement

                # Reverse direction when reaching top or bottom
                if (
                    self.image_offset_y >= self.image_max_offset
                    or self.image_offset_y <= self.image_min_offset
                ):
                    self.movement_direction *= -1

                # alternate between idle and the associated talking image
                # if self.movement_direction > 0:
                character_image = self.voice_image
                # else:
                #    character_image = self.images_by_state.get("idle")
                self.show_image(character_image, offset_y=self.image_offset_y)
            else:
                self.show_image(self.images_by_state.get(self.state), offset_y=0)

        # Show subtitles
        if self.show_subtitles:
            self.draw_text_with_outline(text=self.subtitles)

    def draw_text_with_outline(self, text: str):
        """Draws text on the canvas with an outline effect.

        The text is drawn multiple times with offsets to create the appearance of an outline.

        Args:
            text (str): The text to be displayed.
        """
        # Draw outline text offset from where the actual text will be
        for x_offset in range(-self.text_outline_width, self.text_outline_width + 1):
            for y_offset in range(
                -self.text_outline_width, self.text_outline_width + 1
            ):
                self.canvas.create_text(
                    (SCREEN_WIDTH * 0.5) + x_offset + 20,
                    20 + y_offset,
                    text=text,
                    font=self.font,
                    fill=self.text_outline_color,
                    anchor="n",
                    width=SCREEN_WIDTH - 40,
                    justify="center",
                )

        self.canvas.create_text(
            20 + SCREEN_WIDTH * 0.5,
            20,
            text=text,
            font=self.font,
            fill=self.voice_color,
            anchor="n",
            width=SCREEN_WIDTH - 40,
            justify="center",
        )

    def show_image(self, file_path: str, offset_y: int = 0):
        """Displays an image on the canvas.

        Tries to load the image from the specified file path and display it centered on the canvas.

        Args:
            file_path (str): The path to the image file to be displayed.

        Raises:
            Exception: If the image cannot be loaded, an error message is printed.
        """
        if file_path is None:
            print("[red]\nNo file_path was provided to show_image!")
            file_path = self.images_by_state.get("error", None)

        try:
            self.image = Image.open(file_path)
            self.photo = ImageTk.PhotoImage(
                image=self.image, size=(SCREEN_WIDTH, SCREEN_HEIGHT)
            )

            self.canvas.create_image(
                SCREEN_WIDTH * 0.5, SCREEN_HEIGHT * 0.5 + offset_y, image=self.photo
            )
        except Exception as e:
            print(f"[red]\nError loading image: {e}")

    def init_ai_connections(self):
        """Initializes the main thread that will handle the connections to the AI endpoints.

        Starts new threads that will terminate if the main process terminates.
        The first thread handles user input, sending to the various endpoints, and printing results.
        The second thread just allows keyboard toggling of screenshots on or off.

        """
        # Create thread to handle the AI stuff, they will terminate if the main process terminates
        thread_chatgpt = threading.Thread(target=self.handle_chatgpt, daemon=True)
        non_blocking_toggles = threading.Thread(
            target=self.handle_non_blocking_toggles, daemon=True
        )

        # Start the thread
        thread_chatgpt.start()
        non_blocking_toggles.start()

    def handle_chatgpt(self):
        """Main logic loop for handling all interactions between the user and AI character."""
        print(f"[green]\nStarting the loop, press num {self.mic_start_key} to begin")
        while True:
            print("[green]\nWaiting")
            # Wait until user presses the mic_start_key
            wait_until_key(key_to_match=self.mic_start_key)

            print("[yellow]\nListening to mic")
            self.state = "listening"
            self.subtitles = None
            self.voice_color = self.user_text_color

            # get mic result
            mic_result = self.speechtotext_manager.speechtotext_from_mic_continuous(
                stop_key=self.mic_stop_key, commander_gpt=self
            )
            self.subtitles = mic_result
            print("[green]\nDone listening to mic")
            self.state = "thinking"

            # determine if screenshots are enabled, if so what monitor to screenshot
            # -1 means it will not send one in this case
            monitor_number = -1
            if self.screen_shot_enabled:
                monitor_number = self.monitor_to_screenshot

            # send question to openai
            openai_result = self.openai_manager.chat_with_history(
                prompt=mic_result,
                monitor_to_screenshot=monitor_number,
                max_history_length_messages=self.max_history_length_messages,
            )
            self.subtitles = None
            if openai_result is None:
                print("[red]\nThe AI had nothing to say or something went wrong.")
                self.state = "error"
                continue

            if self.message_replacements is not None and openai_result is not None:
                for replacement_info in self.message_replacements:
                    to_replace = replacement_info.get("to_replace", None)
                    replace_with = replacement_info.get("replace_with", None)
                    if to_replace and replace_with:
                        openai_result = openai_result.replace(to_replace, replace_with)

            # write the results to chat_history as a backup
            write_json_file(
                self.chat_history_filepath, self.openai_manager.chat_history
            )

            # submit to 11labs to get audio
            if self.use_elevenlabs_voice:
                print("convert text to audio")
                elevenlabs_output = self.elevenlabs_manager.text_to_audio(
                    input_text=openai_result,
                    voice=self.elevenlabs_voice,
                    save_as_wave=True,
                    subdirectory="assets/audio",
                )

            self.state = "talking"
            self.voice_color = self.character_text_color
            self.subtitles = openai_result

            # play the audio
            if self.use_elevenlabs_voice:
                print("play audio")
                self.audio_manager.play_audio(
                    file_path=elevenlabs_output,
                    sleep_during_playback=True,
                    delete_file=True,
                    play_using_music=False,
                )
            else:
                print("play audio using azure tts")
                self.voice_style = None
                self.voice_image = None
                if openai_result.startswith("(") and ")" in openai_result:
                    for prefix in self.supported_prefixes:
                        if openai_result.startswith(prefix):
                            self.voice_style = self.supported_prefixes.get(prefix, None)

                            voice_image_file_name = prefix.replace("(", "").replace(
                                ")", ""
                            )
                            print(self.images_by_state)
                            print(voice_image_file_name)
                            self.voice_image = self.images_by_state.get(
                                voice_image_file_name, self.images_by_state.get("error")
                            )
                            openai_result = openai_result.removeprefix(prefix)
                self.speechtotext_manager.texttospeech_from_text(
                    azure_voice_name=self.azure_voice_name,
                    azure_voice_style=self.voice_style,
                    text_to_speak=openai_result,
                )

            self.state = "idle"
            # if we hide the character then also hide the subtitles when they're done
            if self.hide_character_when_idle:
                self.subtitles = None

            print(
                "[green]\n---\nFinished processing dialogue.\nReady for next input.\n---\n"
            )

    def handle_non_blocking_toggles(self):
        """Waits for a key to pressed and toggles enabling of sending screenshots."""
        # only need to do this if we actually have screenshots enabled in configs
        while True:
            # Wait until user presses the mic_start_key
            wait_until_key(key_to_match=self.mic_start_with_screenshot_key)
            self.screen_shot_enabled = not self.screen_shot_enabled
            if self.screen_shot_enabled:
                print("[green]\nScreenshot will be sent with your next message.")
            else:
                print("[yelow]\nYour next message will be text-only.")

    def update(self):
        """Periodically updates the visuals and interactions in the app.

        This method calls the update_visuals method to refresh the display. It runs in a loop to keep updating until the app is closed.
        """
        self.update_visuals()
        # Schedule the next update (every 10ms)
        self.root.after(10, self.update)


if __name__ == "__main__":
    print(sys.argv)
    # Create the main window (root)
    root = tk.Tk()

    # Initialize the app
    app = CommanderGPTApp(root=root, args=sys.argv)

    # Run the application
    root.mainloop()
