"""
Test suite for Scrobbling Settings UI - v0.4.0
Following TDD approach - Red phase (failing tests first)
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, MagicMock, patch

# These imports will fail initially (TDD Red phase)
from src.ui.settings_dialog import SettingsDialog
from src.services.scrobbling_manager import ScrobblingManager


class TestScrobblingSettingsTab:
    """Test scrobbling settings tab in settings dialog."""

    @pytest.fixture
    def root(self):
        """Create a Tk root window for testing."""
        root = tk.Tk()
        root.withdraw()  # Hide window during tests
        yield root
        root.destroy()

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        # Mock config.get to return sensible defaults for different keys
        def config_get(key, default=None):
            config_values = {
                "check_updates": True,
                "minimize_to_tray": False,
                "start_minimized": False,
                "theme": "light",
                "mal_client_id": "",
                "mal_code_verifier": "",
                "scrobbling": {"enabled": False, "port": 7834}
            }
            return config_values.get(key, default)

        config.get = Mock(side_effect=config_get)
        config.set = Mock()
        config.save = Mock()
        return config

    @pytest.fixture
    def mock_scrobbling_manager(self):
        """Create a mock scrobbling manager."""
        manager = Mock(spec=ScrobblingManager)
        manager.enabled = False
        manager.port = 7834
        manager.is_running = Mock(return_value=False)
        manager.enable = Mock(return_value=True)
        manager.disable = Mock(return_value=True)
        manager.set_port = Mock(return_value=True)
        manager.get_status = Mock(return_value={
            "enabled": False,
            "running": False,
            "port": 7834,
            "clients": 0,
            "sessions": 0
        })
        return manager

    @pytest.fixture
    def settings_dialog(self, root, mock_config, mock_scrobbling_manager):
        """Create a settings dialog with scrobbling manager."""
        dialog = SettingsDialog(
            root,
            config=mock_config,
            scrobbling_manager=mock_scrobbling_manager
        )
        return dialog

    def test_scrobbling_tab_exists(self, settings_dialog):
        """Test that scrobbling tab is added to settings dialog."""
        # Check that the tab exists
        tab_names = [settings_dialog.notebook.tab(i, "text") for i in range(settings_dialog.notebook.index("end"))]
        assert "Scrobbling" in tab_names

    def test_scrobbling_enable_checkbox(self, settings_dialog):
        """Test that enable scrobbling checkbox exists and works."""
        # Find the scrobbling tab
        scrobbling_frame = settings_dialog.scrobbling_frame

        # Check that enable checkbox exists
        assert hasattr(settings_dialog, 'scrobbling_enabled_var')
        assert settings_dialog.scrobbling_enabled_var.get() is False

        # Simulate enabling scrobbling
        settings_dialog.scrobbling_enabled_var.set(True)
        settings_dialog._on_scrobbling_toggle()

        # Verify manager was called
        settings_dialog.scrobbling_manager.enable.assert_called_once()

    def test_scrobbling_disable_checkbox(self, settings_dialog):
        """Test disabling scrobbling via checkbox."""
        # Setup - start with enabled
        settings_dialog.scrobbling_manager.enabled = True
        settings_dialog.scrobbling_enabled_var.set(True)

        # Simulate disabling scrobbling
        settings_dialog.scrobbling_enabled_var.set(False)
        settings_dialog._on_scrobbling_toggle()

        # Verify manager was called
        settings_dialog.scrobbling_manager.disable.assert_called_once()

    def test_port_configuration(self, settings_dialog):
        """Test port configuration input."""
        # Check that port entry exists
        assert hasattr(settings_dialog, 'scrobbling_port_var')
        assert settings_dialog.scrobbling_port_var.get() == "7834"

        # Change port
        settings_dialog.scrobbling_port_var.set("8080")
        settings_dialog._on_port_change()

        # Verify manager was called
        settings_dialog.scrobbling_manager.set_port.assert_called_with(8080)

    def test_port_validation(self, settings_dialog):
        """Test that invalid ports are rejected."""
        # Try invalid port (too low)
        settings_dialog.scrobbling_port_var.set("1023")
        result = settings_dialog._validate_port("1023")
        assert result is False

        # Try invalid port (too high)
        settings_dialog.scrobbling_port_var.set("65536")
        result = settings_dialog._validate_port("65536")
        assert result is False

        # Try non-numeric port
        settings_dialog.scrobbling_port_var.set("abc")
        result = settings_dialog._validate_port("abc")
        assert result is False

        # Try valid port
        settings_dialog.scrobbling_port_var.set("8080")
        result = settings_dialog._validate_port("8080")
        assert result is True

    def test_status_display(self, settings_dialog):
        """Test that status is displayed correctly."""
        # Check that status label exists
        assert hasattr(settings_dialog, 'scrobbling_status_label')

        # Update status when running
        settings_dialog.scrobbling_manager.get_status.return_value = {
            "enabled": True,
            "running": True,
            "port": 7834,
            "clients": 2,
            "sessions": 1
        }
        settings_dialog._update_scrobbling_status()

        # Check status text
        status_text = settings_dialog.scrobbling_status_label.cget("text")
        assert "Running" in status_text
        assert "2 clients" in status_text
        assert "1 session" in status_text

    def test_status_display_when_stopped(self, settings_dialog):
        """Test status display when server is stopped."""
        # Update status when stopped
        settings_dialog.scrobbling_manager.get_status.return_value = {
            "enabled": False,
            "running": False,
            "port": 7834,
            "clients": 0,
            "sessions": 0
        }
        settings_dialog._update_scrobbling_status()

        # Check status text
        status_text = settings_dialog.scrobbling_status_label.cget("text")
        assert "Stopped" in status_text or "Disabled" in status_text

    def test_settings_save(self, settings_dialog, mock_config):
        """Test that settings are saved when dialog is closed."""
        # Change settings
        settings_dialog.scrobbling_enabled_var.set(True)
        settings_dialog.scrobbling_port_var.set("8080")

        # Save settings
        settings_dialog._save_settings()

        # Verify config was updated
        mock_config.set.assert_called()
        mock_config.save.assert_called()

    def test_ui_disabled_when_server_running(self, settings_dialog):
        """Test that port field is disabled when server is running."""
        # Simulate server running
        settings_dialog.scrobbling_manager.is_running.return_value = True
        settings_dialog.scrobbling_manager.enabled = True
        settings_dialog.scrobbling_enabled_var.set(True)

        # Update UI state
        settings_dialog._update_scrobbling_ui_state()

        # Check that port entry is disabled
        assert str(settings_dialog.scrobbling_port_entry.cget("state")) == "disabled"

    def test_ui_enabled_when_server_stopped(self, settings_dialog):
        """Test that port field is enabled when server is stopped."""
        # Simulate server stopped
        settings_dialog.scrobbling_manager.is_running.return_value = False
        settings_dialog.scrobbling_manager.enabled = False
        settings_dialog.scrobbling_enabled_var.set(False)

        # Update UI state
        settings_dialog._update_scrobbling_ui_state()

        # Check that port entry is enabled
        assert str(settings_dialog.scrobbling_port_entry.cget("state")) == "normal"


class TestScrobblingSettingsIntegration:
    """Test integration of scrobbling settings with the app."""

    @pytest.fixture
    def root(self):
        """Create a Tk root window for testing."""
        root = tk.Tk()
        root.withdraw()
        yield root
        root.destroy()

    def test_settings_dialog_accepts_scrobbling_manager(self, root):
        """Test that SettingsDialog can accept a scrobbling manager."""
        mock_config = Mock()
        # Mock config.get to return sensible defaults
        def config_get(key, default=None):
            config_values = {
                "check_updates": True,
                "minimize_to_tray": False,
                "start_minimized": False,
                "theme": "light",
                "mal_client_id": "",
                "mal_code_verifier": "",
                "scrobbling": {"enabled": False, "port": 7834}
            }
            return config_values.get(key, default)
        mock_config.get = Mock(side_effect=config_get)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_manager = Mock(spec=ScrobblingManager)
        mock_manager.enabled = False
        mock_manager.port = 7834
        mock_manager.get_status = Mock(return_value={
            "enabled": False,
            "running": False,
            "port": 7834,
            "clients": 0,
            "sessions": 0
        })
        mock_manager.is_running = Mock(return_value=False)

        # Create dialog with scrobbling manager
        dialog = SettingsDialog(
            root,
            config=mock_config,
            scrobbling_manager=mock_manager
        )

        # Verify manager is stored
        assert dialog.scrobbling_manager is mock_manager

    def test_settings_dialog_creates_tab_only_with_manager(self, root):
        """Test that scrobbling tab is only created when manager is provided."""
        mock_config = Mock()
        # Mock config.get to return sensible defaults
        def config_get(key, default=None):
            config_values = {
                "check_updates": True,
                "minimize_to_tray": False,
                "start_minimized": False,
                "theme": "light",
                "mal_client_id": "",
                "mal_code_verifier": "",
                "scrobbling": {"enabled": False, "port": 7834}
            }
            return config_values.get(key, default)
        mock_config.get = Mock(side_effect=config_get)
        mock_config.set = Mock()
        mock_config.save = Mock()

        # Create dialog without scrobbling manager
        dialog_without = SettingsDialog(root, config=mock_config)
        tab_names = [dialog_without.notebook.tab(i, "text") for i in range(dialog_without.notebook.index("end"))]
        assert "Scrobbling" not in tab_names

        # Create dialog with scrobbling manager
        mock_manager = Mock(spec=ScrobblingManager)
        mock_manager.enabled = False
        mock_manager.port = 7834
        mock_manager.get_status = Mock(return_value={
            "enabled": False,
            "running": False,
            "port": 7834,
            "clients": 0,
            "sessions": 0
        })
        mock_manager.is_running = Mock(return_value=False)
        dialog_with = SettingsDialog(
            root,
            config=mock_config,
            scrobbling_manager=mock_manager
        )
        tab_names = [dialog_with.notebook.tab(i, "text") for i in range(dialog_with.notebook.index("end"))]
        assert "Scrobbling" in tab_names


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])