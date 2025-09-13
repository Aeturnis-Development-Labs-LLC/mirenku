"""Repository for anime database operations"""

import logging
from typing import Any, Dict, List, Optional

from models.anime import Anime
from models.database import Database

logger = logging.getLogger(__name__)


class AnimeRepository:
    """Repository for anime CRUD operations"""

    def __init__(self, database: Database):
        """Initialize repository

        Args:
            database: Database instance
        """
        self.db = database

    def create(self, anime: Anime) -> int:
        """Create new anime entry

        Args:
            anime: Anime instance to create

        Returns:
            int: ID of created anime
        """
        data = anime.to_dict()

        # Remove id if present
        data.pop("id", None)

        # Build insert query
        columns = list(data.keys())
        placeholders = ["?" for _ in columns]

        query = f"""
            INSERT INTO anime ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """

        with self.db.get_cursor() as cursor:
            cursor.execute(query, list(data.values()))
            anime_id = cursor.lastrowid
            logger.info(f"Created anime with ID: {anime_id}")
            return anime_id

    def get_by_id(self, anime_id: int) -> Optional[Anime]:
        """Get anime by ID

        Args:
            anime_id: Anime ID

        Returns:
            Optional[Anime]: Anime instance or None
        """
        query = "SELECT * FROM anime WHERE id = ?"

        row = self.db.fetchone(query, (anime_id,))
        if row:
            return Anime.from_db_row(row)
        return None

    def get_by_mal_id(self, mal_id: int) -> Optional[Anime]:
        """Get anime by MyAnimeList ID

        Args:
            mal_id: MyAnimeList ID

        Returns:
            Optional[Anime]: Anime instance or None
        """
        query = "SELECT * FROM anime WHERE mal_id = ?"

        row = self.db.fetchone(query, (mal_id,))
        if row:
            return Anime.from_db_row(row)
        return None

    def get_all(self, order_by: str = "title", ascending: bool = True) -> List[Anime]:
        """Get all anime

        Args:
            order_by: Column to order by
            ascending: Sort order

        Returns:
            List[Anime]: List of anime
        """
        valid_columns = [
            "title",
            "status",
            "score",
            "episodes_watched",
            "date_added",
            "date_updated",
        ]
        if order_by not in valid_columns:
            order_by = "title"

        direction = "ASC" if ascending else "DESC"
        query = f"SELECT * FROM anime ORDER BY {order_by} {direction}"

        rows = self.db.fetchall(query)
        return [Anime.from_db_row(row) for row in rows]

    def get_by_status(self, status: str) -> List[Anime]:
        """Get anime by status

        Args:
            status: Anime status

        Returns:
            List[Anime]: List of anime with given status
        """
        query = "SELECT * FROM anime WHERE status = ? ORDER BY title"

        rows = self.db.fetchall(query, (status,))
        return [Anime.from_db_row(row) for row in rows]

    def search(self, search_term: str) -> List[Anime]:
        """Search anime by title or notes

        Args:
            search_term: Search term

        Returns:
            List[Anime]: List of matching anime
        """
        query = """
            SELECT * FROM anime
            WHERE title LIKE ?
               OR title_english LIKE ?
               OR title_japanese LIKE ?
               OR notes LIKE ?
            ORDER BY title
        """

        search_pattern = f"%{search_term}%"
        params = (search_pattern, search_pattern, search_pattern, search_pattern)

        rows = self.db.fetchall(query, params)
        return [Anime.from_db_row(row) for row in rows]

    def filter(
        self,
        status: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        search_term: Optional[str] = None,
    ) -> List[Anime]:
        """Filter anime by multiple criteria

        Args:
            status: Filter by status
            min_score: Minimum score
            max_score: Maximum score
            search_term: Search in title/notes

        Returns:
            List[Anime]: Filtered anime list
        """
        conditions = []
        params = []

        if status and status != "All":
            conditions.append("status = ?")
            params.append(status)

        if min_score is not None:
            conditions.append("score >= ?")
            params.append(min_score)

        if max_score is not None:
            conditions.append("score <= ?")
            params.append(max_score)

        if search_term:
            conditions.append(
                """
                (title LIKE ? OR title_english LIKE ?
                 OR title_japanese LIKE ? OR notes LIKE ?)
            """
            )
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 4)

        query = "SELECT * FROM anime"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY title"

        rows = self.db.fetchall(query, tuple(params))
        return [Anime.from_db_row(row) for row in rows]

    def update(self, anime: Anime) -> bool:
        """Update anime entry

        Args:
            anime: Anime instance with updated data

        Returns:
            bool: True if successful
        """
        if not anime.id:
            raise ValueError("Cannot update anime without ID")

        data = anime.to_dict()
        anime_id = data.pop("id")

        # Remove timestamps that shouldn't be updated manually
        data.pop("created_at", None)
        data.pop("date_added", None)

        # Build update query
        set_clauses = [f"{col} = ?" for col in data.keys()]
        query = f"""
            UPDATE anime
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """

        params = list(data.values()) + [anime_id]

        with self.db.get_cursor() as cursor:
            cursor.execute(query, params)
            updated = cursor.rowcount > 0

            if updated:
                logger.info(f"Updated anime ID: {anime_id}")
            else:
                logger.warning(f"No anime found with ID: {anime_id}")

            return updated

    def update_episodes(self, anime_id: int, episodes: int) -> bool:
        """Quick update for episode count

        Args:
            anime_id: Anime ID
            episodes: New episode count

        Returns:
            bool: True if successful
        """
        anime = self.get_by_id(anime_id)
        if not anime:
            return False

        anime.episodes_watched = episodes

        # Auto-complete if reached total
        if anime.total_episodes and anime.episodes_watched >= anime.total_episodes:
            anime.episodes_watched = anime.total_episodes
            if anime.status == Anime.STATUS_WATCHING:
                anime.status = Anime.STATUS_COMPLETED

        return self.update(anime)

    def increment_episode(self, anime_id: int) -> bool:
        """Increment episode count

        Args:
            anime_id: Anime ID

        Returns:
            bool: True if successful
        """
        anime = self.get_by_id(anime_id)
        if not anime:
            return False

        if anime.increment_episode():
            return self.update(anime)
        return False

    def decrement_episode(self, anime_id: int) -> bool:
        """Decrement episode count

        Args:
            anime_id: Anime ID

        Returns:
            bool: True if successful
        """
        anime = self.get_by_id(anime_id)
        if not anime:
            return False

        if anime.decrement_episode():
            return self.update(anime)
        return False

    def delete(self, anime_id: int) -> bool:
        """Delete anime entry

        Args:
            anime_id: Anime ID

        Returns:
            bool: True if successful
        """
        query = "DELETE FROM anime WHERE id = ?"

        with self.db.get_cursor() as cursor:
            cursor.execute(query, (anime_id,))
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"Deleted anime ID: {anime_id}")
            else:
                logger.warning(f"No anime found with ID: {anime_id}")

            return deleted

    def bulk_create(self, anime_list: List[Anime]) -> List[int]:
        """Create multiple anime entries

        Args:
            anime_list: List of Anime instances

        Returns:
            List[int]: List of created IDs
        """
        created_ids = []

        for anime in anime_list:
            try:
                anime_id = self.create(anime)
                created_ids.append(anime_id)
            except Exception as e:
                logger.error(f"Failed to create anime '{anime.title}': {e}")

        return created_ids

    def bulk_delete(self, anime_ids: List[int]) -> int:
        """Delete multiple anime entries

        Args:
            anime_ids: List of anime IDs

        Returns:
            int: Number of deleted entries
        """
        if not anime_ids:
            return 0

        placeholders = ",".join(["?" for _ in anime_ids])
        query = f"DELETE FROM anime WHERE id IN ({placeholders})"

        with self.db.get_cursor() as cursor:
            cursor.execute(query, anime_ids)
            deleted_count = cursor.rowcount
            logger.info(f"Deleted {deleted_count} anime entries")
            return deleted_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get anime statistics

        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        stats = {}

        # Total count
        total_query = "SELECT COUNT(*) as count FROM anime"
        stats["total"] = self.db.fetchone(total_query)["count"]

        # Count by status
        status_query = """
            SELECT status, COUNT(*) as count
            FROM anime
            GROUP BY status
        """
        status_rows = self.db.fetchall(status_query)
        stats["by_status"] = {row["status"]: row["count"] for row in status_rows}

        # Average score
        score_query = """
            SELECT AVG(score) as avg_score
            FROM anime
            WHERE score IS NOT NULL
        """
        avg_score = self.db.fetchone(score_query)["avg_score"]
        stats["average_score"] = round(avg_score, 2) if avg_score else 0

        # Total episodes watched
        episodes_query = """
            SELECT SUM(episodes_watched) as total_episodes
            FROM anime
        """
        stats["total_episodes_watched"] = self.db.fetchone(episodes_query)["total_episodes"] or 0

        # Recent additions
        recent_query = """
            SELECT COUNT(*) as count
            FROM anime
            WHERE date_added >= date('now', '-7 days')
        """
        stats["added_this_week"] = self.db.fetchone(recent_query)["count"]

        return stats

    def exists(self, title: str) -> bool:
        """Check if anime with title exists

        Args:
            title: Anime title

        Returns:
            bool: True if exists
        """
        query = "SELECT COUNT(*) as count FROM anime WHERE title = ?"
        count = self.db.fetchone(query, (title,))["count"]
        return count > 0

    def exists_mal_id(self, mal_id: int) -> bool:
        """Check if anime with MAL ID exists

        Args:
            mal_id: MyAnimeList ID

        Returns:
            bool: True if exists
        """
        query = "SELECT COUNT(*) as count FROM anime WHERE mal_id = ?"
        count = self.db.fetchone(query, (mal_id,))["count"]
        return count > 0
