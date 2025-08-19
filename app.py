import sentry_sdk
from flask import Flask, jsonify, request
from flask_cors import CORS
from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

sentry_sdk.init(
    dsn="https://5a289d9c36119a97d6c4b2a0c687aa5d@o925438.ingest.us.sentry.io/4509869299073024",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profile_session_sample_rate to 1.0 to profile 100%
    # of profile sessions.
    profiles_sample_rate=1.0,
)

# Create Flask app
flask_app = Flask(__name__)

# Wrap with Sentry middleware
app = SentryWsgiMiddleware(flask_app)

CORS(flask_app)  # CORS should be applied to the Flask app, not the middleware


@flask_app.route("/")
def hello_world():
    1 / 0  # raises an error
    return "<p>Hello, World!</p>"


@flask_app.route("/api/data/")
def get_data():
    return jsonify({"message": "Hello from Flask!", "status": "success"})


def hex_to_rgb(hex):
    hex = hex.replace("#", "")
    big_int = int(hex, 16)
    return [
        (big_int >> 16) & 255,
        (big_int >> 8) & 255,
        big_int & 255,
    ]


def blend_channel(bg, fg, alpha):
    return round(alpha * fg + (1 - alpha) * bg)


def find_best_rgba_match(target_rgb, background_rgb, alpha_steps=100):
    best_match = None
    min_error = float("inf")

    for i in range(1, alpha_steps + 1):
        alpha = i / alpha_steps

        # Calculate optimal foreground RGB mathematically for this alpha
        optimal_fg = []
        for j in range(3):
            # Solve: target = alpha * fg + (1 - alpha) * bg
            # Therefore: fg = (target - (1 - alpha) * bg) / alpha
            fg_exact = (target_rgb[j] - (1 - alpha) * background_rgb[j]) / alpha
            optimal_fg.append(fg_exact)

        # Find the nearest quantized RGB values (multiples of 8) to test
        # We'll test a small 3x3x3 grid around the optimal point
        center_r = max(0, min(248, round(optimal_fg[0] / 8) * 8))
        center_g = max(0, min(248, round(optimal_fg[1] / 8) * 8))
        center_b = max(0, min(248, round(optimal_fg[2] / 8) * 8))

        # Test candidates in a 3x3x3 grid around the center
        for r_offset in [-8, 0, 8]:
            for g_offset in [-8, 0, 8]:
                for b_offset in [-8, 0, 8]:
                    r = max(0, min(248, center_r + r_offset))
                    g = max(0, min(248, center_g + g_offset))
                    b = max(0, min(248, center_b + b_offset))

                    blended = [
                        blend_channel(background_rgb[0], r, alpha),
                        blend_channel(background_rgb[1], g, alpha),
                        blend_channel(background_rgb[2], b, alpha),
                    ]

                    error = 0
                    for idx, val in enumerate(blended):
                        error += pow(val - target_rgb[idx], 2)

                    if error < min_error or (
                        error == min_error and alpha > best_match[3]
                        if best_match
                        else False
                    ):
                        min_error = error
                        # Match JavaScript's parseFloat(alpha.toFixed(2))
                        alpha_formatted = float(f"{alpha:.2f}")
                        # Format 1.0 as 1 to match JavaScript
                        if alpha_formatted == 1.0:
                            alpha_formatted = 1
                        best_match = [r, g, b, alpha_formatted]

                    if error < 2:
                        return best_match
    return best_match


def calculate_transparent_colors(foreground_colors, background_color):
    """
    Calculate transparent RGBA values for given foreground colors against a background.

    Args:
        foreground_colors: str or list of str - hex color(s) to convert
        background_color: str - hex background color

    Returns:
        list of dict - each containing original hex and calculated rgba
    """
    # Ensure foreground_colors is a list
    if isinstance(foreground_colors, str):
        foreground_colors = [foreground_colors]

    background_rgb = hex_to_rgb(background_color)
    results = []

    for hex_color in foreground_colors:
        target_rgb = hex_to_rgb(hex_color)
        match = find_best_rgba_match(tuple(target_rgb), tuple(background_rgb))
        r, g, b, a = match

        results.append(
            {
                "originalHex": hex_color,
                "rgba": f"rgba({r}, {g}, {b}, {a})",
                "rgbaValues": {"r": r, "g": g, "b": b, "a": a},
            }
        )

    return results


@flask_app.route("/api/colors/", methods=["POST"], strict_slashes=False)
def process_colors():
    """
    Process foreground and background colors to calculate transparent RGBA values.

    Expected JSON payload:
    {
        "backgroundColor": "#ffffff",
        "foregroundColor": "#ff0000" or ["#ff0000", "#00ff00", "#0000ff"]
    }

    Returns:
    {
        "backgroundColor": "#ffffff",
        "results": [
            {
                "originalHex": "#ff0000",
                "rgba": "rgba(255, 0, 0, 1)",
                "rgbaValues": {"r": 255, "g": 0, "b": 0, "a": 1}
            }
        ],
        "status": "success"
    }
    """
    try:
        # Validate request content type
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json", "status": "error"}
            ), 400

        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({"error": "No JSON data provided", "status": "error"}), 400

        background_color = data.get("backgroundColor")
        foreground_color = data.get("foregroundColor")

        if not background_color:
            return jsonify(
                {"error": "backgroundColor is required", "status": "error"}
            ), 400

        if not foreground_color:
            return jsonify(
                {"error": "foregroundColor is required", "status": "error"}
            ), 400

        # Validate hex color format
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

        # Normalize 3-digit hex to 6-digit
        def normalize_hex(color):
            color = color.strip()
            if len(color) == 4:  # #RGB -> #RRGGBB
                return "#" + "".join([c * 2 for c in color[1:]])
            return color

        # Validate background color
        if not is_valid_hex(background_color):
            return jsonify(
                {
                    "error": f"Invalid backgroundColor format: {background_color}. Expected format: #ffffff or #fff",
                    "status": "error",
                }
            ), 400

        # Validate foreground color(s)
        foreground_list = (
            foreground_color
            if isinstance(foreground_color, list)
            else [foreground_color]
        )

        for i, color in enumerate(foreground_list):
            if not is_valid_hex(color):
                return jsonify(
                    {
                        "error": f"Invalid foregroundColor format at index {i}: {color}. Expected format: #ffffff or #fff",
                        "status": "error",
                    }
                ), 400

        # Normalize colors
        background_color = normalize_hex(background_color)
        if isinstance(foreground_color, list):
            foreground_color = [normalize_hex(color) for color in foreground_color]
        else:
            foreground_color = normalize_hex(foreground_color)

        # Calculate transparent colors
        with sentry_sdk.start_transaction(name="calculate_transparent_colors"):
            results = calculate_transparent_colors(foreground_color, background_color)

        return jsonify(
            {
                "backgroundColor": background_color,
                "results": results,
                "status": "success",
            }
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        return jsonify(
            {"error": f"Internal server error: {str(e)}", "status": "error"}
        ), 500


if __name__ == "__main__":
    flask_app.run(host="127.0.0.1", port=5000, debug=True)
