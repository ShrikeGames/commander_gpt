import azure.cognitiveservices.speech as speechsdk
from .utils import wait_until_key
from rich import print


class SpeechToTextManager:
    """Class for managing Azure Speech-to-Text and Text-to-Speech operations."""

    azure_speechconfig = None
    azure_audioconfig = None
    azure_speechrecognizer = None

    def __init__(
        self,
        azure_tts_key: str,
        azure_tts_region: str,
        speech_recognition_language: str = "en-US",
    ):
        """Initializes the SpeechToTextManager with specified Azure subscription key and region.

        Args:
            azure_tts_key (str): The Azure Subscription Key to use for the Speech API.
            azure_tts_region (str): The Azure Subscription Region (e.g., "westus") for the Speech API.
            speech_recognition_language (str): The Speech Recognition Language (default en-US)
        Raises:
            Exception: If the Azure Speech configuration fails to initialize.
        """
        try:
            self.azure_speechconfig = speechsdk.SpeechConfig(
                subscription=azure_tts_key, region=azure_tts_region
            )
            self.output_speech_config = speechsdk.SpeechConfig(
                subscription=azure_tts_key, region=azure_tts_region
            )
            self.output_audio_config = speechsdk.audio.AudioOutputConfig(
                use_default_speaker=True
            )
            self.azure_speechconfig.speech_recognition_language = (
                speech_recognition_language
            )
        except Exception as e:
            print("[red]\nFailed to setup azure speech")
            exit(e)

    def texttospeech_from_text(
        self,
        azure_voice_name: str,
        azure_voice_style: str = "",
        text_to_speak: str = "",
    ):
        """Synthesizes text to speech using Azure's Text-to-Speech service.

        Args:
            azure_voice_name (str): The name of the voice to use for synthesis (e.g., "en-US-JennyNeural").
            azure_voice_style (str, optional): The style of the voice (e.g., "cheerful", "whispering"). Defaults to "".
            text_to_speak (str): The text to convert into speech.

        Returns:
            speechsdk.SpeechSynthesisResult: The result of the speech synthesis process.

        Raises:
            None: Prints errors to console if synthesis fails.
        """
        if len(text_to_speak) == 0:
            print("This message was empty")
            return

        voice_style = azure_voice_style

        # Set the voice and format for synthesis
        self.output_speech_config.speech_synthesis_voice_name = azure_voice_name
        self.output_speech_config.speech_synthesis_output_format_string

        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.output_speech_config,
            audio_config=self.output_audio_config,
        )

        if voice_style != "":
            ssml_text = f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xmlns:emo='http://www.w3.org/2009/10/emotionml' xml:lang='en-US'><voice name='{azure_voice_name}'><mstts:express-as style='{voice_style}'>{text_to_speak}</mstts:express-as></voice></speak>"
            speech_synthesis_result = speech_synthesizer.speak_ssml_async(
                ssml_text
            ).get()
        else:
            speech_synthesis_result = speech_synthesizer.speak_text_async(
                text_to_speak
            ).get()

        if (
            speech_synthesis_result.reason
            == speechsdk.ResultReason.SynthesizingAudioCompleted
        ):
            print("Audio completed")
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print(f"[yellow]\nSpeech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print(f"[red]\nError details: {cancellation_details.error_details}")
                    print("Did you set the speech resource key and region values?")
                    return None

        return speech_synthesis_result

    def speechtotext_from_mic_continuous(self, stop_key="8", ai_character=None):
        """Performs continuous speech recognition using the microphone input.

        Args:
            stop_key (str, optional): The key to stop the speech recognition (default is "8").
            ai_character (AICharacter, optional): The ai charater you are talking to.

        Returns:
            str: The recognized speech as a single concatenated string.

        Raises:
            None: Prints any errors or details during the speech recognition process.
        """
        self.azure_audioconfig = speechsdk.audio.AudioConfig(
            use_default_microphone=True
        )
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(
            speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig
        )

        done = False

        def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            """Callback function that handles speech recognition results while recognizing.

            Args:
                evt (speechsdk.SpeechRecognitionEventArgs): The event argument containing recognition data.
            """
            # print(f"RECOGNIZING: {evt.result.text}")
            if ai_character:
                # tell it to show your in-progress message
                ai_character.subtitles = evt.result.text

        all_results = []

        def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            """Callback function that handles speech recognition results once recognized.

            Args:
                evt (speechsdk.SpeechRecognitionEventArgs): The event argument containing recognition data.
            """
            print(f"[green]\n{evt.result.text}")
            all_results.append(evt.result.text)

        def stop_cb(evt: speechsdk.SessionEventArgs):
            """Callback function that signals to stop continuous recognition.

            Args:
                evt (speechsdk.SessionEventArgs): The event argument signaling session end.
            """
            # print(f"CLOSING on {evt}")
            nonlocal done
            done = True

        # Connect callbacks to the events fired by the speech recognizer
        self.azure_speechrecognizer.recognizing.connect(recognizing_cb)
        self.azure_speechrecognizer.recognized.connect(recognized_cb)
        self.azure_speechrecognizer.session_stopped.connect(stop_cb)
        self.azure_speechrecognizer.canceled.connect(stop_cb)

        # Perform recognition. `start_continuous_recognition_async` asynchronously initiates continuous recognition operation,
        # Other tasks can be performed on this thread while recognition starts...
        # wait on result_future.get() to know when initialization is done.
        # Call stop_continuous_recognition_async() to stop recognition.
        result_future = self.azure_speechrecognizer.start_continuous_recognition_async()

        result_future.get()  # wait for voidfuture, so we know engine initialization is done.
        print("Continuous Recognition is now running, say something.")

        while not done:
            # No real sample parallel work to do on this thread, so just wait for user to type stop.
            # Can't exit function or speech_recognizer will go out of scope and be destroyed while running.
            wait_until_key(key_to_match=stop_key)
            print("\nEnding azure speech recognition\n")
            self.azure_speechrecognizer.stop_continuous_recognition_async()
            break

        print("recognition stopped, main thread can exit now.")
        if len(all_results) <= 0:
            return None

        final_result = " ".join(all_results).strip()
        print(f"[green]\n\nHere’s the result we got!\n\n{final_result}\n\n")
        return final_result
