from .parsers import is_valid_color


def is_valid_hex(color):
    if not isinstance(color, str):
        return False
    color = color.strip()
    if not color.startswith("#"):
        return False
    hex_part = color[1:]
    if len(hex_part) not in [3, 6]:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


def normalize_hex(color):
    color = color.strip()
    if len(color) == 4:  # #RGB -> #RRGGBB
        return "#" + "".join([c * 2 for c in color[1:]])
    return color


def validate_request(request):
    if not request.is_json:
        return "Content-Type must be application/json"

    data = request.get_json()

    if not data:
        return "No JSON data provided"

    background_color = data.get("backgroundColor")
    foreground_color = data.get("foregroundColor")

    if not background_color:
        return "backgroundColor is required"

    if not foreground_color:
        return "foregroundColor is required"

    if not is_valid_color(background_color):
        return f"Invalid backgroundColor format: {background_color}"


def validate_foreground_list(foreground_list):
    for i, color in enumerate(foreground_list):
        if not is_valid_color(color):
            return f"Invalid foregroundColor format at index {i}: {color}"
