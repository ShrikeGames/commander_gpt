import time
import keyboard
import sys
from lib.utils import read_config_file
from lib.azure_speech_to_text import SpeechToTextManager
from lib.openai_chat import OpenAiManager
from lib.eleven_labs import ElevenLabsManager
from lib.audio_player import AudioManager

if __name__ == '__main__':
    # read token_config file
    token_config = read_config_file("configs/token_config.json")
    
    # read character_config file
    character_config = read_config_file("configs/character_config.json")
    if len(sys.argv) < 2:
        exit("You must provide a character defined in character_config.json. EG: commander_gpt.py commander")
    
    # get character based on name from command line args
    character_config_key = sys.argv[1]

    # retrieve character config based on character name
    character_info = character_config.get(character_config_key, None)
    if character_info is None:
        exit("The provided character name was not defind in character_config.json")

    chat_history_filepath = f"chat_history/{character_config_key}_history.txt"
    use_elevenlabs_voice = character_info.get("use_elevenlabs_voice", True)
    elevenlabs_voice = character_info.get("elevenlabs_voice", None)
    azure_voice_name = character_info.get("azure_voice_name", "en-US-AvaMultilingualNeural")

    # setup our libraries
    if use_elevenlabs_voice and elevenlabs_voice is not None:
        elevenlabs_manager = ElevenLabsManager(elevenlabs_api_key=token_config.get("elevenlabs_api_key", None))
    
    speechtotext_manager = SpeechToTextManager(azure_tts_key=token_config.get("azure_tts_key", None), azure_tts_region=token_config.get("azure_tts_region", None))
    openai_manager = OpenAiManager(openai_api_key=token_config.get("openai_api_key", None))
    audio_manager = AudioManager()

    # determine what keys we'll listen for to start and stop mic recording
    mic_start_key = character_info.get("input_voice_start_button", "F4")
    mic_stop_key = character_info.get("input_voice_end_button", "p")
    print("mic_start_key", mic_start_key)
    print("mic_stop_key", mic_stop_key)
    
    if use_elevenlabs_voice and elevenlabs_voice is None:
        exit("No elevenlabs voice was provided.")
    
    first_system_message = character_info.get("first_system_message", None)
    print("first_system_message:", first_system_message)
    if first_system_message is not None:
        openai_manager.chat_history.append(first_system_message)

    message_replacements = character_info.get("message_replacements", None)

    with open(chat_history_filepath, "w") as file:
        file.write("")

    # start logic loops
    print("[green]Starting the loop, press num 7 to begin")
    while True:
        # Wait until user presses the mic_start_key
        if not keyboard.is_pressed(mic_start_key):
            time.sleep(0.1)
            continue
        print("Listening to mic")
        # get mic result
        mic_result = speechtotext_manager.speechtotext_from_mic_continuous(stop_key=mic_stop_key)

        #mic_result = speechtotext_manager.speechtotext_from_file("question.wav")
        print("Done listening to mic")
        print("mic_result: ", mic_result)
        # send question to openai
        openai_result = openai_manager.chat_with_history(prompt=mic_result)
        print("openai_result: ", openai_result)

        if message_replacements is not None:
            for replacement_info in message_replacements:
                to_replace = replacement_info.get("to_replace", None)
                replace_with = replacement_info.get("replace_with", None)
                if to_replace and replace_with:
                    openai_result = openai_result.replace(to_replace, replace_with)

        # write the results to chat_history as a backup
        with open(chat_history_filepath, "w") as file:
            file.write(str(openai_manager.chat_history))
        
        # submit to 11labs to get audio
        if use_elevenlabs_voice:
            print("convert text to audio")
            elevenlabs_output = elevenlabs_manager.text_to_audio(input_text=openai_result, voice=elevenlabs_voice, save_as_wave=True, subdirectory="assets/audio")

        # show configured image

        # play the audio
        if use_elevenlabs_voice:
            print("play audio")
            audio_manager.play_audio(file_path=elevenlabs_output, sleep_during_playback=True, delete_file=False, play_using_music=True)
        else:
            print("play audio using azure tts")
            speechtotext_manager.texttospeech_from_text(azure_voice_name=azure_voice_name, text_to_speak=openai_result)
        
        # hide the configured image
        print("\n---\nFinished processing dialogue.\nReady for next input.\n---\n")
