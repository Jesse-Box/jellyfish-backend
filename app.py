from functools import cache

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/api/data/")
def get_data():
    return jsonify({"message": "Hello from Flask!", "status": "success"})


@cache
def hex_to_rgb(hex):
    hex = hex.replace("#", "")
    big_int = int(hex, 16)
    return [
        (big_int >> 16) & 255,
        (big_int >> 8) & 255,
        big_int & 255,
    ]


@cache
def blend_channel(bg, fg, alpha):
    return round(alpha * fg + (1 - alpha) * bg)


@cache
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

                    if error < min_error:
                        min_error = error
                        best_match = [r, g, b, round(alpha, 2)]

                    if error < 2:
                        return best_match
    return best_match


def generate_alpha_scale(hex_scale, background_hex="#FFF", label_prefix="blueA"):
    background_rgb = hex_to_rgb(background_hex)
    output = []

    for i, hex in enumerate(hex_scale, 1):
        target_rgb = hex_to_rgb(hex)
        match = find_best_rgba_match(tuple(target_rgb), tuple(background_rgb))
        r, g, b, a = match
        output.append(f"--{label_prefix}{i}: rgba({r}, {g}, {b}, {a});")

    return output


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


@app.route("/api/data/targetColor/")
def get_target_color():
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

    output = generate_alpha_scale(color_scale, "#FFF", "blueA")
    return jsonify(output)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
