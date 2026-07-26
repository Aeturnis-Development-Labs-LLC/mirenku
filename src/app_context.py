"""
Application composition root.

All service construction lives here, not inside widgets. MainWindow (and any
future frontend) receives a fully-built AppContext and only wires callbacks —
which is what makes the GUI layer swappable.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from models.database import Database
from services.anime_service import AnimeService
from utils.config import Config
from utils.persistence import PersistenceManager

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """The application's non-UI collaborators, fully constructed."""

    config: Config
    db: Database
    anime_service: AnimeService
    persistence: PersistenceManager
    mal_service: "object"
    image_service: "object"
    mal_auth_manager: "object"
    scrobbling_manager: Optional["object"]
    mal_api_v2_service: Optional["object"]
    sync_service: "object"

    @classmethod
    def build(cls, config: Config, db: Database) -> "AppContext":
        """Construct all services.

        Must be called after tk.Tk() exists: MALAuthManager may prompt for a
        client ID with a Tk dialog when no mal_config.json is present.
        """
        anime_service = AnimeService(db)
        persistence = PersistenceManager(config, db)

        from services.image_service import ImageService
        from services.mal_service import MALService

        mal_service = MALService(config.get_data_directory() / "mal_cache")
        image_service = ImageService(config.get_data_directory() / "image_cache")

        # Client ID is embedded in the application / read from mal_config.json
        from ui.mal_auth_dialog import MALAuthManager

        mal_auth_manager = MALAuthManager(config.get_data_directory())

        # WIP scrobbling feature — off by default, absent unless its optional
        # dependencies are installed
        scrobbling_manager = None
        try:
            from services.scrobbling_manager import ScrobblingManager

            scrobbling_manager = ScrobblingManager(anime_service, config)
            scrobbling_manager.start()  # No-op unless enabled in settings
        except Exception as e:
            logger.warning(f"Failed to initialize ScrobblingManager: {e}")

        # MAL API v2 service only if already authenticated (silent check)
        mal_api_v2_service = None
        if mal_auth_manager.is_authenticated(silent=True):
            from services.mal_api_v2_service import MALAPIv2Service

            mal_api_v2_service = MALAPIv2Service(mal_auth_manager.oauth_client)

        from services.sync_service import SyncService

        sync_service = SyncService(
            db,
            mal_api_v2_service,
            getattr(mal_auth_manager, "oauth_client", None),
        )

        return cls(
            config=config,
            db=db,
            anime_service=anime_service,
            persistence=persistence,
            mal_service=mal_service,
            image_service=image_service,
            mal_auth_manager=mal_auth_manager,
            scrobbling_manager=scrobbling_manager,
            mal_api_v2_service=mal_api_v2_service,
            sync_service=sync_service,
        )
