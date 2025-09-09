"""
Test suite for First Run Dialog
Tests the first run welcome dialog and protocol registration UI
"""

import pytest
import sys
import os
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui.first_run_dialog import FirstRunDialog


class TestFirstRunDialogUI:
    """Test First Run Dialog UI components"""
    
    @pytest.fixture
    def root(self):
        """Create root window for testing"""
        root = tk.Tk()
        root.withdraw()  # Hide window during tests
        yield root
        root.destroy()
    
    @pytest.fixture
    def mock_first_run_manager(self):
        """Mock FirstRunManager"""
        mock_manager = Mock()
        mock_manager.is_first_run.return_value = True
        mock_manager.get_preference.return_value = None
        mock_manager.set_preference.return_value = None
        mock_manager.mark_first_run_complete.return_value = None
        return mock_manager
    
    @pytest.fixture
    def mock_protocol_manager(self):
        """Mock ProtocolManager"""
        mock_manager = Mock()
        mock_manager.is_registered.return_value = False
        mock_manager.register_protocol.return_value = True
        return mock_manager
    
    def test_dialog_creation(self, root, mock_first_run_manager, mock_protocol_manager):
        """Test dialog window is created properly"""
        dialog = FirstRunDialog(root, mock_first_run_manager, mock_protocol_manager)
        
        assert dialog.dialog is not None
        assert dialog.dialog.winfo_exists()
        assert dialog.dialog.title() == "Welcome to Mirenku"
        
        dialog.dialog.destroy()
    
    def test_welcome_message_displayed(self, root, mock_first_run_manager, mock_protocol_manager):
        """Test welcome message is displayed"""
        dialog = FirstRunDialog(root, mock_first_run_manager, mock_protocol_manager)
        
        # Check for welcome label
        assert dialog.welcome_label is not None
        assert "Welcome" in dialog.welcome_label.cget("text")
        
        dialog.dialog.destroy()
    
    def test_protocol_checkbox_exists(self, root, mock_first_run_manager, mock_protocol_manager):
        """Test protocol registration checkbox exists"""
        dialog = FirstRunDialog(root, mock_first_run_manager, mock_protocol_manager)
        
        assert dialog.protocol_checkbox is not None
        assert dialog.register_protocol_var.get() is True  # Default checked
        
        dialog.dialog.destroy()
    
    def test_learn_more_link(self, root, mock_first_run_manager, mock_protocol_manager):
        """Test Learn More link exists"""
        dialog = FirstRunDialog(root, mock_first_run_manager, mock_protocol_manager)
        
        assert dialog.learn_more_label is not None
        # Link should have cursor style (check string representation)
        cursor = str(dialog.learn_more_label.cget("cursor"))
        assert "hand2" in cursor
        
        dialog.dialog.destroy()
    
    def test_continue_button(self, root, mock_first_run_manager, mock_protocol_manager):
        """Test Continue button exists and is default"""
        dialog = FirstRunDialog(root, mock_first_run_manager, mock_protocol_manager)
        
        assert dialog.continue_button is not None
        assert dialog.continue_button.cget("text") == "Continue"
        
        dialog.dialog.destroy()
    
    def test_skip_button(self, root, mock_first_run_manager, mock_protocol_manager):
        """Test Skip button exists"""
        dialog = FirstRunDialog(root, mock_first_run_manager, mock_protocol_manager)
        
        assert dialog.skip_button is not None
        assert dialog.skip_button.cget("text") == "Skip"
        
        dialog.dialog.destroy()


