"""Helper module for setting application icon on Windows"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def set_app_icon(root):
    """Set application icon for both window and taskbar

    Args:
        root: Tkinter root window
    """
    try:
        # Find icon file
        if getattr(sys, "frozen", False):
            # Running as compiled executable - icon is in _MEIPASS/assets
            import sys

            base_path = Path(sys._MEIPASS)
            icon_path = base_path / "assets" / "mirenku.ico"
        else:
            # Running as script
            base_path = Path(__file__).parent.parent.parent
            icon_path = base_path / "assets" / "mirenku.ico"

        if not icon_path.exists():
            # Try current working directory
            icon_path = Path.cwd() / "assets" / "mirenku.ico"

        if icon_path.exists():
            icon_str = str(icon_path)

            # Set window icon
            root.iconbitmap(default=icon_str)

            # Force Windows to use this icon in taskbar
            if sys.platform == "win32":
                try:
                    import ctypes

                    # Set app user model ID to group windows properly
                    myappid = "aeturnis.mirenku.anime.tracker.v030"
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                except Exception as e:
                    logger.debug(f"Could not set app ID: {e}")

            logger.info(f"Icon set successfully from: {icon_path}")
            return True
        logger.warning(f"Icon file not found at: {icon_path}")
        return False

    except Exception as e:
        logger.error(f"Failed to set application icon: {e}")
        return False


def set_taskbar_icon():
    """Additional method to ensure taskbar icon is set on Windows"""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        # Get the window handle
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        # Get console window
        hWnd = kernel32.GetConsoleWindow()

        if hWnd:
            # Find icon file
            if getattr(sys, "frozen", False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = Path(__file__).parent.parent.parent

            icon_path = base_path / "assets" / "mirenku.ico"

            if icon_path.exists():
                # Load icon
                hIcon = user32.LoadImageW(
                    0,
                    str(icon_path),
                    1,  # IMAGE_ICON
                    0,
                    0,
                    0x00000010,  # LR_LOADFROMFILE
                )

                if hIcon:
                    # Set icon
                    user32.SendMessageW(hWnd, 0x80, 0, hIcon)  # WM_SETICON, ICON_SMALL
                    user32.SendMessageW(hWnd, 0x80, 1, hIcon)  # WM_SETICON, ICON_BIG
                    logger.info("Taskbar icon set successfully")

    except Exception as e:
        logger.debug(f"Could not set taskbar icon: {e}")
