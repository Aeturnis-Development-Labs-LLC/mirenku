"""
One-time cleanup of artifacts left behind by removed features.

v0.3.3 removed the mirenku:// custom protocol handler; existing installs
may still have the HKCU registration pointing at the executable.
"""

import logging
import platform

logger = logging.getLogger(__name__)

_PROTOCOL = "mirenku"


def cleanup_legacy_protocol_registration() -> None:
    """Remove the legacy mirenku:// protocol registration if present.

    Idempotent and safe to call on every startup. Registration was only
    ever written on Windows (HKCU\\Software\\Classes\\mirenku).
    """
    if platform.system() != "Windows":
        return

    import winreg

    root = f"Software\\Classes\\{_PROTOCOL}"
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, root).Close()
    except FileNotFoundError:
        return
    except OSError as e:
        logger.warning(f"Could not check legacy protocol registration: {e}")
        return

    try:
        _delete_registry_tree(winreg.HKEY_CURRENT_USER, root)
        logger.info("Removed legacy mirenku:// protocol registration")
    except OSError as e:
        logger.warning(f"Could not remove legacy protocol registration: {e}")


def _delete_registry_tree(hive: int, key_path: str) -> None:
    """Recursively delete a registry key and all its subkeys."""
    import winreg

    with winreg.OpenKey(hive, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
        while True:
            try:
                subkey = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_registry_tree(hive, f"{key_path}\\{subkey}")
    winreg.DeleteKey(hive, key_path)
