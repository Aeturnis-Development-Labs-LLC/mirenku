"""
Test suite for Settings Dialog with Protocol Management
"""

import pytest
import sys
import os
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui.settings_dialog import SettingsDialog


class TestSettingsDialogUI:
    """Test Settings Dialog UI components"""
    
    @pytest.fixture
    def root(self):
        """Create root window for testing"""
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except:
            pass  # Handle if already destroyed
    
    @pytest.fixture
    def mock_managers(self):
        """Mock managers for settings"""
        first_run = Mock()
        first_run.get_preference.return_value = None
        first_run.set_preference.return_value = None
        
        protocol = Mock()
        protocol.is_registered.return_value = True
        protocol.get_registered_path.return_value = "C:\\Program Files\\Mirenku\\mirenku.exe"
        protocol.register_protocol.return_value = True
        protocol.unregister_protocol.return_value = True
        
        return first_run, protocol
    
    def test_dialog_creation(self, root, mock_managers):
        """Test settings dialog is created properly"""
        first_run_mgr, protocol_mgr = mock_managers
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.dialog is not None
        assert dialog.dialog.winfo_exists()
        assert dialog.dialog.title() == "Settings"
        
        dialog.dialog.destroy()
    
    def test_notebook_tabs_exist(self, root, mock_managers):
        """Test that notebook with tabs exists"""
        first_run_mgr, protocol_mgr = mock_managers
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.notebook is not None
        tabs = dialog.notebook.tabs()
        assert len(tabs) >= 2  # At least General and Protocol tabs
        
        dialog.dialog.destroy()
    
    def test_protocol_tab_exists(self, root, mock_managers):
        """Test protocol tab exists with correct content"""
        first_run_mgr, protocol_mgr = mock_managers
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Check protocol tab exists
        assert dialog.protocol_frame is not None
        
        # Check for status label
        assert dialog.protocol_status_label is not None
        
        dialog.dialog.destroy()
    
    def test_protocol_registration_status_shown(self, root, mock_managers):
        """Test protocol registration status is displayed"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.is_registered.return_value = True
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        status_text = dialog.protocol_status_label.cget("text")
        assert "registered" in status_text.lower()
        
        dialog.dialog.destroy()
    
    def test_register_button_when_not_registered(self, root, mock_managers):
        """Test register button appears when protocol not registered"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.is_registered.return_value = False
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.register_button is not None
        assert dialog.register_button.cget("text") == "Register Protocol"
        
        dialog.dialog.destroy()
    
    def test_unregister_button_when_registered(self, root, mock_managers):
        """Test unregister button appears when protocol is registered"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.is_registered.return_value = True
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.unregister_button is not None
        assert dialog.unregister_button.cget("text") == "Unregister Protocol"
        
        dialog.dialog.destroy()
    
    def test_test_protocol_button_exists(self, root, mock_managers):
        """Test that Test Protocol button exists"""
        first_run_mgr, protocol_mgr = mock_managers
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.test_button is not None
        assert "test" in dialog.test_button.cget("text").lower()
        
        dialog.dialog.destroy()
    
    def test_auto_reregister_checkbox(self, root, mock_managers):
        """Test auto-reregister checkbox exists"""
        first_run_mgr, protocol_mgr = mock_managers
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.auto_reregister_var is not None
        assert dialog.auto_reregister_checkbox is not None
        
        dialog.dialog.destroy()


class TestSettingsDialogBehavior:
    """Test Settings Dialog behavior"""
    
    @pytest.fixture
    def root(self):
        """Create root window for testing"""
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except:
            pass
    
    @pytest.fixture
    def mock_managers(self):
        """Mock managers"""
        first_run = Mock()
        first_run.get_preference.return_value = True
        first_run.set_preference.return_value = None
        
        protocol = Mock()
        protocol.is_registered.return_value = False
        protocol.register_protocol.return_value = True
        protocol.unregister_protocol.return_value = True
        
        return first_run, protocol
    
    def test_register_protocol_button_action(self, root, mock_managers):
        """Test register protocol button functionality"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.is_registered.return_value = False
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Click register button
        dialog._on_register_protocol()
        
        # Verify protocol was registered
        protocol_mgr.register_protocol.assert_called_once()
        first_run_mgr.set_preference.assert_any_call("protocol_registered", True)
    
    def test_unregister_protocol_button_action(self, root, mock_managers):
        """Test unregister protocol button functionality"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.is_registered.return_value = True
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        with patch('tkinter.messagebox.askyesno', return_value=True):
            # Click unregister button
            dialog._on_unregister_protocol()
            
            # Verify protocol was unregistered
            protocol_mgr.unregister_protocol.assert_called_once()
            first_run_mgr.set_preference.assert_any_call("protocol_registered", False)
    
    def test_unregister_cancelled(self, root, mock_managers):
        """Test unregister cancellation"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.is_registered.return_value = True
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        with patch('tkinter.messagebox.askyesno', return_value=False):
            dialog._on_unregister_protocol()
            
            # Should not unregister if user cancels
            protocol_mgr.unregister_protocol.assert_not_called()
    
    @patch('webbrowser.open')
    def test_test_protocol_button(self, mock_browser, root, mock_managers):
        """Test the Test Protocol button opens test URL"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Click test button
        dialog._on_test_protocol()
        
        # Should open browser with test URL
        mock_browser.assert_called_once()
        call_args = mock_browser.call_args[0][0]
        assert "mirenku://" in call_args
    
    def test_auto_reregister_preference_saved(self, root, mock_managers):
        """Test auto-reregister preference is saved"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Change auto-reregister setting
        dialog.auto_reregister_var.set(False)
        dialog._on_save()
        
        # Verify preference was saved
        first_run_mgr.set_preference.assert_any_call("auto_reregister", False)
    
    def test_refresh_status_updates_ui(self, root, mock_managers):
        """Test refresh status updates UI correctly"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Change registration status
        protocol_mgr.is_registered.return_value = True
        dialog._refresh_protocol_status()
        
        # Status should be updated
        status_text = dialog.protocol_status_label.cget("text")
        assert "registered" in status_text.lower()
    
    def test_save_button_saves_all_settings(self, root, mock_managers):
        """Test Save button saves all settings"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Change some settings
        dialog.auto_reregister_var.set(False)
        
        # Click Save
        dialog._on_save()
        
        # Verify settings were saved
        assert first_run_mgr.set_preference.called
        assert dialog.result == "save"
    
    def test_cancel_button_discards_changes(self, root, mock_managers):
        """Test Cancel button discards changes"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        # Change settings but click Cancel
        dialog.auto_reregister_var.set(False)
        dialog._on_cancel()
        
        # Should not save preferences
        first_run_mgr.set_preference.assert_not_called()
        assert dialog.result == "cancel"
    
    def test_general_tab_has_theme_option(self, root, mock_managers):
        """Test general tab has theme selection"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = SettingsDialog(root, first_run_mgr, protocol_mgr)
        
        assert dialog.theme_var is not None
        assert dialog.theme_combo is not None
        
        # Should have at least light and dark themes
        themes = dialog.theme_combo['values']
        assert len(themes) >= 2


class TestSettingsIntegration:
    """Test integration with main window"""
    
    @patch('ui.settings_dialog.SettingsDialog')
    def test_show_from_main_window(self, mock_dialog_class):
        """Test settings can be shown from main window"""
        mock_dialog = Mock()
        mock_dialog.result = "save"
        mock_dialog_class.return_value = mock_dialog
        
        # Import after mocking to use the mock
        from ui.settings_dialog import show_settings_dialog
        
        root = tk.Tk()
        root.withdraw()
        
        result = show_settings_dialog(root)
        
        assert result == "save"
        mock_dialog_class.assert_called_once()
        
        root.destroy()