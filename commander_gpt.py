import tkinter as tk
import tkinter.font as tkFont
from tkinter import PhotoImage
import threading
import sys
from lib.utils import (
    read_config_file,
    wait_until_key,
    write_json_file,
)
from lib.azure_connections import AzureConnectionsManager
from lib.eleven_labs import ElevenLabsManager
from lib.ai_character import AICharacter
from lib.twitch_bot import TwitchBot

from rich import print
import time
import math
import re


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
        self.init_logic_threads()
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
        self.mic_activation_key = self.system_config.get(
            "mic_activation_key", "Key.home"
        )
        self.enable_screenshot_toggle_key = self.system_config.get(
            "enable_screenshot_toggle_key", "="
        )
        self.subtitles = None
        self.last_characters_response = None

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

        # Twitch configs
        self.enable_twitch_integration = self.system_config.get(
            "enable_twitch_integration", False
        )
        self.twitch_channel_name = self.system_config.get("twitch_channel_name", None)
        self.twitch_chat_history_length = self.system_config.get(
            "twitch_chat_history_length", 50
        )

        self.twitch_access_token = self.token_config.get("twitch_access_token", None)
        # User's subtitles
        self.subtitles_config = self.system_config.get("subtitles", {})
        self.show_subtitles = self.subtitles_config.get("show_subtitles", False)
        self.user_text_color = self.subtitles_config.get("user_text_color", False)
        self.text_outline_color = self.subtitles_config.get("text_outline_color", False)
        self.text_outline_width = self.subtitles_config.get("text_outline_width", 2)
        self.font_size = self.subtitles_config.get("font_size", 32)
        self.subtitle_xpos = self.subtitles_config.get("xpos", 20)
        self.subtitle_ypos = self.subtitles_config.get("ypos", 20)
        self.subtitle_width = self.subtitles_config.get("width", 1280)

        self.font = tkFont.Font(
            family="assets/fonts/NotoSerifCJK-Regular.ttc",
            size=self.font_size,
            weight="bold",
        )

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
        self.speechtotext_manager = AzureConnectionsManager(
            azure_tts_key=self.token_config.get("azure_tts_key", None),
            azure_tts_region=self.token_config.get("azure_tts_region", None),
            speech_recognition_language=self.system_config.get(
                "speech_recognition_language", "en-US"
            ),
        )

        self.twitch_bot: TwitchBot = None
        if self.twitch_channel_name:
            self.twitch_bot = TwitchBot(
                twitch_access_token=self.twitch_access_token,
                twitch_channel_name=self.twitch_channel_name,
                chat_history_length=self.twitch_chat_history_length,
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
            highlightthickness=0,
        )
        self.canvas.pack()

    def init_logic_threads(self):
        """Initializes the main thread that will handle the connections to the AI endpoints.

        Starts new threads that will terminate if the main process terminates.
        The first thread handles user input.
        The second thread handles the queue of characters who you activated to respond.
        There is then a thread for each character who waits for their specific activation key to be pressed and add themselves to the queue.
        The last thread just allows keyboard toggling of screenshots on or off.
        """
        self.character_activation_queue = []
        self.is_talking = False
        # one thread to handle waiting on the mic input
        handle_mic_input_thread = threading.Thread(
            target=self.handle_mic_input, daemon=True
        )
        handle_mic_input_thread.start()
        # thread to go through queue of activated characters and ask them the question
        handle_activate_next_character_thread = threading.Thread(
            target=self.activate_next_character, daemon=True
        )
        handle_activate_next_character_thread.start()

        # one thread per character to wait on being activated
        # when activated they will add themselves to the queue to be asked the question recorded by the mic
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

            # Thread to respond to twitch chat messages if enabled
            if self.enable_twitch_integration:
                thread_twitch_chat = threading.Thread(
                    target=self.handle_twitch_chat_responses,
                    daemon=True,
                    kwargs={"ai_character": ai_character},
                )
                # Start the thread
                thread_twitch_chat.start()
        # thread to read twitch messages if enabled
        if self.enable_twitch_integration:
            thread_twitch_chat_monitor = threading.Thread(
                target=self.handle_twitch_chat_monitor,
                daemon=True,
            )
            # Start the thread
            thread_twitch_chat_monitor.start()

        non_blocking_toggles = threading.Thread(
            target=self.handle_non_blocking_toggles, daemon=True
        )

        non_blocking_toggles.start()

    def update(self):
        """Periodically updates the visuals and interactions in the app.

        This method calls the update_visuals method to refresh the display. It runs in a loop to keep updating until the app is closed.
        """
        # determine how much time has past since the last update
        now = time.monotonic()
        # update visuals telling it how long it's been since an update
        self.update_visuals(time=now)

        # Schedule the next update (every 10ms)
        self.root.after(10, self.update)

    def update_visuals(self, time: int):
        """Updates the visuals on the canvas.

        Clears the canvas, updates the character image and the subtitles based on the current state, and applies the necessary offsets for movement.

        Args:
            time (int): The time given in seconds, always increases.
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
                    offset_y = (
                        ai_character.image_offset_y
                        + ai_character.max_amplitude
                        + (
                            math.sin(time * ai_character.movement_speed)
                            * ai_character.max_amplitude
                        )
                    )
                    character_image = ai_character.voice_image
                    self.show_image(
                        character_image,
                        offset_y=offset_y,
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
                self.draw_text_with_outline(
                    xpos=ai_character.subtitle_xpos,
                    ypos=ai_character.subtitle_ypos,
                    text=ai_character.subtitles,
                    text_color=ai_character.character_text_color,
                    outline_color=ai_character.text_outline_color,
                    width=ai_character.subtitle_width,
                    font=ai_character.font,
                    outline_width=ai_character.text_outline_width,
                )

        # draw user's subtitles from the mic input
        if self.subtitles:
            self.draw_text_with_outline(
                xpos=self.subtitle_xpos,
                ypos=self.subtitle_ypos,
                text=self.subtitles,
                text_color=self.user_text_color,
                outline_color=self.text_outline_color,
                width=self.subtitle_width,
                font=self.font,
                outline_width=self.text_outline_width,
            )

    def show_image(self, file_path: str, offset_y: int, ai_character: AICharacter):
        """Displays an image on the canvas.

        Tries to load the image from the specified file path and display it based on the AI character's config.

        Args:
            file_path (str): The path to the image file to be displayed.
            offset_y (int): Shift the image by this many pixels down.
            ai_character (AICharacter): The AI Character to draw the image of.
        Raises:
            Exception: If the image cannot be loaded, an error message is printed.
        """
        try:
            if file_path is None:
                return

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
            print(file_path)
            ai_character.voice_style = None
            ai_character.voice_image = None

    def draw_text_with_outline(
        self,
        xpos: int,
        ypos: int,
        text: str,
        text_color: str,
        outline_color: str,
        width: int,
        font: tkFont,
        outline_width: int = 2,
    ):
        """Draws text on the canvas with an outline effect.

        The text is drawn multiple times with offsets to create the appearance of an outline.
        Args:
            xpos (int): The x position given in pixels.
            ypos (int): The x position given in pixels.
            text (str): The text to draw.
            text_color (str): The colour of the text.
            outline_color (str): The colour of the text's outline.
            width (int): The width of the text are it can be drawn to, given in pixels.
            font (tkFont): The font face to use.
        """
        # Draw outline text offset from where the actual text will be
        for x_offset in range(-outline_width, outline_width + 1):
            for y_offset in range(-outline_width, outline_width + 1):
                self.canvas.create_text(
                    xpos + x_offset,
                    ypos + y_offset,
                    text=text,
                    font=font,
                    fill=outline_color,
                    anchor="n",
                    width=width,
                    justify="center",
                )

        self.canvas.create_text(
            xpos,
            ypos,
            text=text,
            font=font,
            fill=text_color,
            anchor="n",
            width=width,
            justify="center",
        )

    def handle_mic_input(self):
        """Handles the mic input.
        Wait for the mic activation key to be pressed.
        Record the audio as text using Azure.
        Stop recording when the activation key is pressed again.
        """
        while True:
            if self.is_talking:
                continue
            print(
                f"[green]\nWaiting. Press {self.mic_activation_key} to start talking or the activation key for any character to hear them talk."
            )
            # Wait until user presses the mic_activation_key
            wait_until_key(key_to_match=self.mic_activation_key)
            self.is_talking = True

            print(
                f"[yellow]\nListening to mic. Press {self.mic_activation_key} again to stop talking."
            )
            # clear state of ALL characters if you start talking
            ai_char: AICharacter
            for ai_char in self.ai_characters:
                ai_char.state = "listening"
                ai_char.subtitles = None
                # ensure to reset the user's name to the original configured one
                ai_char.users_name = ai_char.original_users_name

            # get mic result
            mic_result = self.speechtotext_manager.speechtotext_from_mic_continuous(
                stop_key=self.mic_activation_key, commander_gpt=self
            )
            self.subtitles = mic_result
            self.last_characters_response = mic_result
            print("[green]\nDone listening to mic.")
            self.is_talking = False

    def activate_character(self, ai_character: AICharacter):
        """Activates a given AI Character by adding them to the queue.
        Will only add them to the queue if the user is not actively recording from the mic.

        Args:
            ai_character (AICharacter): The AI Character to activate.
        """
        if self.is_talking:
            print(
                f"[red]\nMic is active, cannot activate character. Stop talking by pressing {self.mic_activation_key} again."
            )
            return
        # queue up the given character
        if ai_character not in self.character_activation_queue:
            self.character_activation_queue.append(ai_character)

    def activate_next_character(self):
        """Handles activating each character in the queue one at a time.
        Characters are given the most recent prompt, and it is then sent to OpenAI to generate a response.
        The character's response is then fed into the TTS configured for that character.
        Lastly the returned audio is played.
        It does this for each character in the queue, in the order they were added.
        """
        while True:
            if len(self.character_activation_queue) > 0:
                # first entry in the queue
                ai_character: AICharacter
                ai_character = self.character_activation_queue.pop(0)
                print(
                    f"[green]\n---\nStart processing dialogue for {ai_character.name}.\n---"
                )
                ai_character.state = "thinking"

                # determine if screenshots are enabled, if so what monitor to screenshot
                # -1 means it will not send one in this case
                monitor_number = -1
                if self.screen_shot_enabled:
                    monitor_number = ai_character.monitor_to_screenshot

                # send question to openai
                openai_result = ai_character.openai_manager.chat_with_history(
                    ai_character=ai_character,
                    prompt=self.last_characters_response,
                    monitor_to_screenshot=monitor_number,
                    max_history_length_messages=ai_character.max_history_length_messages,
                    model=ai_character.openai_model_name,
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
                            openai_result = openai_result.replace(
                                to_replace, replace_with
                            )

                # write the results to chat_history as a backup
                write_json_file(
                    ai_character.chat_history_filepath,
                    ai_character.openai_manager.chat_history,
                )
                # hide any mic input shown on screen
                self.subtitles = None
                self.last_characters_response = openai_result

                # submit to 11labs to get audio
                if ai_character.use_elevenlabs_voice:
                    print("convert text to audio and play it")
                    ai_character.voice_style = None
                    # generic talking by default
                    ai_character.voice_image = ai_character.images_by_state.get(
                        "talking"
                    )
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
                    # generic talking by default
                    ai_character.voice_image = ai_character.images_by_state.get(
                        "talking"
                    )
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
                                ai_character.voice_image = (
                                    ai_character.images_by_state.get(
                                        voice_image_file_name,
                                        ai_character.images_by_state.get("error"),
                                    )
                                )
                                openai_result = openai_result.removeprefix(prefix)

                    ai_character.state = "talking"
                    # while this character talks, the others listen
                    other_ai_character: AICharacter
                    for other_ai_character in ai_character.other_ai_characters:
                        other_ai_character.state = "listening"
                        other_ai_character.subtitles = None

                    # there are other characters we could potentially trigger
                    trigger_pattern = re.compile("\[trigger\](.*?)\[\/trigger\]")
                    if (
                        openai_result is not None
                        and ai_character.other_ai_characters is not None
                    ):
                        # find if the AI wants to trigger any other characters
                        find_triggers = re.findall(trigger_pattern, openai_result)
                        if len(find_triggers) > 0:
                            for character_name in find_triggers:
                                # as long as the name is valid
                                if character_name is not None:
                                    # trigger the character specified based on their name
                                    for (
                                        other_ai_character
                                    ) in ai_character.other_ai_characters:
                                        # if the name matches another character in the scene
                                        if other_ai_character.name == character_name:
                                            # add them to the queue to talk next
                                            self.activate_character(other_ai_character)
                                            break
                            # Remove all instances of [trigger]NAME[/trigger]
                            openai_result = re.sub(trigger_pattern, "", openai_result)

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
                    f"[green]\n---\nFinished processing dialogue for {ai_character.name}.\n---\n"
                )
                if len(self.character_activation_queue) <= 0:
                    print(
                        f"[green]\n---\nFinished processing queue, press {self.mic_activation_key} to talk again.\n---\n"
                    )
            time.sleep(0.5)

    def handle_chatgpt(self, ai_character: AICharacter):
        """Listens for the character's activation key is pressed and adds them to the queue to respond.

        Args:
            ai_character (AICharacter): The AI Character to monitor.
        """
        print(
            f"[green]\nStarting the loop for {ai_character.name}, press num {ai_character.activation_key} to begin"
        )
        while True:
            print(f"[green]\n{ai_character.name} is waiting.")
            # wait for them to be activated
            wait_until_key(key_to_match=ai_character.activation_key)
            print(f"[yellow]\n{ai_character.name} has been queued up to talk.")
            self.activate_character(ai_character)

    def handle_twitch_chat_responses(self, ai_character: AICharacter):
        while True:
            # if user is talking through their mic we won't respond to twitch chat
            if self.is_talking:
                continue
            # we will only respond to twitch chat if we're idle
            if ai_character.state != "idle":
                continue
            # there's a queue of characters talking already so don't respond to chat
            if len(self.character_activation_queue) > 0:
                continue

            # get mic result
            twitch_message = self.twitch_bot.pick_random_message(
                ai_character=ai_character, remove_after=True
            )
            # only respond if there's a message
            if twitch_message is not None:
                self.subtitles = twitch_message
                self.last_characters_response = twitch_message
                print(
                    f"[yellow]\n{ai_character.name} has been queued up to respond to twitch chat's message {twitch_message}'"
                )
                self.activate_character(ai_character)
            else:
                # only check once a second at most
                time.sleep(1)

    def handle_twitch_chat_monitor(self):
        if self.enable_twitch_integration:
            self.twitch_bot.run()

    def handle_non_blocking_toggles(self):
        """Waits for a key to pressed and toggles enabling of sending screenshots."""
        # only need to do this if we actually have screenshots enabled in configs
        while True:
            # Wait until user presses the enable_screenshot_toggle_key
            wait_until_key(key_to_match=self.enable_screenshot_toggle_key)
            self.screen_shot_enabled = not self.screen_shot_enabled
            if self.screen_shot_enabled:
                print("[green]\nScreenshot will be sent with your next message.")
            else:
                print("[yelow]\nYour next message will be text-only.")


if __name__ == "__main__":
    print(sys.argv)
    # Create the main window (root)
    root = tk.Tk()

    # Initialize the app
    app = CommanderGPTApp(root=root, args=sys.argv)

    # Run the application
    root.mainloop()
