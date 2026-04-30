import math
import re

# ── Format detection ──────────────────────────────────────────────────────────

_PATTERNS = {
    "hex":    re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"),
    "rgb":    re.compile(r"^rgb\(", re.IGNORECASE),
    "hsl":    re.compile(r"^hsl\(", re.IGNORECASE),
    "hwb":    re.compile(r"^hwb\(", re.IGNORECASE),
    "oklch":  re.compile(r"^oklch\(", re.IGNORECASE),
    "lch":    re.compile(r"^lch\(", re.IGNORECASE),
    "lab":    re.compile(r"^lab\(", re.IGNORECASE),
}


def detect_format(color):
    color = color.strip()
    for fmt, pattern in _PATTERNS.items():
        if pattern.match(color):
            return fmt
    return None


def is_valid_color(color):
    return detect_format(color) is not None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_values(color):
    """Extract numeric values from a CSS color function, ignoring % and /."""
    inner = re.sub(r"^[a-z]+\(|\)$", "", color.strip(), flags=re.IGNORECASE)
    tokens = re.split(r"[\s,/]+", inner.strip())
    return [float(t.rstrip("%")) for t in tokens if t]


def _clamp(value, lo=0, hi=255):
    return max(lo, min(hi, value))


def _linearize(c):
    """sRGB channel [0,1] → linear light."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gamma(c):
    """Linear light → sRGB channel [0,1]."""
    if c <= 0.0:
        return 0.0
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1 / 2.4)) - 0.055


# ── RGB ↔ HSL ─────────────────────────────────────────────────────────────────

def _hsl_to_rgb(h, s, l):
    """h [0,360), s [0,1], l [0,1] → (r, g, b) 0-255."""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:   r1, g1, b1 = c, x, 0
    elif h < 120: r1, g1, b1 = x, c, 0
    elif h < 180: r1, g1, b1 = 0, c, x
    elif h < 240: r1, g1, b1 = 0, x, c
    elif h < 300: r1, g1, b1 = x, 0, c
    else:         r1, g1, b1 = c, 0, x
    return (round((r1 + m) * 255), round((g1 + m) * 255), round((b1 + m) * 255))


def _rgb_to_hsl(r, g, b):
    """r, g, b 0-255 → (h [0,360), s [0,1], l [0,1])."""
    r_, g_, b_ = r / 255, g / 255, b / 255
    mx, mn = max(r_, g_, b_), min(r_, g_, b_)
    l = (mx + mn) / 2
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (1 - abs(2 * l - 1))
    if mx == r_:   h = 60 * (((g_ - b_) / d) % 6)
    elif mx == g_: h = 60 * ((b_ - r_) / d + 2)
    else:          h = 60 * ((r_ - g_) / d + 4)
    return h, s, l


# ── RGB ↔ HWB ─────────────────────────────────────────────────────────────────

def _hwb_to_rgb(h, w, b):
    """h [0,360), w [0,1], b [0,1] → (r, g, b) 0-255."""
    w_, b_ = w, b
    if w_ + b_ >= 1:
        grey = round(w_ / (w_ + b_) * 255)
        return grey, grey, grey
    r, g, bv = _hsl_to_rgb(h, 1.0, 0.5)
    r = round(r / 255 * (1 - w_ - b_) * 255 + w_ * 255)
    g = round(g / 255 * (1 - w_ - b_) * 255 + w_ * 255)
    bv = round(bv / 255 * (1 - w_ - b_) * 255 + w_ * 255)
    return r, g, bv


def _rgb_to_hwb(r, g, b):
    """r, g, b 0-255 → (h [0,360), w [0,1], b [0,1])."""
    h, _, _ = _rgb_to_hsl(r, g, b)
    w = min(r, g, b) / 255
    bk = 1 - max(r, g, b) / 255
    return h, w, bk


# ── RGB ↔ XYZ (D65) ───────────────────────────────────────────────────────────

def _rgb_to_xyz(r, g, b):
    r_, g_, b_ = _linearize(r / 255), _linearize(g / 255), _linearize(b / 255)
    x = 0.4124564 * r_ + 0.3575761 * g_ + 0.1804375 * b_
    y = 0.2126729 * r_ + 0.7151522 * g_ + 0.0721750 * b_
    z = 0.0193339 * r_ + 0.1191920 * g_ + 0.9503041 * b_
    return x, y, z


def _xyz_to_rgb(x, y, z):
    r_ =  3.2404542 * x - 1.5371385 * y - 0.4985314 * z
    g_ = -0.9692660 * x + 1.8760108 * y + 0.0415560 * z
    b_ =  0.0556434 * x - 0.2040259 * y + 1.0572252 * z
    return (
        _clamp(round(_gamma(r_) * 255)),
        _clamp(round(_gamma(g_) * 255)),
        _clamp(round(_gamma(b_) * 255)),
    )


# ── RGB ↔ Lab ─────────────────────────────────────────────────────────────────

_D65 = (0.95047, 1.00000, 1.08883)
_EPSILON = 216 / 24389
_KAPPA = 24389 / 27


def _xyz_to_lab(x, y, z):
    def f(t):
        return t ** (1 / 3) if t > _EPSILON else (_KAPPA * t + 16) / 116
    fx, fy, fz = f(x / _D65[0]), f(y / _D65[1]), f(z / _D65[2])
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _lab_to_xyz(L, a, b):
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    x = _D65[0] * (fx ** 3 if fx ** 3 > _EPSILON else (116 * fx - 16) / _KAPPA)
    y = _D65[1] * (((L + 16) / 116) ** 3 if L > _KAPPA * _EPSILON else L / _KAPPA)
    z = _D65[2] * (fz ** 3 if fz ** 3 > _EPSILON else (116 * fz - 16) / _KAPPA)
    return x, y, z


def _rgb_to_lab(r, g, b):
    return _xyz_to_lab(*_rgb_to_xyz(r, g, b))


def _lab_to_rgb(L, a, b):
    return _xyz_to_rgb(*_lab_to_xyz(L, a, b))


# ── RGB ↔ LCh ─────────────────────────────────────────────────────────────────

def _rgb_to_lch(r, g, b):
    L, a, bv = _rgb_to_lab(r, g, b)
    C = math.sqrt(a ** 2 + bv ** 2)
    H = math.degrees(math.atan2(bv, a)) % 360
    return L, C, H


def _lch_to_rgb(L, C, H):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    return _lab_to_rgb(L, a, b)


# ── RGB ↔ OKLab / OKLCh ──────────────────────────────────────────────────────

def _rgb_to_oklab(r, g, b):
    r_, g_, b_ = _linearize(r / 255), _linearize(g / 255), _linearize(b / 255)
    l = 0.4122214708 * r_ + 0.5363325363 * g_ + 0.0514459929 * b_
    m = 0.2119034982 * r_ + 0.6806995451 * g_ + 0.1073969566 * b_
    s = 0.0883024619 * r_ + 0.2817188376 * g_ + 0.6299787005 * b_
    l_, m_, s_ = l ** (1/3), m ** (1/3), s ** (1/3)
    L =  0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a =  1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bv = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, a, bv


def _oklab_to_rgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r_ =  4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g_ = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_ = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return (
        _clamp(round(_gamma(r_) * 255)),
        _clamp(round(_gamma(g_) * 255)),
        _clamp(round(_gamma(b_) * 255)),
    )


def _rgb_to_oklch(r, g, b):
    L, a, bv = _rgb_to_oklab(r, g, b)
    C = math.sqrt(a ** 2 + bv ** 2)
    H = math.degrees(math.atan2(bv, a)) % 360
    return L, C, H


def _oklch_to_rgb(L, C, H):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    return _oklab_to_rgb(L, a, b)


# ── Public API ────────────────────────────────────────────────────────────────

def parse_to_rgb(color):
    """Parse any supported color string to (r, g, b) tuple, 0-255."""
    color = color.strip()
    fmt = detect_format(color)

    if fmt == "hex":
        hex_str = color.replace("#", "")
        if len(hex_str) == 3:
            hex_str = "".join(c * 2 for c in hex_str)
        n = int(hex_str, 16)
        return (n >> 16) & 255, (n >> 8) & 255, n & 255

    vals = _parse_values(color)

    if fmt == "rgb":
        return _clamp(round(vals[0])), _clamp(round(vals[1])), _clamp(round(vals[2]))

    if fmt == "hsl":
        return _hsl_to_rgb(vals[0] % 360, vals[1] / 100, vals[2] / 100)

    if fmt == "hwb":
        return _hwb_to_rgb(vals[0] % 360, vals[1] / 100, vals[2] / 100)

    if fmt == "lab":
        return _lab_to_rgb(vals[0], vals[1], vals[2])

    if fmt == "lch":
        return _lch_to_rgb(vals[0], vals[1], vals[2])

    if fmt == "oklch":
        # L may be expressed as % (e.g. 40.1% → 0.401) — already stripped by _parse_values
        # Detect if original string had % on L
        inner = re.sub(r"^oklch\(|\)$", "", color.strip(), flags=re.IGNORECASE)
        first_token = re.split(r"[\s,/]+", inner.strip())[0]
        L = vals[0] / 100 if "%" in first_token else vals[0]
        return _oklch_to_rgb(L, vals[1], vals[2])

    raise ValueError(f"Unsupported color format: {color}")


def rgb_to_format(r, g, b, a, fmt, original=None):
    """
    Convert (r, g, b, a) back to the given format string.
    `original` is the original input string (used to preserve % notation in oklch).
    """
    alpha_str = f" / {a}"

    if fmt == "hex":
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        if a == 1:
            return hex_color
        return f"rgba({r}, {g}, {b}, {a})"

    if fmt == "rgb":
        return f"rgb({r} {g} {b}{alpha_str})"

    if fmt == "hsl":
        h, s, l = _rgb_to_hsl(r, g, b)
        return f"hsl({h:.1f} {s * 100:.1f}% {l * 100:.1f}%{alpha_str})"

    if fmt == "hwb":
        h, w, bk = _rgb_to_hwb(r, g, b)
        return f"hwb({h:.1f} {w * 100:.1f}% {bk * 100:.1f}%{alpha_str})"

    if fmt == "lab":
        L, av, bv = _rgb_to_lab(r, g, b)
        return f"lab({L:.3f} {av:.3f} {bv:.3f}{alpha_str})"

    if fmt == "lch":
        L, C, H = _rgb_to_lch(r, g, b)
        return f"lch({L:.3f} {C:.3f} {H:.3f}{alpha_str})"

    if fmt == "oklch":
        L, C, H = _rgb_to_oklch(r, g, b)
        # Preserve % notation if original used it
        use_percent = original and re.match(r"oklch\(\s*[\d.]+%", original, re.IGNORECASE)
        l_str = f"{L * 100:.2f}%" if use_percent else f"{L:.4f}"
        return f"oklch({l_str} {C:.4f} {H:.3f}{alpha_str})"

    raise ValueError(f"Unsupported format: {fmt}")
