from twitchio.ext import commands
from twitchio import Message
from .ai_character import AICharacter
import random


class TwitchBot(commands.Bot):
    """A TwitchBot that connects to a channel and keeps a history of the latest chat messages."""

    def __init__(
        self,
        twitch_channel_name: str = None,
        twitch_access_token: str = None,
        chat_history_length: int = 50,
    ):
        """Initializes the TwitchBot for the given channel.

        Arguments:
            twitch_channel_name (str): The name of the twitch channel which should be stored in system_config.json
            twitch_access_token (str): The access token for the bot account, which should be stored in token_config.json and created in the dev.twitch.tv interface.
            chat_history_length (int): How many chat messages should the bot remember.
        """
        if not twitch_channel_name:
            error_message = "Twitch channel name not defined in system_config.json"
            raise Exception(error_message)
        if not twitch_access_token:
            error_message = "Twitch access token not defined in token_config.json "
            raise Exception(error_message)

        # connect to the twitch channel using access token
        super().__init__(
            token=twitch_access_token,
            prefix="!",
            initial_channels=[twitch_channel_name],
        )
        #
        self.chat_history_length = chat_history_length
        self.chat_history = []

    # We use a listener in our Component to display the messages received.
    async def event_message(self, message: Message) -> None:
        print(f"{message.author.display_name}: {message.content}")
        self.chat_history.append(message)
        if len(self.chat_history) > self.chat_history_length:
            # remove the oldest chat history
            self.chat_history.pop(0)

        # we don't actually have any commands right now but in the future this needs to be called
        await self.handle_commands(message)

    def pick_random_message(
        self, ai_character: AICharacter, remove_after: bool = True
    ) -> str:
        """Picks a random message from the stored history and returns it.
        Optionally removes the message from history so it cannot be picked a second time.

        Arguments:
            remove_after (bool): Remove the randomly selected message from the chat history. Defaults to True.

        Returns:
            str: A message from twitch chat.
        """
        if len(self.chat_history) <= 0:
            return None
        # [inclusive, exclusive) random number
        random_message_index = random.randrange(0, len(self.chat_history))
        random_message: Message = self.chat_history[random_message_index]
        extra_info = ""
        if random_message.first:
            extra_info = "[First Time Chatter]"
        # tell the ai character who is talking
        ai_character.users_name = random_message.author.display_name
        random_message_formatted_string = f"{extra_info}\n{random_message.content}"
        if remove_after:
            # remove the message from history so it can't be picked again
            self.chat_history.pop(random_message_index)

        return random_message_formatted_string
