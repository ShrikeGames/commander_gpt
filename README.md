# commander_gpt
An attempt to integrate OpenAI, Azure TTS, and other tech to have a conversation with a fictional character.

Based on DougDoug's https://github.com/DougDougGithub/Babagaboosh/tree/main


pip install -r requirements.txt

Create a token_config.json in the configs folder with the following format
{
    "elevenlabs_api_key": "YOUR KEY HERE",
    "azure_tts_key": "YOUR KEY HERE",
    "azure_tts_region": "YOUR REGION HERE",
    "openai_api_key": "YOUR KEY HERE"
}

Update character_config.json with specifics to your character.
You can switch between using 11lab voices or not (if not then it will use azure TTS instead)
11labs seems a lot more expensive, and azure gives you plenty of monthly credits.

DO NOT RUN AS SUDO IF ON LINUX.
Mainly because you'll have to deal with endless impossible to solve issues around audio devices already being in use when you have OBS open at the same time (or music playing, etc).