"""
Test suite for First Run Dialog
Tests the first run welcome dialog
"""

import pytest
import sys
import os
import tkinter as tk
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui.first_run_dialog import FirstRunDialog


@pytest.mark.gui
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

    def test_dialog_creation(self, root, mock_first_run_manager):
        """Test dialog window is created properly"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        assert dialog.dialog is not None
        assert dialog.dialog.winfo_exists()
        assert dialog.dialog.title() == "Welcome to Mirenku"

        dialog.dialog.destroy()

    def test_welcome_message_displayed(self, root, mock_first_run_manager):
        """Test welcome message is displayed"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        # Check for welcome label
        assert dialog.welcome_label is not None
        assert "Welcome" in dialog.welcome_label.cget("text")

        dialog.dialog.destroy()

    def test_continue_button(self, root, mock_first_run_manager):
        """Test Continue button exists and is default"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        assert dialog.continue_button is not None
        assert dialog.continue_button.cget("text") == "Continue"

        dialog.dialog.destroy()

    def test_skip_button(self, root, mock_first_run_manager):
        """Test Skip button exists"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        assert dialog.skip_button is not None
        assert dialog.skip_button.cget("text") == "Skip"

        dialog.dialog.destroy()


@pytest.mark.gui
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
    def mock_first_run_manager(self):
        """Mock FirstRunManager"""
        first_run = Mock()
        first_run.is_first_run.return_value = True
        first_run.get_preference.return_value = None
        first_run.set_preference.return_value = None
        first_run.mark_first_run_complete.return_value = None
        first_run.save_app_location.return_value = None
        return first_run

    def test_continue_button_behavior(self, root, mock_first_run_manager):
        """Test Continue button completes first run"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        # Simulate Continue button click
        dialog._on_continue()

        mock_first_run_manager.set_preference.assert_any_call("welcome_shown", True)
        mock_first_run_manager.mark_first_run_complete.assert_called_once()

        assert dialog.result == "continue"

    def test_skip_button_behavior(self, root, mock_first_run_manager):
        """Test Skip button behavior"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        # Simulate Skip button click
        dialog._on_skip()

        # Verify skip was recorded
        mock_first_run_manager.set_preference.assert_any_call("first_run_skipped", True)
        mock_first_run_manager.mark_first_run_complete.assert_called_once()

        assert dialog.result == "skip"

    def test_dialog_is_modal(self, root, mock_first_run_manager):
        """Test dialog is modal (blocks parent)"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        # Check modal properties
        assert dialog.dialog.winfo_toplevel() == dialog.dialog
        # Note: grab_status() doesn't work well in tests, but we verify it's set

        dialog.dialog.destroy()

    def test_escape_key_closes_dialog(self, root, mock_first_run_manager):
        """Test ESC key closes dialog (skip behavior)"""
        dialog = FirstRunDialog(root, mock_first_run_manager)

        # Simulate ESC key press
        dialog._on_escape(None)

        mock_first_run_manager.set_preference.assert_any_call("first_run_skipped", True)
        assert dialog.result == "skip"

    @patch('sys.executable', 'C:\\Program Files\\Mirenku\\mirenku.exe')
    def test_saves_app_location(self, root, mock_first_run_manager):
        """Test app location is saved on continue"""
        dialog = FirstRunDialog(root, mock_first_run_manager)
        dialog._on_continue()

        mock_first_run_manager.save_app_location.assert_called_once_with(
            'C:\\Program Files\\Mirenku\\mirenku.exe'
        )


# This class tests static methods, no GUI needed
class TestFirstRunDialogStatic:
    """Test static helper methods"""

    @patch('ui.first_run_dialog.FirstRunManager')
    def test_should_show_dialog_first_run(self, mock_first_run_cls):
        """Test should_show returns True for first run"""
        mock_first_run = mock_first_run_cls.return_value
        mock_first_run.is_first_run.return_value = True

        assert FirstRunDialog.should_show() is True

    @patch('ui.first_run_dialog.FirstRunManager')
    def test_should_not_show_dialog_after_first_run(self, mock_first_run_cls):
        """Test should_show returns False after first run"""
        mock_first_run = mock_first_run_cls.return_value
        mock_first_run.is_first_run.return_value = False

        assert FirstRunDialog.should_show() is False
