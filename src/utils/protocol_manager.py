"""
Protocol Manager for registering custom URI schemes
Handles Windows Registry operations for mirenku:// protocol
"""

import datetime
import json
import logging
import platform
from pathlib import Path
from typing import Any, Dict, Optional

# Windows-specific imports
if platform.system() == "Windows":
    import winreg

logger = logging.getLogger(__name__)


class ProtocolManager:
    """Manages custom protocol registration for OAuth callbacks"""

    def __init__(self, development_mode: bool = False):
        """
        Initialize Protocol Manager

        Args:
            development_mode: If True, simulates registration without modifying system
        """
        self.development_mode = development_mode
        self.platform = platform.system()
        self.default_protocol = "mirenku"

        # Backup directory for registry exports
        self.backup_dir = Path.home() / ".mirenku" / "registry_backups"
        if not self.development_mode:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    def register_protocol(self, exe_path: str, protocol: str = None) -> bool:
        """
        Register custom protocol handler

        Args:
            exe_path: Path to the executable to handle the protocol
            protocol: Protocol scheme (default: mirenku)

        Returns:
            True if registration successful, False otherwise
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            logger.info(f"[DEV MODE] Would register {protocol}:// -> {exe_path}")
            return True

        if self.platform == "Windows":
            return self._register_windows(exe_path, protocol)
        logger.warning(f"Protocol registration not implemented for {self.platform}")
        return False

    def check_existing_handler(self, protocol: str = None) -> Optional[Dict[str, Any]]:
        """
        Check if a protocol handler already exists

        Args:
            protocol: Protocol scheme to check

        Returns:
            Dictionary with handler info if exists, None otherwise
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            logger.info(f"[DEV MODE] Checking for existing {protocol}:// handler")
            return None

        if self.platform != "Windows":
            return None

        try:
            # Check if protocol key exists
            protocol_key_path = f"Software\\Classes\\{protocol}"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, protocol_key_path) as key:
                # Get protocol description
                try:
                    desc, _ = winreg.QueryValueEx(key, "")
                except:
                    desc = "Unknown"

                # Get command handler
                command_path = f"{protocol_key_path}\\shell\\open\\command"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, command_path) as cmd_key:
                        command, _ = winreg.QueryValueEx(cmd_key, "")
                except:
                    command = "Unknown"

                return {
                    "protocol": protocol,
                    "description": desc,
                    "command": command,
                    "registry_path": protocol_key_path,
                }
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error checking existing handler: {e}")
            return None

    def backup_registry_key(self, protocol: str = None) -> Optional[str]:
        """
        Backup existing registry key before modification

        Args:
            protocol: Protocol scheme to backup

        Returns:
            Path to backup file if successful, None otherwise
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            logger.info(f"[DEV MODE] Would backup {protocol}:// registry keys")
            return "dev_mode_backup.json"

        if self.platform != "Windows":
            return None

        try:
            # Check if key exists
            existing = self.check_existing_handler(protocol)
            if not existing:
                logger.info(f"No existing {protocol}:// handler to backup")
                return None

            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{protocol}_backup_{timestamp}.json"

            # Export registry values
            backup_data = {
                "timestamp": timestamp,
                "protocol": protocol,
                "registry_data": self._export_registry_branch(
                    winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{protocol}"
                ),
            }

            # Save backup
            with open(backup_file, "w") as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"Registry backup saved to {backup_file}")
            return str(backup_file)

        except Exception as e:
            logger.error(f"Failed to backup registry: {e}")
            return None

    def _export_registry_branch(self, hive, key_path: str) -> Dict:
        """
        Export a registry branch to dictionary

        Args:
            hive: Registry hive
            key_path: Path to registry key

        Returns:
            Dictionary representation of registry branch
        """
        result = {"values": {}, "subkeys": {}}

        try:
            with winreg.OpenKey(hive, key_path) as key:
                # Export values
                i = 0
                while True:
                    try:
                        name, value, reg_type = winreg.EnumValue(key, i)
                        result["values"][name] = {"value": value, "type": reg_type}
                        i += 1
                    except OSError:
                        break

                # Export subkeys
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey_path = f"{key_path}\\{subkey_name}"
                        result["subkeys"][subkey_name] = self._export_registry_branch(
                            hive, subkey_path
                        )
                        i += 1
                    except OSError:
                        break

        except FileNotFoundError:
            pass

        return result

    def restore_registry_backup(self, backup_file: str) -> bool:
        """
        Restore registry from backup file

        Args:
            backup_file: Path to backup file

        Returns:
            True if successful
        """
        if self.development_mode:
            logger.info(f"[DEV MODE] Would restore from {backup_file}")
            return True

        if self.platform != "Windows":
            return False

        try:
            # Load backup
            with open(backup_file) as f:
                backup_data = json.load(f)

            protocol = backup_data["protocol"]

            # First, delete current keys
            self.unregister_protocol(protocol)

            # Restore from backup
            self._import_registry_branch(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{protocol}",
                backup_data["registry_data"],
            )

            logger.info(f"Registry restored from {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore registry: {e}")
            return False

    def _import_registry_branch(self, hive, key_path: str, data: Dict):
        """
        Import registry branch from dictionary

        Args:
            hive: Registry hive
            key_path: Path to registry key
            data: Dictionary with registry data
        """
        # Create key
        with winreg.CreateKey(hive, key_path) as key:
            # Import values
            for name, value_data in data.get("values", {}).items():
                winreg.SetValueEx(key, name, 0, value_data["type"], value_data["value"])

            # Import subkeys
            for subkey_name, subkey_data in data.get("subkeys", {}).items():
                subkey_path = f"{key_path}\\{subkey_name}"
                self._import_registry_branch(hive, subkey_path, subkey_data)

    def _register_windows(self, exe_path: str, protocol: str) -> bool:
        """
        Register protocol on Windows via Registry with safety checks

        Args:
            exe_path: Path to executable
            protocol: Protocol scheme

        Returns:
            True if successful
        """
        try:
            # Check for existing handler
            existing = self.check_existing_handler(protocol)
            if existing:
                logger.warning(f"Protocol {protocol}:// already registered")
                logger.warning(f"Existing handler: {existing['command']}")

                # Create backup before overwriting
                backup_file = self.backup_registry_key(protocol)
                if backup_file:
                    logger.info(f"Created backup before overwriting: {backup_file}")
                else:
                    logger.warning("Failed to create backup, proceeding anyway")
            # Create main protocol key
            protocol_key_path = f"Software\\Classes\\{protocol}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, protocol_key_path) as protocol_key:
                winreg.SetValueEx(protocol_key, "", 0, winreg.REG_SZ, f"URL:{protocol} Protocol")
                winreg.SetValueEx(protocol_key, "URL Protocol", 0, winreg.REG_SZ, "")

            # Create shell command key
            command_key_path = f"Software\\Classes\\{protocol}\\shell\\open\\command"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path) as command_key:
                # Check if exe_path is python.exe, then we need to add the script path
                import os

                if exe_path.lower().endswith("python.exe") or exe_path.lower().endswith(
                    "pythonw.exe"
                ):
                    # Get the main.py script path
                    script_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
                    )
                    command = f'"{exe_path}" "{script_path}" "%1"'
                else:
                    # Assume it's a compiled exe or includes the script
                    command = f'"{exe_path}" "%1"'
                winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)

            logger.info(f"Successfully registered {protocol}:// protocol")

            # Verify registration
            if self.is_registered(protocol):
                logger.info("Registration verified successfully")
                return True
            logger.error("Registration verification failed")
            return False

        except PermissionError as e:
            logger.error(f"Permission denied registering protocol: {e}")
            return False
        except Exception as e:
            logger.error(f"Error registering protocol: {e}")
            return False

    def unregister_protocol(self, protocol: str = None) -> bool:
        """
        Unregister custom protocol handler

        Args:
            protocol: Protocol scheme to unregister (default: mirenku)

        Returns:
            True if unregistration successful
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            logger.info(f"[DEV MODE] Would unregister {protocol}://")
            return True

        if self.platform == "Windows":
            return self._unregister_windows(protocol)
        logger.warning(f"Protocol unregistration not implemented for {self.platform}")
        return False

    def _unregister_windows(self, protocol: str) -> bool:
        """
        Unregister protocol on Windows

        Args:
            protocol: Protocol scheme

        Returns:
            True if successful
        """
        try:
            # Delete the entire protocol key tree
            self._delete_registry_tree(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{protocol}")
            logger.info(f"Successfully unregistered {protocol}:// protocol")
            return True

        except FileNotFoundError:
            logger.info(f"Protocol {protocol}:// was not registered")
            return True
        except Exception as e:
            logger.error(f"Error unregistering protocol: {e}")
            return False

    def _delete_registry_tree(self, key, subkey_path):
        """
        Recursively delete a registry key and all subkeys

        Args:
            key: Registry hive (e.g., HKEY_CURRENT_USER)
            subkey_path: Path to the key to delete
        """
        if platform.system() != "Windows":
            return

        try:
            with winreg.OpenKey(key, subkey_path, 0, winreg.KEY_ALL_ACCESS) as open_key:
                # Get number of subkeys
                info = winreg.QueryInfoKey(open_key)
                num_subkeys = info[0]

                # Delete all subkeys first (in reverse to avoid index issues)
                for i in range(num_subkeys - 1, -1, -1):
                    subkey_name = winreg.EnumKey(open_key, i)
                    self._delete_registry_tree(key, f"{subkey_path}\\{subkey_name}")

            # Now delete the key itself
            winreg.DeleteKey(key, subkey_path)
        except FileNotFoundError:
            pass  # Key doesn't exist, that's fine
        except AttributeError:
            # winreg not available (mocked in tests)
            pass

    def list_backups(self, protocol: str = None) -> list:
        """
        List available registry backups

        Args:
            protocol: Protocol to filter backups (optional)

        Returns:
            List of backup file paths
        """
        if self.development_mode:
            return []

        if not self.backup_dir.exists():
            return []

        pattern = f"{protocol}_backup_*.json" if protocol else "*_backup_*.json"
        backups = list(self.backup_dir.glob(pattern))

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return [str(b) for b in backups]

    def safe_register_protocol(
        self, exe_path: str, protocol: str = None, force: bool = False
    ) -> Dict[str, Any]:
        """
        Safely register protocol with conflict detection and user confirmation

        Args:
            exe_path: Path to executable
            protocol: Protocol scheme
            force: Force registration even if handler exists

        Returns:
            Dictionary with registration result and details
        """
        protocol = protocol or self.default_protocol
        result = {
            "success": False,
            "protocol": protocol,
            "message": "",
            "backup_file": None,
            "existing_handler": None,
            "action_taken": None,
        }

        if self.development_mode:
            result["success"] = True
            result["message"] = f"[DEV MODE] Would register {protocol}://"
            result["action_taken"] = "simulated"
            return result

        # Check for existing handler
        existing = self.check_existing_handler(protocol)
        if existing:
            result["existing_handler"] = existing

            if not force:
                result["message"] = (
                    f"Protocol {protocol}:// is already registered to: "
                    f"{existing['command']}. Use force=True to override."
                )
                result["action_taken"] = "aborted_conflict"
                return result

            # Create backup before overwriting
            backup_file = self.backup_registry_key(protocol)
            if backup_file:
                result["backup_file"] = backup_file
                logger.info(f"Created backup: {backup_file}")
            else:
                logger.warning("Failed to create backup but proceeding")

        # Perform registration
        success = self.register_protocol(exe_path, protocol)
        result["success"] = success

        if success:
            result["message"] = f"Successfully registered {protocol}://"
            result["action_taken"] = "registered_new" if not existing else "overwritten_existing"
        else:
            result["message"] = f"Failed to register {protocol}://"
            result["action_taken"] = "failed"

            # Try to restore backup if we created one
            if result["backup_file"]:
                logger.info("Attempting to restore from backup after failure")
                if self.restore_registry_backup(result["backup_file"]):
                    result["message"] += " (restored from backup)"

        return result

    def is_registered(self, protocol: str = None) -> bool:
        """
        Check if protocol is registered

        Args:
            protocol: Protocol scheme to check (default: mirenku)

        Returns:
            True if protocol is registered
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            logger.info(f"[DEV MODE] Checking registration for {protocol}://")
            return True

        if self.platform == "Windows":
            return self._is_registered_windows(protocol)
        return False

    def _is_registered_windows(self, protocol: str) -> bool:
        """
        Check if protocol is registered on Windows

        Args:
            protocol: Protocol scheme

        Returns:
            True if registered
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{protocol}"):
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking protocol registration: {e}")
            return False

    def get_registered_path(self, protocol: str = None) -> Optional[str]:
        """
        Get the registered executable path for a protocol

        Args:
            protocol: Protocol scheme (default: mirenku)

        Returns:
            Path to registered executable, or None if not registered
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            logger.info(f"[DEV MODE] Getting registered path for {protocol}://")
            return None

        if self.platform == "Windows":
            return self._get_registered_path_windows(protocol)
        return None

    def _get_registered_path_windows(self, protocol: str) -> Optional[str]:
        """
        Get registered executable path on Windows

        Args:
            protocol: Protocol scheme

        Returns:
            Path to executable or None
        """
        try:
            command_key_path = f"Software\\Classes\\{protocol}\\shell\\open\\command"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, command_key_path) as key:
                command, _ = winreg.QueryValueEx(key, "")
                # Extract path from command string (format: "path" "%1")
                if command.startswith('"'):
                    end_quote = command.index('"', 1)
                    return command[1:end_quote]
                # No quotes, take everything before first space
                parts = command.split(" ")
                return parts[0] if parts else None
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting registered path: {e}")
            return None

    def needs_reregistration(self, current_exe_path: str, protocol: str = None) -> bool:
        """
        Check if protocol needs reregistration (app moved)

        Args:
            current_exe_path: Current executable path
            protocol: Protocol scheme (default: mirenku)

        Returns:
            True if reregistration needed
        """
        protocol = protocol or self.default_protocol

        if self.development_mode:
            return False

        if not self.is_registered(protocol):
            return True

        registered_path = self.get_registered_path(protocol)
        if not registered_path:
            return True

        # Normalize paths for comparison
        current_path = Path(current_exe_path).resolve()
        reg_path = Path(registered_path).resolve()

        return current_path != reg_path

    def auto_reregister(self, current_exe_path: str, protocol: str = None) -> bool:
        """
        Automatically reregister protocol if app has moved

        Args:
            current_exe_path: Current executable path
            protocol: Protocol scheme (default: mirenku)

        Returns:
            True if reregistration successful or not needed
        """
        protocol = protocol or self.default_protocol

        if not self.needs_reregistration(current_exe_path, protocol):
            logger.info(f"Protocol {protocol}:// registration is up to date")
            return True

        logger.info(f"App has moved, reregistering {protocol}:// protocol")

        # Unregister old path
        self.unregister_protocol(protocol)

        # Register new path
        return self.register_protocol(current_exe_path, protocol)
