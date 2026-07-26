"""
Mirenku theme: sv-ttk (Sun Valley) with the Mirenku teal accent.

One place to change the app's look. apply_theme() is the single entry
point; window code never touches ttk styles directly.
"""

import logging
import platform
from tkinter import ttk

logger = logging.getLogger(__name__)

# Mirenku color palette
MIRENKU_TEAL = "#2dd4bf"
MIRENKU_TEAL_LIGHT = "#e6fffa"
MIRENKU_TEAL_DARK = "#0d9488"

# Zebra-stripe pairs per theme (odd, even)
_STRIPES = {
    "light": ("#ffffff", MIRENKU_TEAL_LIGHT),
    "dark": ("#1c1c1c", "#123f39"),
}

_current_mode = "light"


def get_fonts() -> dict:
    """Platform-appropriate fonts — clean, straightforward, no gimmicks"""
    system = platform.system()

    if system == "Windows":
        # Windows: Segoe UI for UI, Consolas for data
        return {
            "ui": ("Segoe UI", 9),
            "ui_bold": ("Segoe UI", 9, "bold"),
            "data": ("Consolas", 9),
            "heading": ("Segoe UI", 10, "bold"),
        }
    if system == "Darwin":  # macOS
        return {
            "ui": ("SF Pro Text", 9),
            "ui_bold": ("SF Pro Text", 9, "bold"),
            "data": ("SF Mono", 9),
            "heading": ("SF Pro Display", 10, "bold"),
        }
    # Linux and others
    return {
        "ui": ("Noto Sans", 9),
        "ui_bold": ("Noto Sans", 9, "bold"),
        "data": ("Roboto Mono", 9),
        "heading": ("Noto Sans", 10, "bold"),
    }


def resolve_mode(preference: str) -> str:
    """Resolve a theme preference (System/Light/Dark) to 'light' or 'dark'"""
    preference = (preference or "System").lower()
    if preference in ("light", "dark"):
        return preference

    # System preference
    try:
        import darkdetect

        detected = darkdetect.theme()
        if detected:
            return detected.lower()
    except Exception:
        pass
    return "light"


def current_mode() -> str:
    """The last-applied resolved mode ('light' or 'dark')"""
    return _current_mode


def stripe_colors() -> tuple:
    """(odd_row_bg, even_row_bg) for the current mode"""
    return _STRIPES[_current_mode]


def apply_theme(root, mode: str = "System") -> dict:
    """Apply the Mirenku theme to a Tk root.

    Args:
        root: Tk root
        mode: "System", "Light", or "Dark" (the Settings preference)

    Returns:
        The fonts dict for widgets that need explicit fonts.
    """
    global _current_mode
    _current_mode = resolve_mode(mode)

    try:
        import sv_ttk

        sv_ttk.set_theme(_current_mode)
    except Exception as e:
        # Fall back to stock ttk rather than failing to start
        logger.warning(f"sv-ttk unavailable, using stock theme: {e}")

    fonts = get_fonts()
    style = ttk.Style()

    # Apply fonts to default widgets
    root.option_add("*Font", fonts["ui"])
    root.option_add("*Menu.Font", fonts["ui"])
    root.option_add("*Menubutton.Font", fonts["ui"])

    style.configure("TButton", font=fonts["ui"])
    style.configure("Accent.TButton", font=fonts["ui_bold"])
    style.configure("TLabel", font=fonts["ui"])
    style.configure("Heading.TLabel", font=fonts["heading"])
    style.configure("TEntry", font=fonts["ui"])
    style.configure("TCombobox", font=fonts["ui"])

    # Keep the Mirenku teal as the selection accent in the anime list
    style.map(
        "Treeview",
        background=[("selected", MIRENKU_TEAL)],
        foreground=[("selected", "#0f172a")],
    )

    return fonts
