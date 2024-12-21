import tkinter as tk
from tkinter import PhotoImage
import threading
import sys
from lib.utils import (
    read_config_file,
    wait_until_key,
    write_json_file,
)
from lib.azure_speech_to_text import SpeechToTextManager
from lib.eleven_labs import ElevenLabsManager
from lib.ai_character import AICharacter

from rich import print


class CommanderGPTApp:
    def __init__(self, root, args):
        """Initializes the app.

        Loads configs, sets up the libraries, loads or creates the chat history, creates the visuals, and prepares to connect to the endpoints.
        Starts the main update loop.

        Args:
            root (tk.Tk): The root Tkinter window.
            args (list[str]): Command-line arguments, used to determine the character for the app. Expected [filename, character_name].
        """
        self.init_configs(args)
        self.init_libs()

        self.init_visuals(root)
        self.init_ai_connections()
        # start updating main thread
        self.update()

    def init_configs(self, args):
        """Initializes configuration settings for the app and create a character for each name provided.

        Loads configuration files, sets up character, chat history, voice settings, and other app preferences.

        Args:
            args (list[str]): Command-line arguments, used to determine the character for the app. Expected [filename, character_name].
        """
        print("[yellow]\nLoading Configs")
        # read token_config file
        self.token_config = read_config_file("configs/token_config.json")

        # read character_config file
        self.character_config = read_config_file("configs/character_config.json")
        if len(args) < 2:
            exit(
                "You must provide at least one character defined in character_config.json. EG: commander_gpt.py commander"
            )

        # read system configs
        self.system_config = read_config_file("configs/system_config.json")
        self.window_width = self.system_config.get("window_width", 1280)
        self.window_height = self.system_config.get("window_height", 1920)
        self.background_colour = self.system_config.get("background_colour", "#00FF00")
        self.mic_start_with_screenshot_key = self.system_config.get(
            "input_voice_start_button_with_screenshot", "Key.shift"
        )

        # create characters for each one provided in args
        self.ai_characters = []
        for i in range(1, len(args)):
            # get character based on name from command line args
            character_config_key = args[i]
            # retrieve character config based on character name
            character_info = self.character_config.get(character_config_key, None)

            if character_info is None:
                print(
                    f"[red]\nThe provided character name of {character_config_key} was not defined in character_config.json"
                )
                continue

            chat_history_filepath = f"chat_history/{character_config_key}_history.json"
            ai_character = AICharacter(
                commander_gpt=self,
                config=character_info,
                chat_history_filepath=chat_history_filepath,
            )
            self.ai_characters.append(ai_character)

        if len(self.ai_characters) > 1:
            # if there is more than 1 AICharacter then tell them each about the others so they can communicate through shared history
            ai_character: AICharacter
            for ai_character in self.ai_characters:
                other_ai_character: AICharacter
                for other_ai_character in self.ai_characters:
                    if ai_character.name != other_ai_character.name:
                        ai_character.other_ai_characters.append(other_ai_character)

        # whether the next message sent to an ai_character would include a screenshot or not
        self.screen_shot_enabled = False

    def init_libs(self):
        """Initializes the necessary libraries for the app.

        Sets up the speech-to-text, OpenAI, ElevenLabs, and audio manager libraries with the respective API keys.
        """
        print("[yellow]\nInit Libraries")
        # setup our libraries
        self.elevenlabs_manager = None
        ai_character: AICharacter
        # if any of the characters need 11labs then create a manager for it, otherwise don't bother
        for ai_character in self.ai_characters:
            if ai_character.use_elevenlabs_voice and self.elevenlabs_manager is None:
                self.elevenlabs_manager = ElevenLabsManager(
                    elevenlabs_api_key=self.token_config.get("elevenlabs_api_key", None)
                )
                break

        # Used for transcribing the mic to text, and optionally for TTS as well if not using 11labs
        self.speechtotext_manager = SpeechToTextManager(
            azure_tts_key=self.token_config.get("azure_tts_key", None),
            azure_tts_region=self.token_config.get("azure_tts_region", None),
            speech_recognition_language=self.token_config.get(
                "speech_recognition_language", "en-US"
            ),
        )

    def init_visuals(self, root: tk.Tk):
        """Initializes the main window and canvas for visual display.

        Sets up the root window size, title, and the canvas for drawing. Initializes the font used for text display.

        Args:
            root (tk.Tk): The root Tkinter window where the app will be displayed.
        """
        print("[yellow]\nInit Main Window")
        self.root = root
        self.root.title("GPT")
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable = False
        self.image_cache = {}
        # Create a canvas to draw text with outline
        self.canvas = tk.Canvas(
            root,
            width=self.window_width,
            height=self.window_height,
            bg=self.background_colour,
        )
        self.canvas.pack()

    def update_visuals(self):
        """Updates the visuals on the canvas.

        Clears the canvas, updates the character image and the subtitles based on the current state, and applies the necessary offsets for movement.
        """
        self.canvas.delete("all")
        # type hint
        ai_character: AICharacter
        # for each character draw them on the screen in their current state
        for ai_character in self.ai_characters:
            # Show character image
            if (
                ai_character.state != "idle"
                or not ai_character.hide_character_when_idle
            ):
                if ai_character.state == "talking":
                    ai_character.image_offset_y += (
                        ai_character.movement_direction * ai_character.movement_speed
                    )
                    # Reverse direction when reaching top or bottom
                    if (
                        ai_character.image_offset_y >= ai_character.image_max_offset
                        or ai_character.image_offset_y <= ai_character.image_min_offset
                    ):
                        ai_character.movement_direction *= -1

                    character_image = ai_character.voice_image
                    self.show_image(
                        character_image,
                        offset_y=ai_character.image_offset_y,
                        ai_character=ai_character,
                    )

                else:
                    self.show_image(
                        ai_character.images_by_state.get(ai_character.state),
                        offset_y=0,
                        ai_character=ai_character,
                    )

        # for each character draw their subtitles on the screen (so they're on top of all character images)
        for ai_character in self.ai_characters:
            # Show subtitles
            if ai_character.show_subtitles:
                self.draw_text_with_outline(ai_character=ai_character)

    def draw_text_with_outline(self, ai_character: AICharacter):
        """Draws text on the canvas with an outline effect.

        The text is drawn multiple times with offsets to create the appearance of an outline.

        Args:
            ai_character (AICharacter): The ai character to display their text for.
        """
        # Draw outline text offset from where the actual text will be
        for x_offset in range(
            -ai_character.text_outline_width, ai_character.text_outline_width + 1
        ):
            for y_offset in range(
                -ai_character.text_outline_width, ai_character.text_outline_width + 1
            ):
                self.canvas.create_text(
                    ai_character.subtitle_xpos + x_offset,
                    ai_character.subtitle_ypos + y_offset,
                    text=ai_character.subtitles,
                    font=ai_character.font,
                    fill=ai_character.text_outline_color,
                    anchor="n",
                    width=ai_character.subtitle_width,
                    justify="center",
                )

        self.canvas.create_text(
            ai_character.subtitle_xpos,
            ai_character.subtitle_ypos,
            text=ai_character.subtitles,
            font=ai_character.font,
            fill=ai_character.voice_color,
            anchor="n",
            width=ai_character.subtitle_width,
            justify="center",
        )

    def show_image(self, file_path: str, offset_y: int, ai_character: AICharacter):
        """Displays an image on the canvas.

        Tries to load the image from the specified file path and display it centered on the canvas.

        Args:
            file_path (str): The path to the image file to be displayed.

        Raises:
            Exception: If the image cannot be loaded, an error message is printed.
        """
        try:
            image = self.image_cache.get(file_path, None)
            if image is None:
                image = PhotoImage(file=file_path)
                self.image_cache[file_path] = image

            self.canvas.create_image(
                ai_character.image_xpos,
                ai_character.image_ypos + offset_y,
                image=image,
                anchor=ai_character.image_alignment,
            )
        except Exception as e:
            print(f"[red]\nError loading image: {e}")

    def init_ai_connections(self):
        """Initializes the main thread that will handle the connections to the AI endpoints.

        Starts new threads that will terminate if the main process terminates.
        The first thread handles user input, sending to the various endpoints, and printing results.
        The second thread just allows keyboard toggling of screenshots on or off.

        """
        ai_character: AICharacter
        for ai_character in self.ai_characters:
            # Create thread to handle the AI stuff, they will terminate if the main process terminates
            thread_chatgpt = threading.Thread(
                target=self.handle_chatgpt,
                daemon=True,
                kwargs={"ai_character": ai_character},
            )
            # Start the thread
            thread_chatgpt.start()

        non_blocking_toggles = threading.Thread(
            target=self.handle_non_blocking_toggles, daemon=True
        )

        non_blocking_toggles.start()

    def handle_chatgpt(self, ai_character: AICharacter):
        """Main logic loop for handling all interactions between the user and AI character."""
        print(
            f"[green]\nStarting the loop for {ai_character.name}, press num {ai_character.mic_start_key} to begin"
        )
        while True:
            print("[green]\nWaiting")
            # Wait until user presses the mic_start_key
            wait_until_key(key_to_match=ai_character.mic_start_key)

            print("[yellow]\nListening to mic")
            # clear state of ALL characters if you start talking to one of them
            for ai_char in self.ai_characters:
                ai_char.state = "idle"
                ai_char.subtitles = None
                ai_char.voice_color = ai_character.user_text_color
            
            ai_character.state = "listening"

            # get mic result
            mic_result = self.speechtotext_manager.speechtotext_from_mic_continuous(
                stop_key=ai_character.mic_stop_key, ai_character=ai_character
            )
            ai_character.subtitles = mic_result
            print("[green]\nDone listening to mic")
            ai_character.state = "thinking"

            # determine if screenshots are enabled, if so what monitor to screenshot
            # -1 means it will not send one in this case
            monitor_number = -1
            if self.screen_shot_enabled:
                monitor_number = ai_character.monitor_to_screenshot

            # send question to openai
            openai_result = ai_character.openai_manager.chat_with_history(
                ai_character=ai_character,
                prompt=mic_result,
                monitor_to_screenshot=monitor_number,
                max_history_length_messages=ai_character.max_history_length_messages,
                other_ai_characters=ai_character.other_ai_characters,
            )
            ai_character.subtitles = None
            if openai_result is None:
                print(
                    "[red]\nThe AI had nothing to say or something went wrong, if you simply pressed the key too early press it again."
                )
                ai_character.state = "error"
                continue

            if (
                ai_character.message_replacements is not None
                and openai_result is not None
            ):
                for replacement_info in ai_character.message_replacements:
                    to_replace = replacement_info.get("to_replace", None)
                    replace_with = replacement_info.get("replace_with", None)
                    if to_replace and replace_with:
                        openai_result = openai_result.replace(to_replace, replace_with)

            # write the results to chat_history as a backup
            write_json_file(
                ai_character.chat_history_filepath,
                ai_character.openai_manager.chat_history,
            )

            # submit to 11labs to get audio
            if ai_character.use_elevenlabs_voice:
                print("convert text to audio and play it")
                self.elevenlabs_manager.text_to_audio(
                    ai_character=ai_character,
                    input_text=openai_result,
                    voice=ai_character.elevenlabs_voice,
                    save_as_wave=True,
                    subdirectory="assets/audio",
                )
            else:
                # Using Azure TTS

                # play the audio
                print("play audio using azure tts")
                ai_character.voice_style = None
                ai_character.voice_image = None
                # Azure TTS support more voice styles, so use those images if they exist
                if openai_result.startswith("(") and ")" in openai_result:
                    for prefix in ai_character.supported_prefixes:
                        if openai_result.startswith(prefix):
                            ai_character.voice_style = (
                                ai_character.supported_prefixes.get(prefix, None)
                            )

                            voice_image_file_name = prefix.replace("(", "").replace(
                                ")", ""
                            )
                            ai_character.voice_image = ai_character.images_by_state.get(
                                voice_image_file_name,
                                ai_character.images_by_state.get("error"),
                            )
                            openai_result = openai_result.removeprefix(prefix)

                ai_character.state = "talking"
                # while this character talks, the others listen
                for other_ai_character in ai_character.other_ai_characters:
                    other_ai_character.state = "listening"
                    other_ai_character.subtitles = None

                ai_character.voice_color = ai_character.character_text_color
                ai_character.subtitles = openai_result

                self.speechtotext_manager.texttospeech_from_text(
                    azure_voice_name=ai_character.azure_voice_name,
                    azure_voice_style=ai_character.voice_style,
                    text_to_speak=openai_result,
                )

            ai_character.state = "idle"
            # if we hide the character then also hide the subtitles when they're done
            if ai_character.hide_character_when_idle:
                ai_character.subtitles = None

            print(
                f"[green]\n---\nFinished processing dialogue for {ai_character.name}.\nReady for next input.\n---\n"
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
