import time
import azure.cognitiveservices.speech as speechsdk
from .utils import wait_until_key


class SpeechToTextManager:
    azure_speechconfig = None
    azure_audioconfig = None
    azure_speechrecognizer = None

    def __init__(self, azure_tts_key: str, azure_tts_region: str):
        """Creates an instance of a speech config with specified subscription key and service region.

        Arguments:
            azure_tts_key (str) - The Azure Subscription Key to use.
            azure_tts_region (str) - The Azure Subscription Region to use (EG: westus)

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
        except Exception as e:
            print("Failed to setup azure speech")
            exit(e)

        self.azure_speechconfig.speech_recognition_language = "en-US"

    def speechtotext_from_mic(self):
        self.azure_audioconfig = speechsdk.audio.AudioConfig(
            use_default_microphone=True
        )
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(
            speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig
        )

        print("Speak into your microphone.")
        speech_recognition_result = (
            self.azure_speechrecognizer.recognize_once_async().get()
        )
        text_result = speech_recognition_result.text

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Recognized: {}".format(speech_recognition_result.text))
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print(
                "No speech could be recognized: {}".format(
                    speech_recognition_result.no_match_details
                )
            )
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

        print(f"We got the following text: {text_result}")
        return text_result

    def speechtotext_from_file(self, filename):
        self.azure_audioconfig = speechsdk.AudioConfig(filename=filename)
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(
            speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig
        )

        print("Listening to the file \n")
        speech_recognition_result = (
            self.azure_speechrecognizer.recognize_once_async().get()
        )

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Recognized: \n {}".format(speech_recognition_result.text))
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print(
                "No speech could be recognized: {}".format(
                    speech_recognition_result.no_match_details
                )
            )
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

        return speech_recognition_result.text

    def texttospeech_from_text(
        self,
        azure_voice_name: str,
        azure_voice_style: str = "",
        text_to_speak: str = "",
    ):
        if len(text_to_speak) == 0:
            print("This message was empty")
            return

        voice_style = azure_voice_style

        # The neural multilingual voice can speak different languages based on the input text.
        self.output_speech_config.speech_synthesis_voice_name = azure_voice_name
        self.output_speech_config.speech_synthesis_output_format_string

        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.output_speech_config,
            audio_config=self.output_audio_config,
        )
        # print("voice_style: ", voice_style)
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
            # print("Speech synthesized for text [{}]".format(text_to_speak))
            print("Audio completed")
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print(
                        "Error details: {}".format(cancellation_details.error_details)
                    )
                    print("Did you set the speech resource key and region values?")
                    return None

        return speech_synthesis_result

    def speechtotext_from_file_continuous(self, filename):
        self.azure_audioconfig = speechsdk.audio.AudioConfig(filename=filename)
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(
            speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig
        )

        done = False

        def stop_cb(evt):
            print("CLOSING on {}".format(evt))
            nonlocal done
            done = True

        # These are optional event callbacks that just print out when an event happens.
        # Recognized is useful as an update when a full chunk of speech has finished processing
        # self.azure_speechrecognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
        self.azure_speechrecognizer.recognized.connect(
            lambda evt: print("RECOGNIZED: {}".format(evt))
        )
        self.azure_speechrecognizer.session_started.connect(
            lambda evt: print("SESSION STARTED: {}".format(evt))
        )
        self.azure_speechrecognizer.session_stopped.connect(
            lambda evt: print("SESSION STOPPED {}".format(evt))
        )
        self.azure_speechrecognizer.canceled.connect(
            lambda evt: print("CANCELED {}".format(evt))
        )

        # These functions will stop the program by flipping the "done" boolean when the session is either stopped or canceled
        self.azure_speechrecognizer.session_stopped.connect(stop_cb)
        self.azure_speechrecognizer.canceled.connect(stop_cb)

        # This is where we compile the results we receive from the ongoing "Recognized" events
        all_results = []

        def handle_final_result(evt):
            all_results.append(evt.result.text)

        self.azure_speechrecognizer.recognized.connect(handle_final_result)

        # Start processing the file
        print("Now processing the audio file...")
        self.azure_speechrecognizer.start_continuous_recognition()

        # We wait until stop_cb() has been called above, because session either stopped or canceled
        while not done:
            time.sleep(0.5)

        # Now that we're done, tell the recognizer to end session
        # NOTE: THIS NEEDS TO BE OUTSIDE OF THE stop_cb FUNCTION. If it's inside that function the program just freezes. Not sure why.
        self.azure_speechrecognizer.stop_continuous_recognition()

        final_result = " ".join(all_results).strip()
        print(
            f"\n\nHeres the result we got from contiuous file read!\n\n{final_result}\n\n"
        )
        return final_result

    def speechtotext_from_mic_continuous(self, stop_key="8", commander_gpt=None):
        """performs continuous speech recognition asynchronously with input from microphone"""
        self.azure_audioconfig = speechsdk.audio.AudioConfig(
            use_default_microphone=True
        )  # , device_name="sysdefault:CARD=Snowball")
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(
            speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig
        )

        done = False

        def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            print("RECOGNIZING: {}".format(evt.result.text))
            if commander_gpt:
                commander_gpt.subtitles = evt.result.text

        all_results = []

        def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
            print("RECOGNIZED: {}".format(evt.result.text))
            all_results.append(evt.result.text)

        def stop_cb(evt: speechsdk.SessionEventArgs):
            """callback that signals to stop continuous recognition"""
            print("CLOSING on {}".format(evt))
            nonlocal done
            done = True

        # Connect callbacks to the events fired by the speech recognizer
        self.azure_speechrecognizer.recognizing.connect(recognizing_cb)
        self.azure_speechrecognizer.recognized.connect(recognized_cb)
        self.azure_speechrecognizer.session_stopped.connect(stop_cb)
        self.azure_speechrecognizer.canceled.connect(stop_cb)

        # Perform recognition. `start_continuous_recognition_async asynchronously initiates continuous recognition operation,
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
            if len(all_results) > 0:
                print("\nEnding azure speech recognition\n")
                self.azure_speechrecognizer.stop_continuous_recognition_async()
                break
            else:
                print(
                    "[yellow]\nYou tried to stop the recording before it finished recgonizing any dialogue."
                )
        print("recognition stopped, main thread can exit now.")

        final_result = " ".join(all_results).strip()
        print(f"\n\nHeres the result we got!\n\n{final_result}\n\n")
        return final_result
