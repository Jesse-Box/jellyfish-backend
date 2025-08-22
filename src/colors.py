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
