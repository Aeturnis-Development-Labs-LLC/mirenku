"""
Regression tests for MainWindow collaborator wiring
"""

import pytest
import sys
import os
import tkinter as tk
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.database import Database


@pytest.mark.gui
class TestMainWindowWiring:
    @pytest.fixture
    def root(self):
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except:
            pass

    def test_db_watcher_watches_real_database_path(self, root, tmp_path):
        """Regression (F1): the auto-refresh watcher must watch the actual DB
        file from config, not a re-derived filename. It silently watched a
        nonexistent 'anime.db' while the real file is 'anime_tracker.db'."""
        db_path = tmp_path / "anime_tracker.db"
        db = Database(db_path)
        db.initialize()

        mock_config = Mock()
        mock_config.get_db_path.return_value = db_path
        mock_config.get_data_directory.return_value = tmp_path
        mock_config.get.side_effect = lambda key, default=None: default

        mock_auth_manager = Mock()
        mock_auth_manager.oauth_client = None

        with patch("ui.main_window.Config", return_value=mock_config), \
             patch("ui.mal_auth_dialog.MALAuthManager", return_value=mock_auth_manager), \
             patch("ui.main_window.SmartDatabaseWatcher") as mock_watcher:
            from ui.main_window import MainWindow

            MainWindow(root, db)

            watched_path = mock_watcher.call_args.kwargs["db_path"]
            assert watched_path == db_path
            assert watched_path.name == "anime_tracker.db"
            assert watched_path.exists()

        db.disconnect()


    def test_auth_error_reaches_error_dialog(self, root, tmp_path):
        """Regression (F4): the auth except-branch referenced an unbound
        exception variable, so real auth failures raised NameError inside
        the after-callback instead of showing the error dialog."""
        db_path = tmp_path / "anime_tracker.db"
        db = Database(db_path)
        db.initialize()

        mock_config = Mock()
        mock_config.get_db_path.return_value = db_path
        mock_config.get_data_directory.return_value = tmp_path
        mock_config.get.side_effect = lambda key, default=None: default

        mock_auth_manager = Mock()
        mock_auth_manager.oauth_client.authorize.side_effect = RuntimeError("boom")

        with patch("ui.main_window.Config", return_value=mock_config), \
             patch("ui.mal_auth_dialog.MALAuthManager", return_value=mock_auth_manager), \
             patch("ui.main_window.SmartDatabaseWatcher"):
            from ui.main_window import MainWindow

            window = MainWindow(root, db)
            window.mal_auth_manager = mock_auth_manager

            with patch("tkinter.messagebox.showerror") as mock_error:
                window._perform_mal_auth()
                root.update()  # drain the after() queue

                mock_error.assert_called_once()
                assert "boom" in mock_error.call_args[0][1]

        db.disconnect()