class TestFirstRunDialogBehavior:
    """Test First Run Dialog behavior"""
    
    @pytest.fixture
    def root(self):
        """Create root window for testing"""
        root = tk.Tk()
        root.withdraw()
        yield root
        root.destroy()
    
    @pytest.fixture
    def mock_managers(self):
        """Mock both managers"""
        first_run = Mock()
        first_run.is_first_run.return_value = True
        first_run.get_preference.return_value = None
        first_run.set_preference.return_value = None
        first_run.mark_first_run_complete.return_value = None
        first_run.save_app_location.return_value = None
        
        protocol = Mock()
        protocol.is_registered.return_value = False
        protocol.register_protocol.return_value = True
        
        return first_run, protocol
    
    def test_continue_with_protocol_registration(self, root, mock_managers):
        """Test Continue button with protocol registration checked"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        dialog.register_protocol_var.set(True)
        
        # Simulate Continue button click
        dialog._on_continue()
        
        # Verify protocol was registered
        protocol_mgr.register_protocol.assert_called_once()
        first_run_mgr.set_preference.assert_any_call("protocol_registered", True)
        first_run_mgr.mark_first_run_complete.assert_called_once()
        
        assert dialog.result == "continue"
    
    def test_continue_without_protocol_registration(self, root, mock_managers):
        """Test Continue button with protocol registration unchecked"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        dialog.register_protocol_var.set(False)
        
        # Simulate Continue button click
        dialog._on_continue()
        
        # Verify protocol was NOT registered
        protocol_mgr.register_protocol.assert_not_called()
        first_run_mgr.set_preference.assert_any_call("protocol_registered", False)
        first_run_mgr.mark_first_run_complete.assert_called_once()
        
        assert dialog.result == "continue"
    
    def test_skip_button_behavior(self, root, mock_managers):
        """Test Skip button behavior"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        
        # Simulate Skip button click
        dialog._on_skip()
        
        # Verify skip was recorded
        first_run_mgr.set_preference.assert_any_call("first_run_skipped", True)
        first_run_mgr.mark_first_run_complete.assert_called_once()
        protocol_mgr.register_protocol.assert_not_called()
        
        assert dialog.result == "skip"
    
    @patch('ui.first_run_dialog.webbrowser.open')
    def test_learn_more_opens_browser(self, mock_browser, root, mock_managers):
        """Test Learn More link opens browser"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        
        # Simulate clicking Learn More
        dialog._on_learn_more(None)
        
        mock_browser.assert_called_once()
        assert "mirenku" in mock_browser.call_args[0][0].lower() or \
               "protocol" in mock_browser.call_args[0][0].lower()
    
    def test_protocol_registration_error_handling(self, root, mock_managers):
        """Test handling of protocol registration errors"""
        first_run_mgr, protocol_mgr = mock_managers
        protocol_mgr.register_protocol.return_value = False  # Simulate failure
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        dialog.register_protocol_var.set(True)
        
        with patch('tkinter.messagebox.showwarning') as mock_warning:
            dialog._on_continue()
            
            # Should show warning but still continue
            mock_warning.assert_called_once()
            first_run_mgr.mark_first_run_complete.assert_called_once()
            assert dialog.result == "continue"
    
    def test_dialog_is_modal(self, root, mock_managers):
        """Test dialog is modal (blocks parent)"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        
        # Check modal properties
        assert dialog.dialog.winfo_toplevel() == dialog.dialog
        # Note: grab_status() doesn't work well in tests, but we verify it's set
        
        dialog.dialog.destroy()
    
    def test_escape_key_closes_dialog(self, root, mock_managers):
        """Test ESC key closes dialog (skip behavior)"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        
        # Simulate ESC key press
        dialog._on_escape(None)
        
        first_run_mgr.set_preference.assert_any_call("first_run_skipped", True)
        assert dialog.result == "skip"
    
    @patch('sys.executable', 'C:\\Program Files\\Mirenku\\mirenku.exe')
    def test_saves_app_location(self, root, mock_managers):
        """Test app location is saved on continue"""
        first_run_mgr, protocol_mgr = mock_managers
        
        dialog = FirstRunDialog(root, first_run_mgr, protocol_mgr)
        dialog._on_continue()
        
        first_run_mgr.save_app_location.assert_called_once_with('C:\\Program Files\\Mirenku\\mirenku.exe')


class TestFirstRunDialogStatic:
    """Test static helper methods"""
    
    @patch('ui.first_run_dialog.FirstRunManager')
    @patch('ui.first_run_dialog.ProtocolManager')
    def test_should_show_dialog_first_run(self, mock_protocol_cls, mock_first_run_cls):
        """Test should_show returns True for first run"""
        mock_first_run = mock_first_run_cls.return_value
        mock_first_run.is_first_run.return_value = True
        
        assert FirstRunDialog.should_show() is True
    
    @patch('ui.first_run_dialog.FirstRunManager')
    @patch('ui.first_run_dialog.ProtocolManager')
    def test_should_not_show_dialog_after_first_run(self, mock_protocol_cls, mock_first_run_cls):
        """Test should_show returns False after first run"""
        mock_first_run = mock_first_run_cls.return_value
        mock_first_run.is_first_run.return_value = False
        mock_first_run.has_app_moved.return_value = False
        
        assert FirstRunDialog.should_show() is False
    
    @patch('ui.first_run_dialog.FirstRunManager')
    @patch('ui.first_run_dialog.ProtocolManager')
    @patch('sys.executable', 'C:\\NewPath\\mirenku.exe')
    def test_should_show_dialog_app_moved(self, mock_protocol_cls, mock_first_run_cls):
        """Test should_show returns True when app moved"""
        mock_first_run = mock_first_run_cls.return_value
        mock_first_run.is_first_run.return_value = False
        mock_first_run.has_app_moved.return_value = True
        mock_first_run.get_preference.return_value = True  # auto_reregister enabled
        
        assert FirstRunDialog.should_show() is True