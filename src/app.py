import sentry_sdk
from flask import Flask, jsonify, request
from flask_cors import CORS

from colors import calculate_transparent_colors
from validation import (
    normalize_hex,
    validate_foreground_list,
    validate_request,
)

sentry_sdk.init(
    dsn="https://5a289d9c36119a97d6c4b2a0c687aa5d@o925438.ingest.us.sentry.io/4509869299073024",
    send_default_pii=True,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

# Create Flask app
jellyfish = Flask("jellyfish")


CORS(jellyfish)


@jellyfish.route("/")
def get_data():
    return jsonify({"message": "Jellyfish Backend", "status": "success"})


@jellyfish.route("/api/colors/", methods=["POST"], strict_slashes=False)
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
        error = validate_request(request)
        if error:
            return jsonify({"error": error, "status": "error"}), 400

        # Validate foreground color(s)
        foreground_color = request.get_json().get("foregroundColor")
        foreground_list = (
            foreground_color
            if isinstance(foreground_color, list)
            else [foreground_color]
        )
        error = validate_foreground_list(foreground_list)
        if error:
            return jsonify({"error": error, "status": "error"}), 400

        # Normalize colors
        background_color = request.get_json().get("backgroundColor")
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
    jellyfish.run(host="127.0.0.1", port=5000, debug=True)
