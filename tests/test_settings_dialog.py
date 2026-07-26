"""
Test suite for Settings Dialog
"""

import pytest
import sys
import os
import tkinter as tk
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="module")
def root():
    """One root window shared across the module — rapid Tk() create/destroy
    cycles are flaky on Windows"""
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except:
        pass


def make_mock_config():
    """Config mock whose get() returns the supplied default"""
    config = Mock()
    config.get.side_effect = lambda key, default=None: default
    config.set.return_value = None
    return config


def make_mock_first_run_manager():
    """FirstRunManager mock whose get_preference() returns the supplied default"""
    first_run = Mock()
    first_run.get_preference.side_effect = lambda key, default=None: default
    first_run.set_preference.return_value = None
    return first_run


class TestSettingsDialogUI:
    """Test Settings Dialog UI components"""

    @pytest.fixture
    def dialog(self, root):
        """Create dialog with mocked collaborators"""
        dialog = SettingsDialog(
            root,
            config=make_mock_config(),
            first_run_manager=make_mock_first_run_manager(),
        )
        yield dialog
        try:
            dialog.dialog.destroy()
        except:
            pass

    def test_dialog_creation(self, dialog):
        """Test settings dialog is created properly"""
        assert dialog.dialog is not None
        assert dialog.dialog.winfo_exists()
        assert dialog.dialog.title() == "Settings"

    def test_notebook_tabs_exist(self, dialog):
        """Test that notebook with tabs exists"""
        assert dialog.notebook is not None
        tabs = dialog.notebook.tabs()
        assert len(tabs) >= 3  # General, Sync, and Updates tabs

    def test_general_tab_has_theme_option(self, dialog):
        """Test general tab has theme selection"""
        assert dialog.theme_var is not None
        assert dialog.theme_combo is not None

        # Should have at least light and dark themes
        themes = dialog.theme_combo['values']
        assert len(themes) >= 2

    def test_sync_tab_has_conflict_options(self, dialog):
        """Test sync tab exposes conflict resolution setting"""
        assert dialog.conflict_var is not None
        assert dialog.conflict_var.get() == "ask"

    def test_updates_tab_defaults_off(self, dialog):
        """Test update checking defaults to disabled (privacy default)"""
        assert dialog.check_updates_var.get() is False


class TestSettingsDialogBehavior:
    """Test Settings Dialog behavior"""

    @pytest.fixture
    def managers(self):
        """Mocked collaborators"""
        return make_mock_config(), make_mock_first_run_manager()

    def test_save_button_saves_all_settings(self, root, managers):
        """Test Save button saves all settings"""
        config, first_run_mgr = managers
        dialog = SettingsDialog(root, config=config, first_run_manager=first_run_mgr)

        dialog.theme_var.set("Dark")
        dialog._on_save()

        first_run_mgr.set_preference.assert_any_call("theme", "Dark")
        config.set.assert_any_call("check_for_updates", False)
        assert dialog.result is True

    def test_cancel_button_discards_changes(self, root, managers):
        """Test Cancel button discards changes"""
        config, first_run_mgr = managers
        dialog = SettingsDialog(root, config=config, first_run_manager=first_run_mgr)

        # Change settings but click Cancel
        dialog.theme_var.set("Dark")
        dialog._on_cancel()

        # Should not save preferences
        first_run_mgr.set_preference.assert_not_called()
        assert dialog.result == "cancel"

    def test_update_check_toggle_enables_dialog_option(self, root, managers):
        """Test enabling update checks enables the detail-dialog checkbox"""
        config, first_run_mgr = managers
        dialog = SettingsDialog(root, config=config, first_run_manager=first_run_mgr)

        assert str(dialog.dialog_checkbox.cget("state")) == "disabled"
        dialog.check_updates_var.set(True)
        dialog._on_update_check_toggle()
        assert str(dialog.dialog_checkbox.cget("state")) == "normal"

        dialog.dialog.destroy()


class TestSettingsIntegration:
    """Test integration with main window"""

    @patch('ui.settings_dialog.SettingsDialog')
    def test_show_from_main_window(self, mock_dialog_class, root):
        """Test settings can be shown from main window"""
        mock_dialog = Mock()
        mock_dialog.result = "save"
        mock_dialog_class.return_value = mock_dialog

        # Import after mocking to use the mock
        from ui.settings_dialog import show_settings_dialog

        # wait_window can't block on a Mock dialog; stub it out
        with patch.object(root, "wait_window"):
            result = show_settings_dialog(root)

        assert result == "save"
        mock_dialog_class.assert_called_once()
