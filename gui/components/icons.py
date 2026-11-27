from typing import Dict, Tuple, Optional
from PIL import Image, ImageDraw
import customtkinter as ctk

_PIL_CACHE: Dict[str, Tuple[Image.Image, Image.Image]] = {}

def _draw_icon(name: str, stroke_hex: str, size: int = 32) -> Image.Image:
    """Draw a clean, crisp vector-style icon on a high-res 32x32 RGBA canvas."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = 2 # 2px stroke on 32x32 translates to 1px on 16x16

    if name == "monitor":
        # Screen box + stand + base
        d.rounded_rectangle([4, 4, 27, 21], radius=2, outline=stroke_hex, width=w)
        d.line([16, 21, 16, 26], fill=stroke_hex, width=w)
        d.line([10, 26, 22, 26], fill=stroke_hex, width=w)

    elif name == "camera":
        # Camera body with lens and top shutter button
        d.rounded_rectangle([4, 8, 27, 26], radius=3, outline=stroke_hex, width=w)
        d.ellipse([11, 12, 20, 21], outline=stroke_hex, width=w)
        d.rectangle([9, 5, 15, 8], fill=stroke_hex)

    elif name == "mic":
        # Pill mic + stand
        d.rounded_rectangle([12, 4, 19, 18], radius=3, outline=stroke_hex, width=w)
        d.arc([8, 11, 23, 22], start=0, end=180, fill=stroke_hex, width=w)
        d.line([16, 22, 16, 27], fill=stroke_hex, width=w)
        d.line([11, 27, 21, 27], fill=stroke_hex, width=w)

    elif name == "speaker":
        # Speaker box + cone
        d.polygon([(6, 11), (11, 11), (19, 5), (19, 27), (11, 21), (6, 21)], outline=stroke_hex, fill=None)
        d.line([6, 11, 11, 11], fill=stroke_hex, width=w)
        d.line([6, 21, 11, 21], fill=stroke_hex, width=w)
        d.arc([16, 8, 26, 24], start=-60, end=60, fill=stroke_hex, width=w)

    elif name == "record":
        # Solid recording dot
        d.ellipse([6, 6, 25, 25], fill="#DC2626")

    elif name == "stop":
        # Solid stop square
        d.rounded_rectangle([7, 7, 24, 24], radius=3, fill="#DC2626")

    elif name == "folder":
        # Folder tab + body
        d.polygon([(4, 8), (12, 8), (15, 11), (27, 11), (27, 25), (4, 25)], outline=stroke_hex)
        d.line([4, 8, 12, 8], fill=stroke_hex, width=w)
        d.line([12, 8, 15, 11], fill=stroke_hex, width=w)
        d.line([15, 11, 27, 11], fill=stroke_hex, width=w)
        d.line([27, 11, 27, 25], fill=stroke_hex, width=w)
        d.line([27, 25, 4, 25], fill=stroke_hex, width=w)
        d.line([4, 25, 4, 8], fill=stroke_hex, width=w)

    elif name == "settings":
        # Gear circle + 4 cross spokes
        d.ellipse([9, 9, 22, 22], outline=stroke_hex, width=w)
        d.ellipse([13, 13, 18, 18], fill=stroke_hex)
        d.line([16, 4, 16, 8], fill=stroke_hex, width=w)
        d.line([16, 23, 16, 27], fill=stroke_hex, width=w)
        d.line([4, 16, 8, 16], fill=stroke_hex, width=w)
        d.line([23, 16, 27, 16], fill=stroke_hex, width=w)

    elif name == "refresh":
        # Circular reload arrow
        d.arc([6, 6, 25, 25], start=45, end=330, fill=stroke_hex, width=w)
        d.polygon([(23, 11), (27, 6), (28, 14)], fill=stroke_hex)

    elif name == "close":
        # Diagonal X
        d.line([8, 8, 23, 23], fill=stroke_hex, width=w)
        d.line([8, 23, 23, 8], fill=stroke_hex, width=w)

    elif name == "search":
        # Magnifying glass
        d.ellipse([6, 6, 19, 19], outline=stroke_hex, width=w)
        d.line([16, 16, 25, 25], fill=stroke_hex, width=w+1)

    elif name == "eye":
        # Eye contour + pupil
        d.arc([4, 6, 27, 26], start=30, end=150, fill=stroke_hex, width=w)
        d.arc([4, 6, 27, 26], start=210, end=330, fill=stroke_hex, width=w)
        d.ellipse([13, 13, 18, 18], fill=stroke_hex)

    elif name == "eye_closed":
        # Crossed eye
        d.arc([4, 6, 27, 26], start=30, end=150, fill=stroke_hex, width=w)
        d.arc([4, 6, 27, 26], start=210, end=330, fill=stroke_hex, width=w)
        d.line([6, 25, 25, 6], fill=stroke_hex, width=w)

    elif name == "lock":
        # Padlock shackle + body
        d.arc([10, 5, 21, 17], start=180, end=0, fill=stroke_hex, width=w)
        d.rounded_rectangle([7, 13, 24, 26], radius=2, outline=stroke_hex, width=w)
        d.ellipse([14, 18, 17, 21], fill=stroke_hex)

    elif name == "wifi":
        # 3 concentric arcs + dot
        d.arc([4, 6, 27, 29], start=225, end=315, fill=stroke_hex, width=w)
        d.arc([8, 11, 23, 26], start=225, end=315, fill=stroke_hex, width=w)
        d.arc([12, 16, 19, 23], start=225, end=315, fill=stroke_hex, width=w)
        d.ellipse([14, 23, 17, 26], fill=stroke_hex)

    elif name == "usb":
        # USB trident
        d.line([16, 6, 16, 26], fill=stroke_hex, width=w)
        d.line([10, 12, 22, 12], fill=stroke_hex, width=w)
        d.line([10, 12, 10, 8], fill=stroke_hex, width=w)
        d.line([22, 12, 22, 8], fill=stroke_hex, width=w)
        d.rectangle([8, 5, 12, 8], fill=stroke_hex)
        d.ellipse([20, 5, 24, 9], fill=stroke_hex)
        d.ellipse([14, 24, 17, 27], fill=stroke_hex)

    elif name == "battery":
        # Battery shell + nipple + charge bars
        d.rounded_rectangle([5, 9, 24, 23], radius=2, outline=stroke_hex, width=w)
        d.rectangle([24, 13, 26, 19], fill=stroke_hex)
        d.rectangle([8, 12, 14, 20], fill="#10B981")

    elif name == "chevron_down":
        d.line([8, 12, 16, 20], fill=stroke_hex, width=w)
        d.line([16, 20, 24, 12], fill=stroke_hex, width=w)

    elif name == "chevron_right":
        d.line([12, 8, 20, 16], fill=stroke_hex, width=w)
        d.line([20, 16, 12, 24], fill=stroke_hex, width=w)

    else:
        # Default dot
        d.ellipse([11, 11, 20, 20], fill=stroke_hex)

    return img

def get_icon(name: str, size: Tuple[int, int] = (16, 16), custom_color: Optional[str] = None) -> ctk.CTkImage:
    """
    Get a crisp, vector-rendered CTkImage icon supporting both light and dark themes.
    Uses 32x32 source images to ensure sharp rendering at 1x, 1.25x, 1.5x, and 2x DPI.
    Instantiates fresh CTkImage instances to prevent cross-root TclError during window recreation.
    """
    cache_key = f"{name}_{custom_color}"
    if cache_key not in _PIL_CACHE:
        # Single colour taken from text_secondary (#374151 in Light, #D1D5DB in Dark)
        light_color = custom_color or "#374151"
        dark_color = custom_color or "#D1D5DB"
        img_light = _draw_icon(name, light_color)
        img_dark = _draw_icon(name, dark_color)
        _PIL_CACHE[cache_key] = (img_light, img_dark)

    img_l, img_d = _PIL_CACHE[cache_key]
    return ctk.CTkImage(light_image=img_l, dark_image=img_d, size=size)
