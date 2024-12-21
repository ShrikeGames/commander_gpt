from .utils import (
    read_config_file,
)
from .openai_chat import OpenAiManager

from rich import print
from os.path import exists
import tkinter.font as tkFont


class AICharacter:
    """Representation of an AI Character."""

    def __init__(self, commander_gpt, config: dict, chat_history_filepath: str):
        """Initializes the OpenAiManager with an API key for OpenAI access.

        Args:
            commander_gpt (CommanderGPTApp): The commander gpt app.
            config (dict): A dictionary of configs specific to this character.
            chat_history_filepath (str): The path to where this character should store its history.
        """
        self.character_info = config
        self.commander_gpt = commander_gpt
        self.chat_history_filepath = chat_history_filepath

        self.init_configs()
        self.init_libs()
        self.init_chat_history()

    def init_configs(self):
        """Initializes configuration settings for character.

        Extracts config values from the character_info dictionary.
        """
        self.name = self.character_info.get("name", "AI")
        self.users_name = self.character_info.get("users_name", "Player")

        self.other_ai_characters = []

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

        # screenshot configs
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

        self.visuals_config = self.character_info.get("visuals", {})

        # subtitles configs
        self.subtitles_config = self.visuals_config.get("subtitles", {})
        self.show_subtitles = self.subtitles_config.get("show_subtitles", False)
        self.user_text_color = self.subtitles_config.get("user_text_color", False)
        self.character_text_color = self.subtitles_config.get(
            "character_text_color", False
        )
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

        # character visuals configs
        self.hide_character_when_idle = self.visuals_config.get(
            "hide_character_when_idle", True
        )
        self.image_alignment = self.visuals_config.get("image_alignment", "n")
        self.image_xpos = self.visuals_config.get("image_xpos", 0)
        self.image_ypos = self.visuals_config.get("image_ypos", 0)

        self.supported_prefixes = self.visuals_config.get("supported_prefixes", {})
        self.image_paths = self.visuals_config.get("images", {})
        self.image_azure_voice_style_root_path = self.visuals_config.get(
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
        self.movement_speed = 2
        self.image_max_offset = 9
        self.image_min_offset = 0

        # global state
        self.state = "idle"
        self.subtitles = None
        self.voice_style = None
        self.voice_image = None
        self.voice_color = "white"

    def init_libs(self):
        """Initializes libraries unique to this character.

        Creates an OpenAIManager to communicate with chatGPT.
        """
        self.openai_manager = OpenAiManager(
            openai_api_key=self.commander_gpt.token_config.get("openai_api_key", None)
        )

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
