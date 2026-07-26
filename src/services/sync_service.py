"""Synchronization service for MAL integration (Phase 3 functionality)"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Sync status for anime entries"""

    LOCAL_ONLY = "local_only"
    SYNCED = "synced"
    PENDING_UPLOAD = "pending_upload"
    PENDING_DOWNLOAD = "pending_download"
    CONFLICT = "conflict"


class SyncOperation(Enum):
    """Types of sync operations"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncService:
    """Service for managing MAL synchronization"""

    def __init__(self, database, mal_api_v2_service=None, oauth_client=None):
        """Initialize sync service

        Args:
            database: Database instance
            mal_api_v2_service: MAL API v2 service instance
            oauth_client: OAuth2 client instance
        """
        self.db = database
        self.mal_api_service = mal_api_v2_service
        self.oauth_client = oauth_client
        self.is_authenticated = False
        self.sync_enabled = False

        # Check authentication through OAuth client
        if self.oauth_client:
            self.is_authenticated = self.oauth_client.is_authenticated()

    def refresh_authentication(self):
        """Refresh authentication status"""
        if self.oauth_client:
            self.is_authenticated = self.oauth_client.is_authenticated()
        return self.is_authenticated

    def get_sync_status(self, anime_id: int) -> SyncStatus:
        """Get sync status for an anime

        Args:
            anime_id: Anime ID

        Returns:
            SyncStatus enum value
        """
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT sync_status FROM anime WHERE id = ?", (anime_id,))
            result = cursor.fetchone()

            if result and result["sync_status"]:
                return SyncStatus(result["sync_status"])
            return SyncStatus.LOCAL_ONLY

    def set_sync_status(self, anime_id: int, status: SyncStatus):
        """Update sync status for an anime

        Args:
            anime_id: Anime ID
            status: New sync status
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                "UPDATE anime SET sync_status = ? WHERE id = ?", (status.value, anime_id)
            )
            logger.info(f"Updated sync status for anime {anime_id} to {status.value}")

    def queue_sync_operation(
        self, anime_id: int, operation: SyncOperation, data: Optional[Dict] = None
    ):
        """Queue a sync operation for later processing

        Args:
            anime_id: Anime ID
            operation: Type of operation
            data: Operation data (optional)
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sync_queue (anime_id, operation, data, status)
                VALUES (?, ?, ?, 'pending')
            """,
                (anime_id, operation.value, json.dumps(data) if data else None),
            )

            # Update anime sync status
            if operation == SyncOperation.DELETE:
                self.set_sync_status(anime_id, SyncStatus.LOCAL_ONLY)
            else:
                self.set_sync_status(anime_id, SyncStatus.PENDING_UPLOAD)

            logger.info(f"Queued {operation.value} operation for anime {anime_id}")

    def get_pending_sync_operations(self) -> List[Dict]:
        """Get all pending sync operations

        Returns:
            List of pending operations
        """
        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT sq.*, a.title, a.mal_id
                FROM sync_queue sq
                JOIN anime a ON sq.anime_id = a.id
                WHERE sq.status = 'pending'
                ORDER BY sq.created_at ASC
            """
            )

            operations = []
            for row in cursor.fetchall():
                op = dict(row)
                if op["data"]:
                    op["data"] = json.loads(op["data"])
                operations.append(op)

            return operations

    def get_sync_queue_count(self) -> int:
        """Get count of pending sync operations

        Returns:
            Number of pending operations
        """
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM sync_queue WHERE status = 'pending'")
            return cursor.fetchone()["count"]

    def process_sync_queue(self) -> Tuple[int, int, List[str]]:
        """Process pending sync operations

        Returns:
            Tuple of (successful, failed, error_messages)
        """
        if not self.is_authenticated:
            return 0, 0, ["MAL authentication required"]

        if not self.mal_api_service:
            return 0, 0, ["MAL API service not available"]

        pending = self.get_pending_sync_operations()

        # If no pending operations, push all local anime to MAL
        if not pending:
            # Get all local anime
            with self.db.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM anime
                    WHERE mal_id IS NOT NULL
                """
                )
                local_anime = cursor.fetchall()

            if not local_anime:
                return 0, 0, ["No anime with MAL IDs to sync"]

            successful = 0
            failed = 0
            errors = []

            for anime_data in local_anime:
                try:
                    # Sync anime to MAL
                    success = self.mal_api_service.sync_anime_from_local(dict(anime_data))
                    if success:
                        successful += 1
                        # Update sync status
                        self.set_sync_status(anime_data["id"], SyncStatus.SYNCED)
                    else:
                        failed += 1
                        errors.append(f"Failed to sync '{anime_data['title']}'")
                except Exception as e:
                    failed += 1
                    errors.append(f"Error syncing '{anime_data['title']}': {e!s}")

            return successful, failed, errors

        successful = 0
        failed = 0
        errors = []

        for op in pending:
            try:
                anime_id = op["anime_id"]
                mal_id = op["mal_id"]
                operation = op["operation"]

                if not mal_id:
                    errors.append(f"No MAL ID for anime '{op['title']}'")
                    failed += 1
                    continue

                # Get current anime data from database
                with self.db.get_cursor() as cursor:
                    cursor.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
                    anime_data = dict(cursor.fetchone())

                success = False

                if operation == "create" or operation == "update":
                    # Sync anime to MAL
                    success = self.mal_api_service.sync_anime_from_local(anime_data)

                elif operation == "delete":
                    # Remove from MAL list
                    success = self.mal_api_service.remove_anime_from_list(mal_id)

                if success:
                    successful += 1
                    self.mark_as_synced(anime_id)
                    logger.info(f"Successfully synced {operation} for anime '{op['title']}'")
                else:
                    failed += 1
                    errors.append(f"Failed to {operation} anime '{op['title']}'")

            except Exception as e:
                failed += 1
                errors.append(f"Error syncing '{op.get('title', 'Unknown')}': {e!s}")
                logger.error(f"Sync error for anime {op.get('anime_id')}: {e}")

        return successful, failed, errors

    def detect_conflicts(self) -> List[Dict]:
        """Detect sync conflicts between local and MAL data

        Returns:
            List of conflicts
        """
        conflicts = []

        with self.db.get_cursor() as cursor:
            # Find anime that have been modified locally since last sync
            cursor.execute(
                """
                SELECT id, title, mal_id, updated_at, last_mal_sync
                FROM anime
                WHERE mal_id IS NOT NULL
                AND sync_status != 'local_only'
                AND (
                    last_mal_sync IS NULL
                    OR updated_at > last_mal_sync
                )
            """
            )

            for row in cursor.fetchall():
                conflicts.append(
                    {
                        "anime_id": row["id"],
                        "title": row["title"],
                        "mal_id": row["mal_id"],
                        "local_updated": row["updated_at"],
                        "last_sync": row["last_mal_sync"],
                        "type": "local_change",
                    }
                )

        return conflicts

    def mark_as_synced(self, anime_id: int):
        """Mark an anime as successfully synced

        Args:
            anime_id: Anime ID
        """
        from utils.timezone import get_current_datetime

        now = get_current_datetime()

        with self.db.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE anime
                SET sync_status = ?, last_mal_sync = ?
                WHERE id = ?
            """,
                (SyncStatus.SYNCED.value, now, anime_id),
            )

            # Clear from sync queue
            cursor.execute(
                """
                UPDATE sync_queue
                SET status = 'completed', processed_at = ?
                WHERE anime_id = ? AND status = 'pending'
            """,
                (now, anime_id),
            )

    def get_sync_statistics(self) -> Dict:
        """Get synchronization statistics

        Returns:
            Dictionary with sync stats
        """
        stats = {}

        with self.db.get_cursor() as cursor:
            # Count by sync status
            cursor.execute(
                """
                SELECT sync_status, COUNT(*) as count
                FROM anime
                GROUP BY sync_status
            """
            )

            status_counts = {}
            for row in cursor.fetchall():
                if row["sync_status"]:
                    status_counts[row["sync_status"]] = row["count"]

            stats["by_status"] = status_counts
            stats["total_synced"] = status_counts.get("synced", 0)
            stats["pending_upload"] = status_counts.get("pending_upload", 0)
            stats["conflicts"] = status_counts.get("conflict", 0)

            # Get queue stats
            cursor.execute(
                """
                SELECT status, COUNT(*) as count
                FROM sync_queue
                GROUP BY status
            """
            )

            queue_counts = {}
            for row in cursor.fetchall():
                queue_counts[row["status"]] = row["count"]

            stats["queue"] = queue_counts
            stats["queue_pending"] = queue_counts.get("pending", 0)

            # Get last sync time
            cursor.execute(
                """
                SELECT MAX(last_mal_sync) as last_sync
                FROM anime
                WHERE last_mal_sync IS NOT NULL
            """
            )

            result = cursor.fetchone()
            if result and result["last_sync"]:
                stats["last_sync"] = result["last_sync"]
            else:
                stats["last_sync"] = None

            # Authentication status
            stats["authenticated"] = self.is_authenticated
            stats["sync_enabled"] = self.sync_enabled

        return stats

    def clear_sync_queue(self):
        """Clear all pending sync operations"""
        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM sync_queue WHERE status = 'pending'")
            cursor.execute(
                """
                UPDATE anime
                SET sync_status = 'local_only'
                WHERE sync_status IN ('pending_upload', 'pending_download')
            """
            )
            logger.info("Cleared sync queue")

    def push_to_mal(self, anime_id: int) -> bool:
        """Push a single anime to MAL

        Args:
            anime_id: Local anime ID

        Returns:
            True if successful
        """
        if not self.is_authenticated or not self.mal_api_service:
            logger.error("Cannot push to MAL without authentication")
            return False

        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
                anime_data = dict(cursor.fetchone())

                if not anime_data.get("mal_id"):
                    logger.error(f"No MAL ID for anime {anime_id}")
                    return False

                # Sync to MAL
                success = self.mal_api_service.sync_anime_from_local(anime_data)

                if success:
                    self.mark_as_synced(anime_id)
                    logger.info(f"Pushed anime {anime_id} to MAL")

                return success

        except Exception as e:
            logger.error(f"Failed to push anime {anime_id} to MAL: {e}")
            return False

    def pull_from_mal(self, mal_id: int) -> bool:
        """Pull anime data from MAL and update local

        Args:
            mal_id: MAL anime ID

        Returns:
            True if successful
        """
        if not self.is_authenticated or not self.mal_api_service:
            logger.error("Cannot pull from MAL without authentication")
            return False

        try:
            # Get data from MAL
            mal_data = self.mal_api_service.sync_anime_to_local(mal_id)

            if not mal_data:
                logger.error(f"Failed to get data for MAL ID {mal_id}")
                return False

            # Update local database
            with self.db.get_cursor() as cursor:
                # Check if anime exists locally
                cursor.execute("SELECT id FROM anime WHERE mal_id = ?", (mal_id,))
                existing = cursor.fetchone()

                if existing:
                    # Update existing anime
                    anime_id = existing["id"]
                    cursor.execute(
                        """
                        UPDATE anime SET
                            title = ?, status = ?, episodes_watched = ?,
                            total_episodes = ?, score = ?, synopsis = ?,
                            genres = ?, studio = ?, image_url = ?,
                            notes = ?, sync_status = ?, last_mal_sync = ?
                        WHERE id = ?
                    """,
                        (
                            mal_data["title"],
                            mal_data["status"],
                            mal_data["episodes_watched"],
                            mal_data["total_episodes"],
                            mal_data["score"],
                            mal_data["synopsis"],
                            json.dumps(mal_data["genres"]) if mal_data["genres"] else None,
                            mal_data["studio"],
                            mal_data["image_url"],
                            mal_data["notes"],
                            SyncStatus.SYNCED.value,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            anime_id,
                        ),
                    )
                else:
                    # Create new anime
                    from models.anime import Anime
                    from models.anime_repository import AnimeRepository

                    repo = AnimeRepository(self.db)
                    anime = Anime(
                        title=mal_data["title"],
                        status=mal_data["status"],
                        episodes_watched=mal_data["episodes_watched"],
                        total_episodes=mal_data["total_episodes"],
                        score=mal_data["score"],
                        mal_id=mal_id,
                    )
                    anime.synopsis = mal_data["synopsis"]
                    anime.genres = mal_data["genres"]
                    anime.studio = mal_data["studio"]
                    anime.image_url = mal_data["image_url"]
                    anime.notes = mal_data["notes"]

                    new_id = repo.create(anime)
                    # to_dict() strips the sync fields, so stamp them directly
                    cursor.execute(
                        "UPDATE anime SET sync_status = ?, last_mal_sync = ? WHERE id = ?",
                        (
                            SyncStatus.SYNCED.value,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            new_id,
                        ),
                    )

                logger.info(f"Pulled MAL ID {mal_id} from MAL")
                return True

        except Exception as e:
            logger.error(f"Failed to pull MAL ID {mal_id}: {e}")
            return False

    def full_sync_from_mal(self) -> Tuple[int, int, List[str]]:
        """Pull entire anime list from MAL

        Returns:
            Tuple of (added, updated, errors)
        """
        if not self.is_authenticated or not self.mal_api_service:
            return 0, 0, ["MAL authentication required"]

        try:
            # Get full anime list from MAL
            mal_list = self.mal_api_service.get_full_animelist()

            added = 0
            updated = 0
            errors = []

            for mal_anime in mal_list:
                try:
                    anime_node = mal_anime.get("node", {})
                    mal_id = anime_node.get("id")

                    if not mal_id:
                        continue

                    # Get list status from the MAL list data
                    list_status = mal_anime.get("list_status", {})

                    # Map MAL status to local status
                    status_map = {
                        "watching": "Watching",
                        "completed": "Completed",
                        "on_hold": "On Hold",
                        "dropped": "Dropped",
                        "plan_to_watch": "Plan to Watch",
                    }

                    mal_status = list_status.get("status", "plan_to_watch")
                    local_status = status_map.get(mal_status, "Plan to Watch")

                    # Prepare anime data from list
                    # Get total episodes - MAL uses 0 for unknown/ongoing
                    total_eps = anime_node.get("num_episodes", 0)
                    # Only set to None if it's truly 0 (unknown), otherwise keep the value
                    # But we need to check the database constraint
                    if total_eps == 0:
                        total_eps = None  # Database requires NULL instead of 0

                    # Get score - 0 means not scored
                    score = list_status.get("score", 0)
                    if score == 0:
                        score = None

                    anime_data = {
                        "mal_id": mal_id,
                        "title": anime_node.get("title", "Unknown"),
                        "status": local_status,
                        "episodes_watched": list_status.get("num_episodes_watched", 0),
                        "total_episodes": total_eps,
                        "score": score,
                    }

                    # Check if exists locally and update/insert
                    with self.db.get_cursor() as cursor:
                        cursor.execute("SELECT id FROM anime WHERE mal_id = ?", (mal_id,))
                        existing = cursor.fetchone()

                        if existing:
                            # Update existing anime
                            anime_id = existing["id"]
                            cursor.execute(
                                """
                                UPDATE anime SET
                                    title = ?, status = ?, episodes_watched = ?,
                                    total_episodes = ?, score = ?, mal_id = ?,
                                    sync_status = ?, last_mal_sync = ?
                                WHERE id = ?
                            """,
                                (
                                    anime_data["title"],
                                    anime_data["status"],
                                    anime_data["episodes_watched"],
                                    anime_data["total_episodes"],
                                    anime_data["score"],
                                    mal_id,
                                    SyncStatus.SYNCED.value,
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    anime_id,
                                ),
                            )
                            updated += 1
                        else:
                            # Create new anime
                            cursor.execute(
                                """
                                INSERT INTO anime (
                                    mal_id, title, status, episodes_watched,
                                    total_episodes, score, sync_status, last_mal_sync,
                                    date_added, date_updated
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    mal_id,
                                    anime_data["title"],
                                    anime_data["status"],
                                    anime_data["episodes_watched"],
                                    anime_data["total_episodes"],
                                    anime_data["score"],
                                    SyncStatus.SYNCED.value,
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ),
                            )
                            added += 1

                    logger.info(
                        f"Synced MAL ID {mal_id}: {anime_data['title']} ({anime_data['status']})"
                    )

                except Exception as e:
                    errors.append(f"Failed to sync anime {mal_id}: {e!s}")

            return added, updated, errors

        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            return 0, 0, [f"Full sync failed: {e!s}"]

    def enable_sync(self):
        """Enable synchronization"""
        if self.is_authenticated:
            self.sync_enabled = True
            logger.info("Sync enabled")
        else:
            logger.warning("Cannot enable sync without authentication")

    def disable_sync(self):
        """Disable synchronization"""
        self.sync_enabled = False
        logger.info("Sync disabled")
