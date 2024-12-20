from openai import OpenAI
import os
from rich import print
from .utils import screenshot_encode_monitor

class OpenAiManager:
    
    def __init__(self, openai_api_key:str):
        self.chat_history = []
        try:
            self.client = OpenAI(api_key=openai_api_key)
        except Exception as e:
            print("Failed to setup open ai")
            exit(e)
    
    # Asks a question that includes the full conversation history
    def chat_with_history(self, prompt="", monitor_to_screenshot=-1, max_history_length_messages=100, model="gpt-4o"):
        if not prompt:
            print("Didn't receive input!")
            return

        chat_history_to_send = self.chat_history.copy()
        # Add our prompt into the chat history which will not include images
        prompt_for_our_history = [{"type": "text", "text": prompt}]
        # prompt we will send which includes text history + any new image
        prompt_json = []
        if monitor_to_screenshot > 0:
            print(f"[yellow]\nincluding screenshot of monitor {monitor_to_screenshot}")
            base64_image = screenshot_encode_monitor(monitor_to_screenshot)
            prompt_json.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                },
            })
        # have the text prompt be second to see if it can still respond if it doesn't like the image
        prompt_json.append({"type": "text", "text": prompt})
        
        self.chat_history.append({"role": "user", "content": prompt_for_our_history})
        chat_history_to_send.append({"role": "user", "content": prompt_json})

        if len(self.chat_history) > max_history_length_messages:
            print("[yellow]\nChat history is longer than configured limit, starting to remove older entries.")
            # remove the 2nd history entry, leaving the 1st because it is the system message with their personality
            # and we don't want them to forget that
            self.chat_history.pop(1)
        #print("prompt_json: ", self.chat_history)

        print("[yellow]\nAsking ChatGPT a question...")
        completion = self.client.chat.completions.create(
          model=model,
          messages=chat_history_to_send
        )

        # Add this answer to our chat history
        self.chat_history.append({"role": completion.choices[0].message.role, "content": completion.choices[0].message.content})

        # Process the answer
        openai_answer = completion.choices[0].message.content
        print(f"[green]\n{openai_answer}\n")
        return openai_answer
   
