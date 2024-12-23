# Commander GPT
- An integratation of OpenAI, Azure TTS, and other tech to have a conversation with a fictional character.
- It aims to have a customizable experience without needing to change code, just config files or image files.

## Inspiration
Based on DougDoug's https://github.com/DougDougGithub/Babagaboosh/tree/main

Key differences:
- No OBS Websockets at all, instead it is an application that opens up a window for you to capture and use a chroma-key on.
![Screenshot_2024-12-20_12-22-01](https://github.com/user-attachments/assets/39cf0e20-cb5e-4cec-a440-a4393b9333f1)
- Does not use the "keyboards" library to avoid needing to run as sudo/root on linux.
- Instead of modifying the code for every use-case, it is instead driven by only 2 configuration files (you can still modify the code however you like).
- Easy swapping between characters without making changes.
- Customizable images that can match the state of the character including their emotion/voice style.
- Cleaner code that only has what you need.
- Documentation ;P
- Allows toggling features on or off, including using Azure TTS instead of 11labs.
- Easier multi-lingual support (EG: English and Japanese at the same time).
  - EG: If you are speaking Japanese change `speech_recognition_language` in the `system_configs.json` to `ja-JP`.
- Can allow arbitrary amounts of characters to talk together, and with you, just be providing their configuration names as arguments.
  - So if you want them to talk to each other, play DND, have an entire council of advisors, etc you can
  - Or just have a regular 1-on-1 conversation.

## Video Example
### Short Example
https://github.com/user-attachments/assets/b94c55be-72be-4fcd-8d22-8dc8c9cb4310

### Multiple Character Example
3 DND Characters converse with each other about their plans.

https://github.com/user-attachments/assets/36e2c841-45f1-4e54-b263-1eb7bf0c89f8

### YouTube
You can check out what happens when 4 AIs play DND together (1 DM and 3 as Players). Recorded on 2024-12-22.
https://www.youtube.com/watch?v=3dd3WLQucZg

You can check out this AI (as of 2024-12-19, now outdated) making all of the decisions in XCOM Enemy Unknown here:
https://www.youtube.com/watch?v=x0U_EnhkBwI


## Setup:
It is suggested to use a virtual environment.

1. Install required libraries, and accounts.

## The Project
- Clone the repo
```
git clone https://github.com/ShrikeGames/commander_gpt.git
```
- Install requirements:
  - Note we are using python 3
```
pip install -r requirements.txt
```

- Create a token_config.json in the configs folder with the following format
```json
{
    "elevenlabs_api_key": "YOUR KEY HERE",
    "azure_tts_key": "YOUR KEY HERE",
    "azure_tts_region": "YOUR REGION HERE",
    "openai_api_key": "YOUR KEY HERE"
}
```
- You will have to register for accounts on these services.
- They also require you to have payment information included.
- ElevenLabs is optional, only if you want more personalized and better sounding voices.

## Azure
- Create an account and login to https://portal.azure.com
- Azure will give you free credits to start, and although you need payment information will not bill you anything until you have used up those credits.
- The free credits are at least $200 USD as of writing this. You can upgrade your account to a pay-as-you-go within the first month.
- It is generally going to be very cheap, or completely free as you won't surpass the free credits easily.
- Additionally you can see how much completely free (no matter what usage) you get from them here: https://azure.microsoft.com/en-ca/pricing/details/cognitive-services/speech-services/
- Create a Resource Group
- Create a "Speech service" inside of your new Resource Group
- Your `azure_tts_key` and `azure_tts_region` are found under "Resource Management" > "Keys and Endpoint"


## OpenAI
- Create an account and login to https://platform.openai.com
- Click on the "Settings" cog in the top right
- In the left navigation click on PROJECT > API keys
- Click "Create new secret key" in the top right
- Copy the created key and that is your `openai_api_key`
- To use some models such as `gpt-4o`, you will need to have at least $5 billed to your account.
- For pricing you can view this page: https://openai.com/api/pricing/
- Note: Sending images (such as screenshots which is a feature of this app) costs although not very much even for a 1080p picture.
- Note: Some models such as `gpt-4o-mini` are extremely cheap in comparison to the full `gpt-4o` if you are on a tighter budget.
  - `$1.25 / 1M input tokens` for `gpt-4o` vs `$0.075 / 1M input tokens` for `gpt-4o-mini`

## ElevenLabs
- Optional, if you just want to use the Azure TTS you can skip this.
- Note: I have done very limited testing with 11Labs
- Create an account and login to https://elevenlabs.io/app/home
- You get 10,000 free tokens
- Depending on the plan you pay for you will get access to better voices, and the ability to create your own custom voices from audio samples.
- For pricing see https://elevenlabs.io/app/subscription
  - It is generally going to be more expensive than Azure, but with noticably better quality TTS.
  - You will likely burn through 30,000 credits of the $5/month tier pretty quickly.
  - The next tier up is $22/month (but first month is half price). It gets you 100,000 credits per month which will likely be enough for casual but consistent use.
- Note: I am currently not paying for any of the tiers, I am quite happy with the Azure TTS for my use cases right now.

2. Update character_config.json with specifics to your character.
### character_config.json Structure
- You can add as many characters as you want to this file.
- This allows you to run the application for different character configurations as easily as passing in the name of the character as the first command line argument
```json
{
    "first_character": {
        ...
    },
    "second_character": {
        ...
    }
}
```
- EG: `python3 commander_gpt first_character` or `python3 commander_gpt second_character`
- For each character you can configure things to its specific needs.
- `name`: The name of the character, used to record and load the chat history.
- `users_name`: The name of the user (you).
- `use_elevenlabs_voice`: true/false - if true the app will use 11labs for TTS, if false will use azure TTS
- `elevenlabs_voice`: If using 11labs it will use this voice, must be one available to you in 11labs.
- `azure_voice_name`: If using azure TTS this is the name of the voice it will use, it must be one available to you. Check the microsoft docs for options: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- `openai_model_name`: What OpenAI model to use, EG: gpt-4o.
- `activation_key`: The key defined to queue up getting a response from this character through OpenAI. Must be a pynput KeyCode. For special keys this is like `Key.home` but for regular keys it will just be `a` or `1`. Does not recgonize numpad keys.
- `monitor_to_screenshot`: When sending a screenshot this is the monitor id (EG: 1) to take the screenshot from. Everything on that monitor will be included.
- `history`: A dictionary of keys containing configurations for the chat history.
  - EG:
```json
"history": {
    "max_history_length_messages": 100,
    "restore_previous_history": true
}
```
- `max_history_length_messages`: The total number of prompts OpenAI will remember in its history, when this limit is passed then older prompts will be deleted. The system prompt will always be kept so that your character remembers its personality and limitations.
- `restore_previous_history`: If true, the app will (on start up) check if you have a chat history and if so load it so you can continue where you left off. If false, will start a brand new chat history, removing any prior logs for this character.
- `supported_prefixes`: A dictionary containing Azure TTS Voice Styles that the selected azure_voice_name supports.
  - It is in the format of:
```json
"supported_prefixes": {
    "(friendly)": "friendly",
    "(relieved)": "relieved",
    ...
}
```
  - You can map any prefix to any Voice Style that the azure_voice_name supports. This allows the AI to express more emotions than the azure_voice_name actually has and just map them to the smaller limited amount.
  - EG if you wanted the AI to have the same voice for (friendly) and (happy) or (shout), (shouting) and (yell) you could do this:
```json
"supported_prefixes": {
    "(friendly)": "friendly",
    "(happy)": "friendly",
    "(shouting)": "shouting",
    "(shout)": "shouting",
    "(yell)": "shouting",
}
```
- `unsupported_prefixes`: The same but is completely unused, and lets you keep a history of possible prefixes and mappings to easily copy paste in the future.
- `images`: A dictionary mapping character state to relates images of them in that state.
  - It must contain "idle", "talking", "listening", "thinking", and "error" states. They are used regardless of if using 11labs or Azure TTS.
  - Images should all be the same size for best results, most likely to match the the size of the app (default 1280x720).
  - EG:
```json
"images": {
    "idle": "noir/idle.png",
    "talking": "noir/talking.png",
    "listening": "noir/listening.png",
    "thinking": "noir/thinking.png",
    "error": "noir/error.png"
},
```
- `image_azure_voice_style_root_path`: The root path to where your character will have any additional images (can be the same as above). It is relative to the `/assets/images` folder.
- This folder must include an image for every entry in `supported_prefixes` defined above. The filenames must be without the brackets, and be .png.
  - EG:
```json
"image_azure_voice_style_root_path": "noir/"
```
- `image_alignment`: The direction in which the position is dirived from. 
  - EG: "nw" will use the top left corner for calculating distance of x and y pos.
- `image_xpos`: The x position in pixels to move the character image, derived from the above `image_alignment` location.
- `image_upos`: The xu position in pixels to move the character image, derived from the above `image_alignment` location.
- `hide_character_when_idle`: If true will hide the character when they are idle, otherwise they will always show on screen.
- `subtitles`: A dictionary of configuration options for customizing the subtitles of you and the character if you want them to show on screen.
  - EG:
```json
"subtitles": {
    "show_subtitles": true,
    "character_text_color": "pink",
    "text_outline_color": "black",
    "text_outline_width": 2,
    "font_size": 32,
    "xpos": 1240,
    "ypos": 20,
    "width": 680
},
```
- `show_subtitles`: If true then subtitles will show when you are recording a prompt from your mic, or when the character is responding. IF false, subtitles will not be displayed.
- `character_text_color`: The text colour of the character's subtitles. Can be a named colour such as "white" or a hexcode of the format "#FFFFFF".
- `text_outline_color`: The colour outline drawn around the subtitles. Can be a named colour such as "black" or a hexcode of the format "#000000".
- `text_outline_width`: The width/strength of the outline around the subtitle's text.
- `font_size`: The size of the subtitles.
- `xpos`: The x position, in pixels, for the subtitles, representing the horizontal center of the text box area.
- `ypos`: The y position, in pixels, for the subtitles, representing the top of the text box area.
- `width`: The total width, in pixels, the subtitles can fill out before wrapping to the next line.
- `first_system_message`: A dictionary containing the `role` which should always be "system", and `content` which is a list of strings.
  - You can add as much or as little as you want to the `content` prompt, and the list is only for the sake of easier formatting, they are concatenated together with `\n` characters before being sent to OpenAI.
  - It is suggested you provide the AI descriptions of who they are, what their goal is, any particular behaviour you want them to have, and any initial information they should always have available to them.
  - You can also give it information about the available azure voice styles you have mapped.

## system_config.json Structure
This is a global config that has options not related to any one particular character.
- `window_width`: The width of the app when it opens, in pixels.
- `window_height`: The height of the app when it opens, in pixels.
- `background_colour`: The background colour of the app, this allows you to chroma-key remove the background to have just the character and subtitles show up in OBS or other recording/video software. Can be a named colour such as "green" or a hexcode of the format "#00FF00".
- `mic_activation_key`: The key defined to start or stop recording from your mic. Same limitations as other key bindings.
- `enable_screenshot_toggle_key`: The key defined to toggle sending a screenshot alongside your recorded prompt from the microphone. Same limitations as other key bindings.
- `speech_recognition_language`: Used for azure speech to text, this should match the language you are speaking.
- `subtitles`: A dictionary of the same format that character_config.json uses, but for the user's subtitles when talking into the mic.

3. Add your character's images to assets/images
It must have one image for each possible state of the character, and mapped voice style. See above documentation on the character_config.json for details.
4. Start the program by running
```
.venv/bin/python3 commander_gpt.py your_characters_defined_name
```
- For example:
```
.venv/bin/python3 commander_gpt.py commander
```
- You can also start the app with more than one character and have a group conversation.
- In this case the AIs will share chat with each other so they know what the other(s) said, including your own input.
- It is recommended they have different `input_voice_start_button` keys defined so you can prompt them separately.
- For example this will introduce both the commander and alien characters defined in character_config.json to be in the same conversation:
```
.venv/bin/python3 commander_gpt.py commander alien
```
5. Press the configured key to start recording from your mic (defined in system_config.json)
6. Talk as much as you want
7. If you want a screenshot to be included with your message then you can toggle that on or off with the button defined in system_config.json
8. Wait a second or two after you are done talking to allow the speech-to-text to finish
10. Press the same key again to stop recording from your mic.
11. Press the configured key (defined in character_config.json) to send the transcribed audio to ChatGPT via OpenAI
  - Have each individual character will wait for their own activation key (in their character_config.json entry) and add themselves to a queue
  - This avoids characters talking over each other, they will wait their turn
  - This will allow having one mic input button to get input, then ask from any character you want to respond afterwards
12. when a response from OpenAI is returned it will process it and send it to either 11labs or azure to convert to audio
13. It will now play the audio of the character talking and show the image of the character.
14. When all of the characters are done talking you can return to step 5 and repeat to continue the conversation, or activate other characters to talk again.
15. When satisfied with the results you can capture the app's window in OBS or other software and add a chroma-key filter to remove the background.

## Troubleshooting
DO NOT RUN AS SUDO IF ON LINUX.
- It seems only one process can have root access to the microphone or output device at one time
- Running it as a regular user doesn't seem to have this limitation
- Tested on Linux Mint
- The program does not use the "keyboard" library anymore because that requires root access, and nothing else does
- Ensure your API keys are correct.
- Read the terminal output for error messages, they should usually tell you what is wrong.


## TODOs
- (Maybe) Make the animation match the audio playback's pace
- Improve the animation effect.
  - Framerate independent (using time delta) sin/cos instead of linear
  - Configurable speed
- Customizable font
- Investigate issue where openAI returned some characters that broke the Azure TTS (program still ran but it did not read it aloud)
- (Maybe) Would be nice to support full animations or 3D models easily
  - Could look at azure's virtual assistants as one option
- (Maybe) Instead of sending images directly to OpenAI use another service to describe the image and send OpenAI the description
  - This is because openAI refuses to identify anything that seems like it contains real people, or has other unspecified criteria that refuses to process it
- (Maybe) Parse the response from openAI and allow it to control the keyboard/mouse?
  - Might be some simpler games where that kind of logic could be possible
