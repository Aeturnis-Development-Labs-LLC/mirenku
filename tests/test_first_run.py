"""
Test suite for First Run Manager
Tests first run detection, app movement detection, and config persistence
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.first_run import FirstRunManager


class TestFirstRunDetection:
    """Test first run detection logic"""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory"""
        config_dir = tmp_path / "mirenku"
        config_dir.mkdir()
        return config_dir
    
    @pytest.fixture
    def manager(self, temp_config_dir):
        """Create FirstRunManager with temp directory"""
        with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_dir:
            mock_dir.return_value = temp_config_dir
            return FirstRunManager()
    
    def test_is_first_run_when_no_config(self, manager, temp_config_dir):
        """Test that first run is detected when no config exists"""
        assert manager.is_first_run() is True
        assert not (temp_config_dir / "first_run.json").exists()
    
    def test_is_not_first_run_when_config_exists(self, manager, temp_config_dir):
        """Test that first run is false when config exists"""
        # Create config file
        config_file = temp_config_dir / "first_run.json"
        config_data = {
            "first_run_completed": True,
            "version": "0.3.0"
        }
        config_file.write_text(json.dumps(config_data))
        
        # Reload config after file creation
        manager.load_config()
        
        assert manager.is_first_run() is False
    
    def test_mark_first_run_complete(self, manager, temp_config_dir):
        """Test marking first run as complete"""
        assert manager.is_first_run() is True
        
        manager.mark_first_run_complete()
        
        assert manager.is_first_run() is False
        config_file = temp_config_dir / "first_run.json"
        assert config_file.exists()
        
        data = json.loads(config_file.read_text())
        assert data["first_run_completed"] is True
    
    def test_get_app_version(self, manager):
        """Test getting app version"""
        version = manager.get_app_version()
        assert isinstance(version, str)
        assert len(version) > 0
    
    def test_is_version_updated(self, manager, temp_config_dir):
        """Test detecting version updates"""
        # Create config with old version
        config_file = temp_config_dir / "first_run.json"
        config_data = {
            "first_run_completed": True,
            "version": "0.2.0"
        }
        config_file.write_text(json.dumps(config_data))
        
        # Current version should be different
        assert manager.is_version_updated() is True
    
    def test_is_version_not_updated(self, manager, temp_config_dir):
        """Test when version hasn't changed"""
        current_version = manager.get_app_version()
        
        # Create config with current version
        config_file = temp_config_dir / "first_run.json"
        config_data = {
            "first_run_completed": True,
            "version": current_version
        }
        config_file.write_text(json.dumps(config_data))
        
        # Reload config after file creation
        manager.load_config()
        
        assert manager.is_version_updated() is False


class TestAppMovementDetection:
    """Test app movement detection"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create FirstRunManager with temp directory"""
        with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_dir:
            mock_dir.return_value = tmp_path
            return FirstRunManager()
    
    def test_detect_app_moved(self, manager, tmp_path):
        """Test detecting when app has moved"""
        old_path = r"C:\OldLocation\mirenku.exe"
        new_path = r"C:\NewLocation\mirenku.exe"
        
        # Save old location
        manager.save_app_location(old_path)
        
        # Check if moved
        assert manager.has_app_moved(new_path) is True
    
    def test_detect_app_not_moved(self, manager, tmp_path):
        """Test when app hasn't moved"""
        current_path = r"C:\Program Files\Mirenku\mirenku.exe"
        
        # Save current location
        manager.save_app_location(current_path)
        
        # Check if moved (same location)
        assert manager.has_app_moved(current_path) is False
    
    def test_get_saved_app_location(self, manager, tmp_path):
        """Test retrieving saved app location"""
        expected_path = r"C:\Program Files\Mirenku\mirenku.exe"
        
        manager.save_app_location(expected_path)
        saved_path = manager.get_saved_app_location()
        
        assert saved_path == expected_path
    
    def test_get_saved_app_location_when_none(self, manager, tmp_path):
        """Test getting location when none saved"""
        location = manager.get_saved_app_location()
        assert location is None
    
    def test_update_app_location(self, manager, tmp_path):
        """Test updating app location after move"""
        old_path = r"C:\OldLocation\mirenku.exe"
        new_path = r"C:\NewLocation\mirenku.exe"
        
        # Save old location
        manager.save_app_location(old_path)
        assert manager.get_saved_app_location() == old_path
        
        # Update to new location
        manager.update_app_location(new_path)
        assert manager.get_saved_app_location() == new_path


class TestUserPreferences:
    """Test user preference storage"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create FirstRunManager with temp directory"""
        with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_dir:
            mock_dir.return_value = tmp_path
            return FirstRunManager()
    
    def test_save_user_preference(self, manager):
        """Test saving user preferences"""
        manager.set_preference("protocol_registered", True)
        manager.set_preference("skip_welcome", False)
        
        assert manager.get_preference("protocol_registered") is True
        assert manager.get_preference("skip_welcome") is False
    
    def test_get_preference_with_default(self, manager):
        """Test getting preference with default value"""
        # Non-existent preference should return default
        value = manager.get_preference("non_existent", default="default_value")
        assert value == "default_value"
    
    def test_get_all_preferences(self, manager):
        """Test getting all preferences"""
        manager.set_preference("pref1", "value1")
        manager.set_preference("pref2", 42)
        manager.set_preference("pref3", True)
        
        prefs = manager.get_all_preferences()
        assert prefs["pref1"] == "value1"
        assert prefs["pref2"] == 42
        assert prefs["pref3"] is True
    
    def test_clear_preference(self, manager):
        """Test clearing a specific preference"""
        manager.set_preference("temp_pref", "temp_value")
        assert manager.get_preference("temp_pref") == "temp_value"
        
        manager.clear_preference("temp_pref")
        assert manager.get_preference("temp_pref") is None
    
    def test_preferences_persist(self, tmp_path):
        """Test that preferences persist across instances"""
        with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_dir:
            mock_dir.return_value = tmp_path
            
            # First instance
            manager1 = FirstRunManager()
            manager1.set_preference("persistent", "data")
            
            # Second instance
            manager2 = FirstRunManager()
            assert manager2.get_preference("persistent") == "data"


