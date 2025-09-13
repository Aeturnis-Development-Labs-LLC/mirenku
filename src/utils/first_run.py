"""
First Run Manager for detecting first run, app movement, and storing preferences
"""

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Version constant
APP_VERSION = "0.3.0"


class FirstRunManager:
    """Manages first run detection, app movement, and user preferences"""

    def __init__(self):
        """Initialize First Run Manager"""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "first_run.json"
        self.config = {}

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config
        self.load_config()

    def _get_config_dir(self) -> Path:
        """
        Get platform-specific config directory

        Returns:
            Path to config directory
        """
        system = platform.system()

        if system == "Windows":
            # Windows: %APPDATA%\Mirenku
            app_data = os.environ.get("APPDATA")
            if app_data:
                return Path(app_data) / "Mirenku"
            # Fallback to user home
            return Path.home() / "AppData" / "Roaming" / "Mirenku"

        if system == "Darwin":  # macOS
            # macOS: ~/Library/Application Support/Mirenku
            return Path.home() / "Library" / "Application Support" / "Mirenku"

        # Linux and others
        # Linux: ~/.config/mirenku
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "mirenku"
        return Path.home() / ".config" / "mirenku"

    def load_config(self) -> None:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    self.config = json.load(f)

                # Migrate old config format if needed
                self._migrate_config()

            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load config, treating as first run: {e}")
                self.config = {}
        else:
            self.config = {}

    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            logger.debug(f"Config saved to {self.config_file}")
        except OSError as e:
            logger.error(f"Failed to save config: {e}")

    def _migrate_config(self) -> None:
        """Migrate old config format to new format"""
        # Migrate "completed" to "first_run_completed"
        if "completed" in self.config and "first_run_completed" not in self.config:
            self.config["first_run_completed"] = self.config.pop("completed")
            self.save_config()

    def is_first_run(self) -> bool:
        """
        Check if this is the first run

        Returns:
            True if first run, False otherwise
        """
        return not self.config.get("first_run_completed", False)

    def mark_first_run_complete(self) -> None:
        """Mark first run as complete"""
        self.config["first_run_completed"] = True
        self.config["version"] = APP_VERSION
        self.save_config()

    def reset_first_run(self) -> None:
        """Reset first run state (mainly for testing)"""
        self.config["first_run_completed"] = False
        self.save_config()

    def get_app_version(self) -> str:
        """
        Get current app version

        Returns:
            App version string
        """
        return APP_VERSION

    def is_version_updated(self) -> bool:
        """
        Check if app version has been updated

        Returns:
            True if version is different from saved version
        """
        saved_version = self.config.get("version")
        return saved_version != APP_VERSION

    def has_app_moved(self, current_path: str) -> bool:
        """
        Check if app has moved to a different location

        Args:
            current_path: Current executable path

        Returns:
            True if app has moved
        """
        saved_path = self.get_saved_app_location()

        if saved_path is None:
            # No saved location, consider it as moved
            return True

        # Normalize paths for comparison
        current = Path(current_path).resolve()
        saved = Path(saved_path).resolve()

        return current != saved

    def get_saved_app_location(self) -> Optional[str]:
        """
        Get saved app location

        Returns:
            Saved executable path or None
        """
        return self.config.get("app_location")

    def save_app_location(self, path: str) -> None:
        """
        Save current app location

        Args:
            path: Executable path to save
        """
        self.config["app_location"] = str(Path(path).resolve())
        self.save_config()

    def update_app_location(self, new_path: str) -> None:
        """
        Update app location after move

        Args:
            new_path: New executable path
        """
        self.save_app_location(new_path)
        logger.info(f"App location updated to: {new_path}")

    def set_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference

        Args:
            key: Preference key
            value: Preference value
        """
        if "preferences" not in self.config:
            self.config["preferences"] = {}

        self.config["preferences"][key] = value
        self.save_config()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a user preference

        Args:
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value or default
        """
        preferences = self.config.get("preferences", {})
        return preferences.get(key, default)

    def get_all_preferences(self) -> Dict[str, Any]:
        """
        Get all user preferences

        Returns:
            Dictionary of all preferences
        """
        return self.config.get("preferences", {}).copy()

    def clear_preference(self, key: str) -> None:
        """
        Clear a specific preference

        Args:
            key: Preference key to clear
        """
        preferences = self.config.get("preferences", {})
        if key in preferences:
            del preferences[key]
            self.save_config()

    def get_first_run_settings(self) -> Dict[str, Any]:
        """
        Get settings relevant to first run experience

        Returns:
            Dictionary with first run settings
        """
        return {
            "is_first_run": self.is_first_run(),
            "version": self.get_app_version(),
            "version_updated": self.is_version_updated(),
            "protocol_registered": self.get_preference("protocol_registered", False),
            "welcome_shown": self.get_preference("welcome_shown", False),
            "first_run_skipped": self.get_preference("first_run_skipped", False),
        }

    def should_show_welcome(self) -> bool:
        """
        Determine if welcome dialog should be shown

        Returns:
            True if welcome should be shown
        """
        # Show welcome on first run
        if self.is_first_run():
            return True

        # Show welcome on major version update (if configured)
        if self.is_version_updated() and self.get_preference("show_welcome_on_update", True):
            return True

        return False

    def should_register_protocol(self, current_path: str) -> bool:
        """
        Determine if protocol should be (re)registered

        Args:
            current_path: Current executable path

        Returns:
            True if protocol should be registered
        """
        # Always register on first run (with user consent)
        if self.is_first_run():
            return True

        # Re-register if app has moved
        if self.has_app_moved(current_path):
            return True

        # Register if not previously registered
        if not self.get_preference("protocol_registered", False):
            return True

        return False
