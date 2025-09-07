"""Tests for configuration management"""

import unittest
import tempfile
from pathlib import Path
import sys
import json
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.config import Config


class TestConfig(unittest.TestCase):
    """Test configuration functionality"""
    
    def setUp(self):
        """Set up test configuration"""
        # Create temporary directory for config
        self.temp_dir = tempfile.mkdtemp()
        self.original_localappdata = os.environ.get('LOCALAPPDATA')
        os.environ['LOCALAPPDATA'] = self.temp_dir
        
        # Create config instance
        self.config = Config()
    
    def tearDown(self):
        """Clean up test configuration"""
        # Restore environment
        if self.original_localappdata:
            os.environ['LOCALAPPDATA'] = self.original_localappdata
        else:
            del os.environ['LOCALAPPDATA']
        
        # Clean up temp directory
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_config_initialization(self):
        """Test config initialization"""
        self.assertIsNotNone(self.config)
        self.assertEqual(self.config.app_name, "AnimeTracker")
        self.assertIsNotNone(self.config.settings)
    
    def test_data_directory_creation(self):
        """Test data directory creation"""
        data_dir = self.config.get_data_directory()
        self.assertTrue(data_dir.exists())
        self.assertTrue(data_dir.is_dir())
    
    def test_default_settings(self):
        """Test default settings"""
        defaults = self.config.get_default_settings()
        
        self.assertIn("theme", defaults)
        self.assertIn("auto_save", defaults)
        self.assertIn("window_geometry", defaults)
        self.assertIn("last_filter", defaults)
        self.assertIn("sort_column", defaults)
        
        self.assertEqual(defaults["theme"], "light")
        self.assertTrue(defaults["auto_save"])
        self.assertEqual(defaults["last_filter"], "All")
    
    def test_get_setting(self):
        """Test getting settings"""
        # Test existing setting
        theme = self.config.get("theme")
        self.assertEqual(theme, "light")
        
        # Test non-existent setting with default
        missing = self.config.get("missing_key", "default_value")
        self.assertEqual(missing, "default_value")
        
        # Test non-existent setting without default
        missing = self.config.get("missing_key")
        self.assertIsNone(missing)
    
    def test_set_setting(self):
        """Test setting values"""
        # Set a new value
        self.config.set("test_key", "test_value")
        
        # Verify it was set
        value = self.config.get("test_key")
        self.assertEqual(value, "test_value")
        
        # Update existing value
        self.config.set("theme", "dark")
        theme = self.config.get("theme")
        self.assertEqual(theme, "dark")
    
    def test_save_and_load_settings(self):
        """Test saving and loading settings"""
        # Modify settings
        self.config.set("custom_setting", "custom_value")
        self.config.set("window_geometry", "1200x800")
        
        # Save settings
        self.config.save_settings()
        
        # Verify file exists
        self.assertTrue(self.config.config_file.exists())
        
        # Load settings from file
        with open(self.config.config_file, 'r') as f:
            loaded = json.load(f)
        
        self.assertEqual(loaded["custom_setting"], "custom_value")
        self.assertEqual(loaded["window_geometry"], "1200x800")
    
    def test_database_path(self):
        """Test database path generation"""
        db_path = self.config.get_db_path()
        
        self.assertIsNotNone(db_path)
        self.assertTrue(str(db_path).endswith("anime_tracker.db"))
        self.assertEqual(db_path.parent, self.config.data_dir)
    
    def test_backup_directory(self):
        """Test backup directory creation"""
        backup_dir = self.config.get_backup_dir()
        
        self.assertTrue(backup_dir.exists())
        self.assertTrue(backup_dir.is_dir())
        self.assertEqual(backup_dir.parent, self.config.data_dir)
        self.assertEqual(backup_dir.name, "backups")
    
    def test_auto_save_setting(self):
        """Test auto-save functionality"""
        # Disable auto-save
        self.config.settings["auto_save"] = False
        
        # Set a value (should not auto-save)
        self.config.set("test_auto", "value1")
        
        # Check file wasn't updated
        if self.config.config_file.exists():
            with open(self.config.config_file, 'r') as f:
                loaded = json.load(f)
            self.assertNotIn("test_auto", loaded)
        
        # Enable auto-save
        self.config.settings["auto_save"] = True
        
        # Set another value (should auto-save)
        self.config.set("test_auto2", "value2")
        
        # Check file was updated
        with open(self.config.config_file, 'r') as f:
            loaded = json.load(f)
        self.assertEqual(loaded.get("test_auto2"), "value2")


if __name__ == '__main__':
    unittest.main()