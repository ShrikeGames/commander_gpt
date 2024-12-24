import pygame
import time
import os
import subprocess

import pyaudio
import soundfile as sf
from mutagen.mp3 import MP3
from rich import print

BUFFER_SIZE = 2048


class AudioManager:
    """Manages audio playback and recording, including methods for playing audio files and calculating audio length."""

    # Variables for recording audio from mic
    is_recording = False
    audio_frames = []
    audio_format = pyaudio.paInt16
    channels = 2
    rate = 44100
    chunk = BUFFER_SIZE

    def __init__(self):
        """Initializes the Pygame mixer for audio playback.

        This method sets the audio playback frequency to 48kHz and the buffer size to the predefined constant
        `BUFFER_SIZE` to avoid audio glitches during playback.
        """
        pygame.mixer.init(frequency=48000, buffer=BUFFER_SIZE)
        return

    def play_audio(
        self,
        file_path: str,
        sleep_during_playback: bool = True,
        delete_file: bool = False,
        play_using_music: bool = True,
    ):
        """Plays an audio file using Pygame's mixer.

        Args:
            file_path (str): The path to the audio file to be played.
            sleep_during_playback (bool, optional): Whether the program should wait for the length of the audio file before returning. Defaults to True.
            delete_file (bool, optional): Whether to delete the file after playback. Should not be used in multithreaded contexts. Defaults to False.
            play_using_music (bool, optional): If True, the audio will be played using Pygame's Music system (which only supports one file at a time). If False, it will use Pygame's Sound system to allow simultaneous playback of multiple sounds. Defaults to True.

        Raises:
            Exception: If the audio file format is incompatible with Pygame's Music system, the file will be converted to WAV format.
        """
        if not pygame.mixer.get_init():  # Reinitialize mixer if needed
            pygame.mixer.init(frequency=48000, buffer=BUFFER_SIZE)

        if play_using_music:
            # Pygame Music can only play one file at a time
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                converted = False
            except Exception:
                # Convert the file to a supported format if loading fails
                converted_wav = "temp_convert.wav"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        file_path,
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-c:a",
                        "pcm_s16le",
                        converted_wav,
                    ]
                )
                converted = True
                pygame.mixer.music.load(converted_wav)
                pygame.mixer.music.play()
        else:
            converted = False
            # Use Pygame Sound for simultaneous playback
            pygame_sound = pygame.mixer.Sound(file_path)
            pygame_sound.play()

        if sleep_during_playback:
            # Sleep until the file is done playing
            file_length = self.get_audio_length(file_path)
            time.sleep(file_length)
            # Delete the file if specified
            if delete_file:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                try:
                    os.remove(file_path)
                    if converted:
                        os.remove(
                            converted_wav
                        )  # Remove the converted wav if it was created
                except PermissionError:
                    print(
                        f"[red]\nCouldn't remove {file_path} because it is being used by another process."
                    )

    def get_audio_length(self, file_path: str) -> float:
        """Calculates the length of an audio file based on its format.

        Args:
            file_path (str): The path to the audio file.

        Returns:
            float: The length of the audio file in seconds.

        Raises:
            ValueError: If the audio file type is not supported.
        """
        _, ext = os.path.splitext(file_path)  # Get the extension of this file
        if ext.lower() == ".wav":
            wav_file = sf.SoundFile(file_path)
            file_length = wav_file.frames / wav_file.samplerate
            wav_file.close()
        elif ext.lower() == ".mp3":
            mp3_file = MP3(file_path)
            file_length = mp3_file.info.length
        else:
            print("[red]\nUnknown audio file type. Returning 0 as file length")
            file_length = 0
        return file_length
