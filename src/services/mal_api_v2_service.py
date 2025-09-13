"""MAL API v2 service for authenticated read/write operations"""

import logging
from datetime import date
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MALStatus(Enum):
    """MAL anime status values"""

    WATCHING = "watching"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    PLAN_TO_WATCH = "plan_to_watch"


class MALAPIv2Service:
    """Service for MAL API v2 operations using OAuth2"""

    def __init__(self, oauth_client):
        """Initialize MAL API v2 service

        Args:
            oauth_client: MAL OAuth2 client instance
        """
        self.oauth_client = oauth_client

    # ========== READ OPERATIONS ==========

    def get_user_info(self) -> Optional[Dict]:
        """Get authenticated user information

        Returns:
            User data or None
        """
        return self.oauth_client.make_api_request("/users/@me")

    def get_user_animelist(
        self, status: Optional[MALStatus] = None, limit: int = 100, offset: int = 0
    ) -> Optional[Dict]:
        """Get user's anime list

        Args:
            status: Filter by status
            limit: Number of items to retrieve
            offset: Pagination offset

        Returns:
            Anime list data or None
        """
        endpoint = "/users/@me/animelist"
        # Request both list_status and anime details including num_episodes
        params = f"?fields=list_status,num_episodes&limit={limit}&offset={offset}"

        if status:
            params += f"&status={status.value}"

        return self.oauth_client.make_api_request(endpoint + params)

    def get_anime_details(self, anime_id: int) -> Optional[Dict]:
        """Get detailed anime information

        Args:
            anime_id: MAL anime ID

        Returns:
            Anime details or None
        """
        fields = (
            "id,title,main_picture,alternative_titles,start_date,end_date,"
            "synopsis,mean,rank,popularity,num_list_users,num_scoring_users,"
            "nsfw,genres,created_at,updated_at,media_type,status,my_list_status,"
            "num_episodes,start_season,broadcast,source,average_episode_duration,"
            "rating,studios"
        )

        endpoint = f"/anime/{anime_id}?fields={fields}"
        return self.oauth_client.make_api_request(endpoint)

    def search_anime(self, query: str, limit: int = 20) -> Optional[List[Dict]]:
        """Search for anime

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Search results or None
        """
        endpoint = f"/anime?q={query}&limit={limit}"
        result = self.oauth_client.make_api_request(endpoint)

        if result and "data" in result:
            return result["data"]
        return None

    # ========== WRITE OPERATIONS ==========

    def update_anime_status(self, anime_id: int, status: MALStatus) -> bool:
        """Update anime watching status

        Args:
            anime_id: MAL anime ID
            status: New status

        Returns:
            True if successful
        """
        endpoint = f"/anime/{anime_id}/my_list_status"
        data = {"status": status.value}

        result = self.oauth_client.make_api_request(endpoint, "PATCH", data)
        return result is not None

    def update_anime_progress(self, anime_id: int, episodes_watched: int) -> bool:
        """Update episode progress

        Args:
            anime_id: MAL anime ID
            episodes_watched: Number of episodes watched

        Returns:
            True if successful
        """
        endpoint = f"/anime/{anime_id}/my_list_status"
        data = {"num_watched_episodes": episodes_watched}

        result = self.oauth_client.make_api_request(endpoint, "PATCH", data)
        return result is not None

    def update_anime_score(self, anime_id: int, score: int) -> bool:
        """Update anime score

        Args:
            anime_id: MAL anime ID
            score: Score (1-10)

        Returns:
            True if successful
        """
        if score < 0 or score > 10:
            logger.error(f"Invalid score: {score}")
            return False

        endpoint = f"/anime/{anime_id}/my_list_status"
        data = {"score": score}

        result = self.oauth_client.make_api_request(endpoint, "PATCH", data)
        return result is not None

    def update_anime_list_status(
        self,
        anime_id: int,
        status: Optional[MALStatus] = None,
        score: Optional[int] = None,
        num_watched_episodes: Optional[int] = None,
        is_rewatching: Optional[bool] = None,
        num_times_rewatched: Optional[int] = None,
        rewatch_value: Optional[int] = None,
        priority: Optional[int] = None,
        tags: Optional[List[str]] = None,
        comments: Optional[str] = None,
        start_date: Optional[date] = None,
        finish_date: Optional[date] = None,
    ) -> bool:
        """Update multiple anime list fields at once

        Args:
            anime_id: MAL anime ID
            status: Watching status
            score: Score (0-10, 0 = no score)
            num_watched_episodes: Episodes watched
            is_rewatching: Currently rewatching
            num_times_rewatched: Number of rewatches
            rewatch_value: Rewatch value (1-5)
            priority: Priority (0-2: Low, Medium, High)
            tags: List of tags
            comments: Personal comments
            start_date: Start watching date
            finish_date: Finish watching date

        Returns:
            True if successful
        """
        endpoint = f"/anime/{anime_id}/my_list_status"
        data = {}

        if status is not None:
            data["status"] = status.value

        if score is not None:
            if 0 <= score <= 10:
                data["score"] = score
            else:
                logger.warning(f"Invalid score {score}, skipping")

        if num_watched_episodes is not None:
            data["num_watched_episodes"] = num_watched_episodes

        if is_rewatching is not None:
            data["is_rewatching"] = "true" if is_rewatching else "false"

        if num_times_rewatched is not None:
            data["num_times_rewatched"] = num_times_rewatched

        if rewatch_value is not None:
            if 1 <= rewatch_value <= 5:
                data["rewatch_value"] = rewatch_value

        if priority is not None:
            if 0 <= priority <= 2:
                data["priority"] = priority

        if tags is not None:
            data["tags"] = ",".join(tags)

        if comments is not None:
            data["comments"] = comments[:1000]  # Limit to 1000 chars

        if start_date is not None:
            data["start_date"] = start_date.isoformat()

        if finish_date is not None:
            data["finish_date"] = finish_date.isoformat()

        if not data:
            logger.warning("No data to update")
            return False

        result = self.oauth_client.make_api_request(endpoint, "PATCH", data)
        return result is not None

    def add_anime_to_list(self, anime_id: int, status: MALStatus = MALStatus.PLAN_TO_WATCH) -> bool:
        """Add anime to user's list

        Args:
            anime_id: MAL anime ID
            status: Initial status

        Returns:
            True if successful
        """
        return self.update_anime_status(anime_id, status)

    def remove_anime_from_list(self, anime_id: int) -> bool:
        """Remove anime from user's list

        Args:
            anime_id: MAL anime ID

        Returns:
            True if successful
        """
        endpoint = f"/anime/{anime_id}/my_list_status"

        # DELETE request
        result = self.oauth_client.make_api_request(endpoint, "DELETE")
        return result is not None

    # ========== SYNC OPERATIONS ==========

    def get_anime_list_status(self, anime_id: int) -> Optional[Dict]:
        """Get user's list status for specific anime

        Args:
            anime_id: MAL anime ID

        Returns:
            List status data or None
        """
        details = self.get_anime_details(anime_id)
        if details and "my_list_status" in details:
            return details["my_list_status"]
        return None

    def sync_anime_from_local(self, anime_data: Dict) -> bool:
        """Sync local anime data to MAL

        Args:
            anime_data: Local anime data with mal_id

        Returns:
            True if successful
        """
        mal_id = anime_data.get("mal_id")
        if not mal_id:
            logger.error("No MAL ID for sync")
            return False

        # Map local status to MAL status
        status_map = {
            "Watching": MALStatus.WATCHING,
            "Completed": MALStatus.COMPLETED,
            "On Hold": MALStatus.ON_HOLD,
            "Dropped": MALStatus.DROPPED,
            "Plan to Watch": MALStatus.PLAN_TO_WATCH,
        }

        local_status = anime_data.get("status")
        mal_status = status_map.get(local_status)

        if not mal_status:
            logger.error(f"Unknown status: {local_status}")
            return False

        # Prepare update data
        return self.update_anime_list_status(
            anime_id=mal_id,
            status=mal_status,
            score=anime_data.get("score"),
            num_watched_episodes=anime_data.get("episodes_watched"),
            comments=anime_data.get("notes"),
        )

    def sync_anime_to_local(self, mal_id: int) -> Optional[Dict]:
        """Get MAL anime data for local sync

        Args:
            mal_id: MAL anime ID

        Returns:
            Anime data formatted for local storage
        """
        details = self.get_anime_details(mal_id)
        if not details:
            return None

        # Map MAL status to local status
        status_map = {
            "watching": "Watching",
            "completed": "Completed",
            "on_hold": "On Hold",
            "dropped": "Dropped",
            "plan_to_watch": "Plan to Watch",
        }

        my_status = details.get("my_list_status", {})
        mal_status = my_status.get("status")
        local_status = status_map.get(mal_status, "Plan to Watch")

        # Extract genres
        genres = [g["name"] for g in details.get("genres", [])]

        # Extract studio
        studios = details.get("studios", [])
        studio = studios[0]["name"] if studios else None

        # Extract image URL
        image_url = None
        if "main_picture" in details:
            image_url = details["main_picture"].get("large") or details["main_picture"].get(
                "medium"
            )

        return {
            "mal_id": details["id"],
            "title": details["title"],
            "title_english": details.get("alternative_titles", {}).get("en"),
            "title_japanese": details.get("alternative_titles", {}).get("ja"),
            "status": local_status,
            "episodes_watched": my_status.get("num_episodes_watched", 0),
            "total_episodes": details.get("num_episodes"),
            "score": my_status.get("score"),
            "synopsis": details.get("synopsis"),
            "genres": genres,
            "studio": studio,
            "image_url": image_url,
            "notes": my_status.get("comments"),
            "mal_updated_at": my_status.get("updated_at"),
        }

    def batch_sync_to_mal(self, anime_list: List[Dict]) -> Dict[str, int]:
        """Batch sync multiple anime to MAL

        Args:
            anime_list: List of local anime data

        Returns:
            Dict with success and failure counts
        """
        success = 0
        failed = 0

        for anime in anime_list:
            if self.sync_anime_from_local(anime):
                success += 1
                logger.info(f"Synced {anime.get('title')} to MAL")
            else:
                failed += 1
                logger.error(f"Failed to sync {anime.get('title')} to MAL")

        return {"success": success, "failed": failed}

    def get_full_animelist(self) -> List[Dict]:
        """Get complete anime list from MAL

        Returns:
            List of all anime in user's list
        """
        all_anime = []
        offset = 0
        limit = 100

        while True:
            result = self.get_user_animelist(limit=limit, offset=offset)
            if not result or "data" not in result:
                break

            anime_list = result["data"]
            if not anime_list:
                break

            all_anime.extend(anime_list)

            # Check if there are more pages
            if "paging" in result and "next" in result["paging"]:
                offset += limit
            else:
                break

        return all_anime