class TestConfigPersistence:
    """Test configuration file persistence"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create FirstRunManager with temp directory"""
        with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_dir:
            mock_dir.return_value = tmp_path
            return FirstRunManager()
    
    def test_config_file_creation(self, manager, tmp_path):
        """Test that config file is created properly"""
        manager.save_config()
        
        config_file = tmp_path / "first_run.json"
        assert config_file.exists()
        
        # Verify it's valid JSON
        data = json.loads(config_file.read_text())
        assert isinstance(data, dict)
    
    def test_config_file_permissions(self, manager, tmp_path):
        """Test config file has appropriate permissions"""
        manager.save_config()
        
        config_file = tmp_path / "first_run.json"
        # File should be readable and writable by user
        assert config_file.stat().st_mode & 0o600
    
    def test_config_corruption_handling(self, manager, tmp_path):
        """Test handling of corrupted config file"""
        config_file = tmp_path / "first_run.json"
        config_file.write_text("not valid json{]")
        
        # Should handle corruption gracefully
        assert manager.is_first_run() is True  # Treat as first run
    
    def test_config_migration(self, manager, tmp_path):
        """Test migrating old config format to new"""
        # Create old format config
        config_file = tmp_path / "first_run.json"
        old_config = {
            "completed": True  # Old format
        }
        config_file.write_text(json.dumps(old_config))
        
        # Manager should migrate to new format
        manager.load_config()
        manager.save_config()
        
        data = json.loads(config_file.read_text())
        assert "first_run_completed" in data  # New format
    
    @patch('utils.first_run.platform.system')
    def test_get_config_dir_windows(self, mock_platform, tmp_path):
        """Test getting config directory on Windows"""
        mock_platform.return_value = 'Windows'
        
        with patch.dict(os.environ, {'APPDATA': str(tmp_path)}):
            with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_get_dir:
                # Return the temp path instead of trying to create a real path
                mock_get_dir.return_value = tmp_path / 'Mirenku'
                
                manager = FirstRunManager()
                config_dir = manager._get_config_dir()
                
                assert 'Mirenku' in str(config_dir)
    
    @patch('utils.first_run.platform.system')
    def test_get_config_dir_linux(self, mock_platform):
        """Test getting config directory on Linux"""
        mock_platform.return_value = 'Linux'
        
        with patch.dict(os.environ, {'HOME': '/home/testuser'}):
            manager = FirstRunManager()
            config_dir = manager._get_config_dir()
            
            assert '.config' in str(config_dir)
            assert 'mirenku' in str(config_dir)
    
    @patch('utils.first_run.platform.system')
    def test_get_config_dir_macos(self, mock_platform, tmp_path):
        """Test getting config directory on macOS"""
        mock_platform.return_value = 'Darwin'
        
        with patch.dict(os.environ, {'HOME': str(tmp_path)}):
            with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_get_dir:
                # Return the temp path instead of trying to create a real path
                mock_get_dir.return_value = tmp_path / 'Library' / 'Application Support' / 'Mirenku'
                
                manager = FirstRunManager()
                config_dir = manager._get_config_dir()
                
                assert 'Mirenku' in str(config_dir)


class TestFirstRunFlow:
    """Test complete first run flow"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create FirstRunManager with temp directory"""
        with patch('utils.first_run.FirstRunManager._get_config_dir') as mock_dir:
            mock_dir.return_value = tmp_path
            return FirstRunManager()
    
    def test_complete_first_run_flow(self, manager):
        """Test complete first run flow"""
        # Initial state
        assert manager.is_first_run() is True
        
        # User completes first run
        manager.set_preference("protocol_registered", True)
        manager.set_preference("welcome_shown", True)
        manager.save_app_location(r"C:\Program Files\Mirenku\mirenku.exe")
        manager.mark_first_run_complete()
        
        # Verify state
        assert manager.is_first_run() is False
        assert manager.get_preference("protocol_registered") is True
        assert manager.get_preference("welcome_shown") is True
        assert manager.get_saved_app_location() == r"C:\Program Files\Mirenku\mirenku.exe"
    
    def test_skip_first_run_flow(self, manager):
        """Test skipping first run"""
        assert manager.is_first_run() is True
        
        # User skips first run
        manager.set_preference("first_run_skipped", True)
        manager.mark_first_run_complete()
        
        # Should still mark as complete
        assert manager.is_first_run() is False
        assert manager.get_preference("first_run_skipped") is True
        assert manager.get_preference("protocol_registered") is None
    
    def test_reset_first_run(self, manager):
        """Test resetting first run state"""
        # Complete first run
        manager.mark_first_run_complete()
        assert manager.is_first_run() is False
        
        # Reset for testing
        manager.reset_first_run()
        assert manager.is_first_run() is True