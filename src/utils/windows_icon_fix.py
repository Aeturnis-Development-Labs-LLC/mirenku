"""Force Windows to use our icon instead of Python's icon"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def force_windows_icon():
    """Force Windows to use our application icon in the taskbar"""

    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        # Get the icon path
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent

        icon_path = base_path / "assets" / "mirenku.ico"

        if not icon_path.exists():
            logger.warning(f"Icon not found: {icon_path}")
            return False

        # Convert path to Windows format
        icon_str = str(icon_path.absolute())

        # Load Windows DLLs
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        # Method 1: Set the process application user model ID
        # This groups our windows separately from other Python apps
        myappid = "AeturnisDev.Mirenku.AnimeTracker.v030"
        shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        # Method 2: Get the console window handle and set its icon
        hwnd = kernel32.GetConsoleWindow()

        # Method 3: Find all windows for this process and set their icons
        def enum_windows_callback(hwnd, lParam):
            """Callback to set icon for each window"""
            try:
                # Get process ID of the window
                process_id = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

                # Check if it's our process
                if process_id.value == os.getpid():
                    # Load the icon
                    icon_handle = user32.LoadImageW(
                        0,
                        icon_str,
                        1,  # IMAGE_ICON
                        0,
                        0,
                        0x00000010,  # LR_LOADFROMFILE
                    )

                    if icon_handle:
                        # Set both small and large icons
                        user32.SendMessageW(hwnd, 0x80, 0, icon_handle)  # WM_SETICON, ICON_SMALL
                        user32.SendMessageW(hwnd, 0x80, 1, icon_handle)  # WM_SETICON, ICON_BIG
                        logger.debug(f"Set icon for window handle: {hwnd}")
            except:
                pass

            return True

        # Enumerate all windows
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        enum_proc = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows(enum_proc, 0)

        # Method 4: Set icon for the main Python executable
        # This affects how Windows groups the taskbar icon
        try:
            # Get handle to the current process
            handle = kernel32.GetModuleHandleW(None)

            # Load our icon
            icon_handle = user32.LoadImageW(
                0,
                icon_str,
                1,  # IMAGE_ICON
                0,
                0,
                0x00000010,  # LR_LOADFROMFILE
            )

            if icon_handle and handle:
                # Try to set it as the default icon
                user32.SetClassLongPtrW(handle, -14, icon_handle)  # GCL_HICON
                user32.SetClassLongPtrW(handle, -34, icon_handle)  # GCL_HICONSM
        except:
            pass

        logger.info(f"Windows icon fix applied with App ID: {myappid}")
        return True

    except Exception as e:
        logger.debug(f"Could not apply Windows icon fix: {e}")
        return False


def set_console_icon():
    """Additional method to set the console window icon"""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        # Get console window
        hwnd = kernel32.GetConsoleWindow()

        if hwnd:
            # Hide console window if it exists (we're a GUI app)
            user32.ShowWindow(hwnd, 0)  # SW_HIDE

    except:
        pass
