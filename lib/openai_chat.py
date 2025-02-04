from openai import OpenAI
from rich import print
from .utils import screenshot_encode_monitor
from transformers import AutoTokenizer, AutoModelForCausalLM

class OpenAiManager:
    """Manager for interacting with OpenAI's GPT models, handling chat history and image input."""

    def __init__(self, openai_api_key: str):
        """Initializes the OpenAiManager with an API key for OpenAI access.

        Args:
            openai_api_key (str): The API key for accessing OpenAI services.

        Raises:
            Exception: If the OpenAI client setup fails.
        """
        self.chat_history = []
        try:
            self.client = OpenAI(api_key=openai_api_key)
        except Exception as e:
            print("Failed to setup OpenAI")
            exit(e)

    def chat_with_history(
        self,
        ai_character,
        prompt="",
        monitor_to_screenshot=-1,
        max_history_length_messages=100,
        model="gpt-4o",
        other_ai_characters=[],
    ):
        """Asks a question to the OpenAI model, including the full conversation history, with optional image input.

        Args:
            ai_character (AICharacter): The character who is being prompted to talk.
            prompt (str, optional): The question or prompt to send to the model. Defaults to an empty string.
            monitor_to_screenshot (int, optional): The monitor number to take a screenshot from. If positive, the screenshot will be included. Defaults to -1 (no screenshot).
            max_history_length_messages (int, optional): The maximum number of messages to keep in the conversation history. Older messages will be discarded. Defaults to 100.
            model (str, optional): The model to use for the completion request. Defaults to "gpt-4o".
            other_ai_characters (list[AICharacter]): A list of other characters to also give the chat history to.
        Returns:
            str: The model's response to the prompt.

        Raises:
            None: Prints errors or details if the prompt is empty or if history exceeds the configured limit.
        """
        # if no prompt was given the AI should be told to just continue.
        if not prompt:
            prompt = "Continue."

        chat_history_to_send = self.chat_history.copy()
        # Add our prompt into the chat history which will not include images
        prompt_for_our_history = [
            {"type": "text", "text": f"\n[{ai_character.users_name}]\n{prompt}"}
        ]
        # prompt we will send which includes text history + any new image
        prompt_json = []
        if monitor_to_screenshot > 0:
            print(f"[yellow]\nIncluding screenshot of monitor {monitor_to_screenshot}")
            base64_image = screenshot_encode_monitor(monitor_to_screenshot)
            prompt_json.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                }
            )
        # Add the text prompt as well
        prompt_json.append({"type": "text", "text": prompt})

        self.chat_history.append({"role": "user", "content": prompt_for_our_history})
        chat_history_to_send.append({"role": "user", "content": prompt_json})
        # share what we said to the other AI's as well
        for other_ai_character in other_ai_characters:
            other_ai_character.openai_manager.chat_history.append(
                {"role": "user", "content": prompt_for_our_history}
            )

        # Trim the chat history if it exceeds the maximum length
        if len(self.chat_history) > max_history_length_messages:
            print(
                "[yellow]\nChat history is longer than configured limit, starting to remove older entries."
            )
            # remove the 2nd history entry, leaving the 1st because it is the system message with their personality
            # and we don't want them to forget that
            self.chat_history.pop(1)
        if ai_character.local_model_name:
            print(f"[yellow]\nAsking {ai_character.local_model_name} a question...")
            local_model = AutoModelForCausalLM.from_pretrained(ai_character.local_model_name)
            local_tokenizer = AutoTokenizer.from_pretrained(ai_character.local_model_name)
            if len(self.chat_history) <= 1:
                print("First message sent, so including system prompt as well.")
                prompt = f"{self.chat_history[0]['content']['text']}\n{prompt}"
            input_ids = local_tokenizer.encode(prompt, return_tensors="pt")
            local_output = local_model.generate(input_ids, max_new_tokens=50)
            openai_answer = local_tokenizer.decode(local_output[0], skip_special_tokens=True)
            # Add the model's response to the chat history
            self.chat_history.append(
                {
                    "role": "assistant",
                    "content": openai_answer,
                }
            )
            # share what we said to the other AI's as well
            for other_ai_character in other_ai_characters:
                other_ai_character.openai_manager.chat_history.append(
                    {
                        "role": "user",
                        "content": f"\n[{ai_character.name}]\n{openai_answer}",
                    }
                )
        else:
            print("[yellow]\nAsking ChatGPT a question...")
            completion = self.client.chat.completions.create(
                model=model, messages=chat_history_to_send
            )
            # Add the model's response to the chat history
            self.chat_history.append(
                {
                    "role": completion.choices[0].message.role,
                    "content": completion.choices[0].message.content,
                }
            )
            # share what we said to the other AI's as well
            for other_ai_character in other_ai_characters:
                other_ai_character.openai_manager.chat_history.append(
                    {
                        "role": "user",
                        "content": f"\n[{ai_character.name}]\n{completion.choices[0].message.content}",
                    }
                )

            # Process and return the answer
            openai_answer = completion.choices[0].message.content
        
        print(f"[green]\n{openai_answer}\n")
        return openai_answer
