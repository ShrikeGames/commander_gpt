import json
import base64
from mss import mss
from pynput import keyboard
from pynput.keyboard import KeyCode


def read_config_file(filepath: str) -> dict:
    """Reads a JSON configuration file and returns its contents.

    Args:
        filepath (str): The path to the configuration file.

    Returns:
        dict: The parsed JSON data as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(filepath) as f:
        json_result = json.load(f)

    return json_result


def write_json_file(filepath: str, data: dict) -> None:
    """Writes a dictionary as JSON data to a specified file.

    Args:
        filepath (str): The path where the JSON data will be saved.
        data (dict): The dictionary containing data to write to the file.

    Raises:
        IOError: If there is an error opening or writing to the file.
    """
    with open(filepath, "w") as file:
        file.write(str(json.dumps(data)))


def button_released(key: KeyCode, to_match_key: str = "7") -> bool:
    """Checks if the released key matches the specified key.

    Args:
        key (KeyCode): The key that was released.
        to_match_key (str, optional): The key to match (default is "7").

    Returns:
        bool: False if the released key matches the specified key, True otherwise.

    Notes:
        This function contains a workaround for issues with pynput not providing
        a reasonable way to access key characters or virtual key codes.
    """
    if to_match_key is None:
        return False

    key_string = f"{KeyCode.from_char(key)}".replace("'", "").replace('"', "")
    to_match_key_string = f"{KeyCode.from_char(to_match_key)}".replace("'", "").replace(
        '"', ""
    )

    if key_string == to_match_key_string:
        return False
    return True


def wait_until_key(key_to_match: str = "7") -> None:
    """Waits until a specified key is released.

    Args:
        key_to_match (str, optional): The key to wait for (default is "7").

    This function uses the `pynput` listener to monitor key events and halts
    execution until the specified key is released.
    """
    with keyboard.Listener(
        on_release=lambda key: button_released(key=key, to_match_key=key_to_match)
    ) as listener:
        listener.join()


def screenshot_encode_monitor(monitor: int = 1) -> str:
    """Captures a screenshot of the specified monitor and encodes it to a base64 string.

    Args:
        monitor (int, optional): The monitor number to capture (default is 1).

    Returns:
        str: The base64-encoded image of the screenshot.

    This function uses the `mss` library to capture the screen and the `base64`
    library to encode the screenshot data.
    """
    with mss() as sct:
        filename = sct.shot(
            mon=monitor, output=f"assets/images/screenshots/monitor_{monitor}.png"
        )
        print(filename)

    with open(filename, "rb") as f:
        data = f.read()
    base64_image = base64.b64encode(data).decode("utf-8")
    return base64_image
