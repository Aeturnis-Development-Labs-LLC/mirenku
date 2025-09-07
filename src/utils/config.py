"""Configuration management for Anime Tracker"""

import os
import sys
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class Config:
    """Manages application configuration and paths"""
    
    def __init__(self):
        self.app_name = "AnimeTracker"
        self.version = "0.1.0-dev"
        
        # Determine if running as frozen executable or script
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.app_dir = Path(sys.executable).parent
        else:
            # Running as script
            self.app_dir = Path(__file__).parent.parent.parent
        
        # Set up application data directory
        self.data_dir = self.get_data_directory()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database path
        self.db_path = self.data_dir / "anime_tracker.db"
        
        # Config file path
        self.config_file = self.data_dir / "config.json"
        
        # Load or create configuration
        self.settings = self.load_settings()
    
    def get_data_directory(self) -> Path:
        """Get the appropriate data directory for the platform"""
        if os.name == 'nt':  # Windows
            # Use AppData/Local
            app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
            return Path(app_data) / self.app_name
        else:  # Linux/Mac
            # Use ~/.config
            config_dir = Path.home() / '.config'
            return config_dir / self.app_name.lower()
    
    def load_settings(self) -> dict:
        """Load settings from config file or create defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self.get_default_settings()
        else:
            settings = self.get_default_settings()
            self.save_settings(settings)
            return settings
    
    def get_default_settings(self) -> dict:
        """Return default application settings"""
        return {
            "theme": "light",
            "auto_save": True,
            "window_geometry": "900x600",
            "last_filter": "All",
            "sort_column": "title",
            "sort_order": "ascending",
            "mal_username": "",
            "sync_on_startup": False,
            "backup_enabled": True,
            "backup_count": 5
        }
    
    def save_settings(self, settings: dict = None):
        """Save settings to config file"""
        if settings:
            self.settings = settings
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info("Settings saved successfully")
        except IOError as e:
            logger.error(f"Error saving settings: {e}")
    
    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        """Set a setting value"""
        self.settings[key] = value
        if self.get("auto_save", True):
            self.save_settings()
    
    def get_db_path(self) -> Path:
        """Get the database file path"""
        return self.db_path
    
    def get_backup_dir(self) -> Path:
        """Get the backup directory path"""
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        return backup_dir


import sys  # Add this import at the top of the file