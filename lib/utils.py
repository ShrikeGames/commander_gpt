import json
import base64
from mss import mss
from pynput import keyboard
from pynput.keyboard import KeyCode


def read_config_file(filepath: str) -> str:
    json_result = None

    with open(filepath) as f:
        json_result = json.load(f)

    return json_result


def write_json_file(filepath: str, data: dict) -> str:
    with open(filepath, "w") as file:
        file.write(str(json.dumps(data)))


def button_released(key: KeyCode, to_match_key: str = "7"):
    if to_match_key is None:
        return
    # For some ungodly reason pynput does not give us any reasonable access to the character or vk or anything
    # no the answers online aren't true (at least not on the latest)
    # Hacky workaround, force to strings and replace any quotes (sometimes it adds single quotes or double quote or none at all)
    # still doesn't really support numpad numbers (they show up as just regular numbers)
    key_string = f"{KeyCode.from_char(key)}".replace("'", "").replace('"', "")
    # print(key_string)
    to_match_key_string = f"{KeyCode.from_char(to_match_key)}".replace("'", "").replace(
        '"', ""
    )
    if key_string == to_match_key_string:
        return False
    return True


def wait_until_key(key_to_match: str = "7"):
    with keyboard.Listener(
        on_release=lambda key: button_released(key=key, to_match_key=key_to_match)
    ) as listener:
        listener.join()


def screenshot_encode_monitor(monitor: int = 1):
    with mss() as sct:
        filename = sct.shot(
            mon=monitor, output=f"assets/images/screenshots/monitor_{monitor}.png"
        )
        print(filename)

    with open(filename, "rb") as f:
        data = f.read()
    base64_image = base64.b64encode(data).decode("utf-8")
    return base64_image


def display_text_with_wrap(
    screen, font, text, box_width, xpos, ypos, color, outline_color=(0, 0, 0)
):
    # Create an empty list to store the wrapped lines
    wrapped_lines = []

    # Split the text into words
    words = text.split()

    # Iterate through the words
    current_line = []
    for word in words:
        # Append the current word to the current line
        current_line.append(word)

        # Get the rendered width of the current line
        line_width = font.render(" ".join(current_line), True, color).get_width()

        # If the line width exceeds the box width, wrap the text
        if line_width > box_width:
            # Remove the last word from the current line
            current_line.pop()

            # Add the previous line to the list of wrapped lines
            wrapped_lines.append(" ".join(current_line))

            # Start a new line with the last word
            current_line = [word]

    # Add the last line to the list of wrapped lines
    wrapped_lines.append(" ".join(current_line))

    # Render the wrapped lines
    for i, line in enumerate(wrapped_lines):
        # Render the line
        outline_surface = font.render(line, True, outline_color)
        line_surface = font.render(line, True, color)

        # Define the outline offset
        outline_offset = 3

        # Calculate the y-coordinate for each line
        y = i * 45

        # Render the outline with different offsets
        for outline_x in range(-outline_offset, outline_offset + 1):
            for outline_y in range(-outline_offset, outline_offset + 1):
                if outline_x == 0 and outline_y == 0:
                    continue  # Skip the center of the outline
                screen.blit(outline_surface, (xpos + outline_x, ypos + y + outline_y))

        # Draw the line on the screen
        screen.blit(line_surface, (xpos, ypos + y))
