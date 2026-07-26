"""
Mirenku theme: colors, fonts, and ttk style configuration.

One place to change the app's look. Phase 3 (sv-ttk) replaces the body of
apply_theme() without touching any window code.
"""

import platform
from tkinter import ttk

# Mirenku color palette
MIRENKU_TEAL = "#2dd4bf"
MIRENKU_TEAL_LIGHT = "#e6fffa"
MIRENKU_TEAL_DARK = "#0d9488"


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


def apply_theme(root) -> dict:
    """Apply the Mirenku theme to a Tk root.

    Returns:
        The fonts dict for widgets that need explicit fonts.
    """
    fonts = get_fonts()
    style = ttk.Style()

    # Apply fonts to default widgets
    root.option_add("*Font", fonts["ui"])
    root.option_add("*Menu.Font", fonts["ui"])
    root.option_add("*Menubutton.Font", fonts["ui"])

    # Button styles
    style.configure(
        "TButton",
        font=fonts["ui"],
        borderwidth=1,
        relief="flat",
        background=MIRENKU_TEAL_LIGHT,
    )
    style.map(
        "TButton", background=[("active", MIRENKU_TEAL), ("pressed", MIRENKU_TEAL_DARK)]
    )

    # Frame styles
    style.configure("TFrame", background="white")
    style.configure("TLabelFrame", background="white", font=fonts["ui_bold"])

    # Label styles
    style.configure("TLabel", background="white", font=fonts["ui"])
    style.configure("Heading.TLabel", font=fonts["heading"])

    # Entry and combobox styles
    style.configure("TEntry", font=fonts["ui"])
    style.configure("TCombobox", font=fonts["ui"])

    return fonts
