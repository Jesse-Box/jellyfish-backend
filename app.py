import sentry_sdk
from flask import Flask, jsonify
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

        for r in range(0, 256, 8):
            for g in range(0, 256, 8):
                for b in range(0, 256, 8):
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


def generate_alpha_scale(hex_scale, background_hex="#ffffff", label_prefix="blueA"):
    background_rgb = hex_to_rgb(background_hex)
    output = []

    for i, hex in enumerate(hex_scale, 1):
        target_rgb = hex_to_rgb(hex)
        match = find_best_rgba_match(tuple(target_rgb), tuple(background_rgb))
        r, g, b, a = match
        output.append(f"--{label_prefix}{i}: rgba({r}, {g}, {b}, {a});")

    return output


@flask_app.route("/api/data/colors/")
def get_target_color():
    with sentry_sdk.start_transaction(name="test"):
        color_scale = [
            "#F7F7FF",
            "#EDEEFF",
            "#E2E2FF",
            "#D4D3FF",
            "#C5C3FF",
            "#B7B2FF",
            "#A79EFF",
            "#988AFF",
            "#7F66FF",
            "#7553FF",
            "#653DE9",
            "#5827D6",
            "#4C0FC0",
            "#3F00A7",
            "#31008B",
            "#24006C",
        ]

        output = generate_alpha_scale(color_scale, "#ffffff", "blueA")
        return jsonify(output)


if __name__ == "__main__":
    flask_app.run(host="127.0.0.1", port=5000, debug=True)
