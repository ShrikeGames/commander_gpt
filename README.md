# Commander GPT
- An integratation of OpenAI, Azure TTS, and other tech to have a conversation with a fictional character.
- It aims to have a customizable experience without needing to change code, just config files or image files.

## Inspiration
Based on DougDoug's https://github.com/DougDougGithub/Babagaboosh/tree/main


## Setup:
It is suggested to use a virtual environment.

1. Install required libraries, note we are using python 3.
```
pip install -r requirements.txt
```

Create a token_config.json in the configs folder with the following format
```json
{
    "elevenlabs_api_key": "YOUR KEY HERE",
    "azure_tts_key": "YOUR KEY HERE",
    "azure_tts_region": "YOUR REGION HERE",
    "openai_api_key": "YOUR KEY HERE"
}
```
2. Update character_config.json with specifics to your character.
- TODO: Document all parts of it.
- You can switch between using 11lab voices or not (if not then it will use azure TTS instead)
- 11labs is more expensive, and azure gives you plenty of monthly credits to effectively be free.
- Azure TTS also supports changing the voice style (shouting, sad, excited, etc) depending on the voice selected.
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support

3. Add your character's images to assets/images
4. Start the program by running
```
.venv/bin/python3 commander_gpt.py your_characters_defined_name
```
For example:
```
.venv/bin/python3 commander_gpt.py commander
```
5. Press the HOME key to start recording from your mic (or whatever key you defined in character_config.json)
6. Talk as much as you want
7. If you want a screenshot to be included with your message then you can toggle that on or off with SHIFT (or button defined in character_config.json)
8. Wait a second or two after you are done talking to allow the speech-to-text to finish
9. Press the END key (or button defined in character_config.json) to send the transcribed audio to ChatGPT via OpenAI
10. when a response from OpenAI is returned it will process it and send it to either 11labs or azure to convert to audio
11. It will now play the audio of the character talking and show the image of the character.
12. When the character is done talking you can return to step 5 and repeat to continue the conversation.


## Troubleshooting
DO NOT RUN AS SUDO IF ON LINUX.
- It seems only one process can have root access to the microphone or output device at one time
- Running it as a regular user doesn't seem to have this limitation
- Tested on Linux Mint
- The program does not use the "keyboard" library anymore because that requires root access, and nothing else does
- Ensure your API keys are correct.
- Read the terminal output for error messages, they should usually tell you what is wrong.


## TODOs
- (Maybe) Replace pygame with an easier frontend
- Option to restore conversation from logged history
- (Maybe) Instead of sending images directly to OpenAI use another service to describe the image and send OpenAI the description