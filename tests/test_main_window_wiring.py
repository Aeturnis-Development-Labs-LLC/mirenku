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

from app_context import AppContext
from models.database import Database
from services.anime_service import AnimeService
from services.sync_service import SyncService
from utils.persistence import PersistenceManager


def make_test_context(tmp_path, db, mal_auth_manager=None):
    """AppContext with real core services and no MAL/scrobbling machinery —
    the injectability MainWindow gains from R1"""
    mock_config = Mock()
    mock_config.get_db_path.return_value = db.db_path
    mock_config.get_data_directory.return_value = tmp_path
    mock_config.get.side_effect = lambda key, default=None: default

    auth = mal_auth_manager or Mock()
    if mal_auth_manager is None:
        auth.oauth_client = None
        auth.is_authenticated.return_value = False

    return AppContext(
        config=mock_config,
        db=db,
        anime_service=AnimeService(db),
        persistence=PersistenceManager(mock_config, db),
        mal_service=Mock(),
        image_service=Mock(),
        mal_auth_manager=auth,
        scrobbling_manager=None,
        mal_api_v2_service=None,
        sync_service=SyncService(db, None, None),
    )


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

        context = make_test_context(tmp_path, db)

        with patch("ui.main_window.SmartDatabaseWatcher") as mock_watcher:
            from ui.main_window import MainWindow

            MainWindow(root, context)

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

        mock_auth_manager = Mock()
        mock_auth_manager.oauth_client.authorize.side_effect = RuntimeError("boom")

        context = make_test_context(tmp_path, db, mal_auth_manager=mock_auth_manager)

        with patch("ui.main_window.SmartDatabaseWatcher"):
            from ui.main_window import MainWindow

            window = MainWindow(root, context)

            with patch("tkinter.messagebox.showerror") as mock_error:
                window._perform_mal_auth()
                root.update()  # drain the after() queue

                mock_error.assert_called_once()
                assert "boom" in mock_error.call_args[0][1]

        db.disconnect()

    def test_main_window_uses_context_services(self, root, tmp_path):
        """Regression (R1): MainWindow must use the injected collaborators,
        not construct its own."""
        db_path = tmp_path / "anime_tracker.db"
        db = Database(db_path)
        db.initialize()

        context = make_test_context(tmp_path, db)

        with patch("ui.main_window.SmartDatabaseWatcher"):
            from ui.main_window import MainWindow

            window = MainWindow(root, context)

            assert window.db is context.db
            assert window.service is context.anime_service
            assert window.config is context.config
            assert window.sync_service is context.sync_service
            assert window.mal_auth_manager is context.mal_auth_manager

        db.disconnect()
