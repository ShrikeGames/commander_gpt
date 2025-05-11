from elevenlabs.client import ElevenLabs
from elevenlabs import save, Voice, AudioWithTimestampsResponseModel
import time
import os
from .audio_player import AudioManager
import base64


class ElevenLabsManager:
    """Manages interaction with the ElevenLabs API, including text-to-speech functionality."""

    def __init__(self, elevenlabs_api_key: str):
        """Initializes the ElevenLabsManager with the provided API key and retrieves voice settings.

        Args:
            elevenlabs_api_key (str): The API key used to authenticate with ElevenLabs.

        Initializes:
            - Retrieves available voices from the ElevenLabs API.
            - Creates mappings of voice names to IDs and stores voice settings for later use.
        """
        self.client = ElevenLabs(api_key=elevenlabs_api_key)
        self.voices = self.client.voices.get_all().voices
        self.voice_to_id = {}
        for voice in self.voices:
            self.voice_to_id[voice.name] = voice.voice_id
            print(voice.name)
        self.voice_to_settings = {}

        self.audio_manager = AudioManager()

    def text_to_audio(
        self,
        ai_character,
        input_text: str,
        voice: str = "Alice",
        save_as_wave: bool = True,
        subdirectory: str = "",
        model_id: str = "eleven_monolingual_v1",
    ) -> str:
        """Converts input text to speech and saves it as an audio file, then plays it.

        It also updates the state of the commander_gpt app so the character reflects the new state.

        Args:
            ai_character (AICharacter): The character speaking.
            input_text (str): The text to be converted to speech.
            voice (str, optional): The voice to use for speech synthesis. Defaults to "Doug VO Only".
            save_as_wave (bool, optional): Whether to save the output as a .wav file (True) or .mp3 (False). Defaults to True.
            subdirectory (str, optional): The subdirectory where the audio file will be saved. Defaults to the current directory.
            model_id (str, optional): The model to use for speech synthesis (e.g., "eleven_monolingual_v1" or "eleven_turbo_v2"). Defaults to "eleven_monolingual_v1".

        Returns:
            str: The file path where the generated audio file is saved.

        Notes:
            - If `save_as_wave` is True, the audio will be saved as a .wav file; otherwise, it will be saved as an .mp3 file.
            - The method uses a workaround for an issue with the ElevenLabs API where the voice settings are not automatically retrieved. It stores the voice settings for later use.
            - The file name is generated based on the hash of the input text and the current time.
        """
        # Workaround to fetch the voice settings the first time a voice is used
        if voice not in self.voice_to_settings:
            self.voice_to_settings[voice] = self.client.voices.get_settings(
                self.voice_to_id[voice]
            )
        voice_settings = self.voice_to_settings[voice]

        # Generate the speech from text using the selected voice and model
        audio_saved = self.client.generate(
            text=input_text,
            voice=Voice(voice_id=self.voice_to_id[voice], settings=voice_settings),
            model=model_id,
        )

        # Generate the file name and path based on whether it's saved as .wav or .mp3
        if save_as_wave:
            file_name = f"___Msg{str(hash(input_text))}{time.time()}_{model_id}.wav"
        else:
            file_name = f"___Msg{str(hash(input_text))}{time.time()}_{model_id}.mp3"

        tts_file = os.path.join(os.path.abspath(os.curdir), subdirectory, file_name)

        # Save the generated audio to the specified file
        save(audio_saved, tts_file)

        ai_character.state = "talking"
        ai_character.voice_color = ai_character.character_text_color
        ai_character.subtitles = input_text
        # while this character talks, the others listen
        for other_ai_character in ai_character.other_ai_characters:
            other_ai_character.state = "listening"
            other_ai_character.subtitles = None

        # play the saved audio file
        self.audio_manager.play_audio(
            file_path=tts_file,
            sleep_during_playback=True,
            delete_file=False,
            play_using_music=True,
        )

        return tts_file

    def text_to_audio_with_timestamps(
        self,
        ai_character,
        input_text: str,
        voice: str = "Alice",
        save_as_wave: bool = True,
        subdirectory: str = "",
        model_id: str = "eleven_monolingual_v1",
    ) -> AudioWithTimestampsResponseModel:
        """Converts input text to speech and saves it as an audio file, then plays it.

        It also updates the state of the commander_gpt app so the character reflects the new state.

        Args:
            ai_character (AICharacter): The character speaking.
            input_text (str): The text to be converted to speech.
            voice (str, optional): The voice to use for speech synthesis. Defaults to "Doug VO Only".
            save_as_wave (bool, optional): Whether to save the output as a .wav file (True) or .mp3 (False). Defaults to True.
            subdirectory (str, optional): The subdirectory where the audio file will be saved. Defaults to the current directory.
            model_id (str, optional): The model to use for speech synthesis (e.g., "eleven_monolingual_v1" or "eleven_turbo_v2"). Defaults to "eleven_monolingual_v1".

        Returns:
            AudioWithTimestampsResponseModel: The audio data and timestamps.

        Notes:
            - If `save_as_wave` is True, the audio will be saved as a .wav file; otherwise, it will be saved as an .mp3 file.
            - The method uses a workaround for an issue with the ElevenLabs API where the voice settings are not automatically retrieved. It stores the voice settings for later use.
            - The file name is generated based on the hash of the input text and the current time.
        """
        # Workaround to fetch the voice settings the first time a voice is used
        if voice not in self.voice_to_settings:
            self.voice_to_settings[voice] = self.client.voices.get_settings(
                self.voice_to_id[voice]
            )
        voice_settings = self.voice_to_settings[voice]

        # Generate the speech from text using the selected voice and model getting the audio and timestamps
        response_model: AudioWithTimestampsResponseModel
        response_model = self.client.text_to_speech.convert_with_timestamps(
            text=input_text,
            voice_id=self.voice_to_id[voice],
            voice_settings=voice_settings,
            model_id=model_id,
        )
        audio_saved = base64.b64decode(response_model.audio_base_64)

        # Generate the file name and path based on whether it's saved as .wav or .mp3
        if save_as_wave:
            file_name = f"___Msg{str(hash(input_text))}{time.time()}_{model_id}.wav"
        else:
            file_name = f"___Msg{str(hash(input_text))}{time.time()}_{model_id}.mp3"

        tts_file = os.path.join(os.path.abspath(os.curdir), subdirectory, file_name)

        # Save the generated audio to the specified file
        save(audio_saved, tts_file)

        ai_character.state = "talking"
        ai_character.voice_color = ai_character.character_text_color
        ai_character.subtitles = input_text
        # while this character talks, the others listen
        for other_ai_character in ai_character.other_ai_characters:
            other_ai_character.state = "listening"
            other_ai_character.subtitles = None

        # play the saved audio file
        self.audio_manager.play_audio(
            file_path=tts_file,
            sleep_during_playback=False,
            delete_file=False,
            play_using_music=True,
        )

        return response_model
