"""MyAnimeList API service using Jikan API"""

import hashlib
import json
import logging
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors"""


class RateLimitError(APIError):
    """Rate limit exceeded error"""


class NetworkError(APIError):
    """Network connection error"""


class CacheStrategy(Enum):
    """Cache duration strategies"""

    PERMANENT = -1  # Never expires
    SHORT = 3600  # 1 hour (search results)
    MEDIUM = 86400  # 1 day (user lists)
    LONG = 604800  # 7 days (anime details)


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API requests"""

    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter

        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.rate = requests_per_minute / 60.0  # Requests per second
        self.max_tokens = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.last_update = time.time()
        self.lock = Lock()

    def wait_if_needed(self) -> float:
        """Wait if rate limit would be exceeded

        Returns:
            float: Seconds waited
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Add tokens based on time elapsed
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)

            # If we don't have tokens, wait
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                logger.debug(f"Rate limit: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self.tokens = 0
                return wait_time
            self.tokens -= 1
            return 0


class ResponseCache:
    """SQLite-based response cache for API calls"""

    def __init__(self, cache_dir: Path):
        """Initialize cache

        Args:
            cache_dir: Directory for cache database
        """
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "mal_cache.db"
        self._init_db()

    def _init_db(self):
        """Initialize cache database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """
            )
            # Clean expired entries
            conn.execute(
                "DELETE FROM cache WHERE expires_at > 0 AND expires_at < ?", (time.time(),)
            )
            conn.commit()

    def get(self, key: str) -> Optional[Dict]:
        """Get cached response

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data, expires_at FROM cache WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row:
                data, expires_at = row
                if expires_at < 0 or expires_at > time.time():
                    return json.loads(data)
                # Expired, delete it
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()

        return None

    def set(self, key: str, data: Dict, strategy: CacheStrategy):
        """Cache response data

        Args:
            key: Cache key
            data: Data to cache
            strategy: Cache duration strategy
        """
        now = time.time()
        if strategy == CacheStrategy.PERMANENT:
            expires_at = -1
        else:
            expires_at = now + strategy.value

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, data, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (key, json.dumps(data), expires_at, now),
            )
            conn.commit()

    def clear(self):
        """Clear all cached data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()


class MALService:
    """Service for interacting with MyAnimeList via Jikan API"""

    BASE_URL = "https://api.jikan.moe/v4"

    def __init__(self, cache_dir: Path):
        """Initialize MAL service

        Args:
            cache_dir: Directory for caching
        """
        self.rate_limiter = RateLimiter(requests_per_minute=60)
        self.cache = ResponseCache(cache_dir)
        self.session_start = time.time()
        self.request_count = 0
        self.last_error = None

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        cache_strategy: Optional[CacheStrategy] = None,
    ) -> Dict:
        """Make API request with rate limiting, caching, and retry logic

        Args:
            endpoint: API endpoint (e.g., "/anime/1")
            params: Query parameters
            cache_strategy: Caching strategy to use

        Returns:
            API response as dictionary

        Raises:
            APIError: On API errors
            NetworkError: On network errors
            RateLimitError: On rate limit errors
        """
        # Build URL
        url = f"{self.BASE_URL}{endpoint}"
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        # Check cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_strategy:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for: {endpoint}")
                return cached

        # Rate limiting
        wait_time = self.rate_limiter.wait_if_needed()

        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                # Make request
                logger.debug(f"API request: {url}")
                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "AnimeTracker/0.2.0 (https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker)"
                    },
                )

                with urllib.request.urlopen(request, timeout=10) as response:
                    self.request_count += 1

                    # Check status
                    if response.status == 200:
                        data = json.loads(response.read().decode("utf-8"))

                        # Cache successful response
                        if cache_strategy:
                            self.cache.set(cache_key, data, cache_strategy)

                        return data
                    if response.status == 429:
                        # Rate limited
                        logger.warning("Rate limit hit, waiting...")
                        time.sleep(60)  # Wait a full minute
                        raise RateLimitError("Rate limit exceeded")
                    raise APIError(f"API returned status {response.status}")

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    logger.warning("Rate limit hit, waiting 60 seconds...")
                    time.sleep(60)
                    continue
                if e.code == 404:
                    raise APIError(f"Not found: {endpoint}")
                if e.code >= 500:
                    # Server error, retry with backoff
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Server error {e.code}, retrying in {retry_delay} seconds..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    raise APIError(f"Server error: {e.code}")
                raise APIError(f"HTTP error: {e.code}")

            except urllib.error.URLError as e:
                # Network error
                if attempt < max_retries - 1:
                    logger.warning(f"Network error, retrying in {retry_delay} seconds: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                self.last_error = str(e)
                raise NetworkError(f"Network error: {e}")

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise APIError(f"Unexpected error: {e}")

        raise APIError(f"Failed after {max_retries} attempts")

    def search_anime(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for anime

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of anime search results
        """
        try:
            response = self._make_request(
                "/anime",
                params={"q": query, "limit": limit, "sfw": "true"},
                cache_strategy=CacheStrategy.SHORT,
            )
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_anime_details(self, mal_id: int) -> Optional[Dict]:
        """Get detailed anime information

        Args:
            mal_id: MyAnimeList anime ID

        Returns:
            Anime details or None if not found
        """
        try:
            response = self._make_request(f"/anime/{mal_id}", cache_strategy=CacheStrategy.LONG)
            return response.get("data")
        except APIError as e:
            if "Not found" in str(e):
                logger.info(f"Anime {mal_id} not found on MAL")
                return None
            logger.error(f"Failed to get anime {mal_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get anime {mal_id}: {e}")
            return None

    def get_anime_full(self, mal_id: int) -> Optional[Dict]:
        """Get full anime information including characters, staff, etc.

        Args:
            mal_id: MyAnimeList anime ID

        Returns:
            Full anime details or None if not found
        """
        try:
            response = self._make_request(
                f"/anime/{mal_id}/full", cache_strategy=CacheStrategy.LONG
            )
            return response.get("data")
        except Exception as e:
            logger.error(f"Failed to get full anime {mal_id}: {e}")
            return None

    def get_user_animelist(self, username: str, status: Optional[str] = None) -> List[Dict]:
        """Get user's anime list (public lists only)

        Args:
            username: MAL username
            status: Filter by status (watching, completed, etc.)

        Returns:
            List of user's anime
        """
        try:
            params = {}
            if status:
                params["status"] = status

            all_anime = []
            page = 1

            while True:
                params["page"] = page
                response = self._make_request(
                    f"/users/{username}/animelist",
                    params=params,
                    cache_strategy=CacheStrategy.MEDIUM,
                )

                data = response.get("data", [])
                if not data:
                    break

                all_anime.extend(data)

                # Check if there are more pages
                pagination = response.get("pagination", {})
                if not pagination.get("has_next_page", False):
                    break

                page += 1
                # Add delay to avoid rate limit
                time.sleep(1)

            return all_anime

        except Exception as e:
            logger.error(f"Failed to get user list for {username}: {e}")
            return []

    def get_seasonal_anime(
        self, year: Optional[int] = None, season: Optional[str] = None
    ) -> List[Dict]:
        """Get seasonal anime

        Args:
            year: Year (None for current)
            season: Season (winter, spring, summer, fall)

        Returns:
            List of seasonal anime
        """
        try:
            if year and season:
                endpoint = f"/seasons/{year}/{season}"
            else:
                endpoint = "/seasons/now"

            response = self._make_request(endpoint, cache_strategy=CacheStrategy.MEDIUM)
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get seasonal anime: {e}")
            return []

    def get_top_anime(self, limit: int = 25) -> List[Dict]:
        """Get top rated anime

        Args:
            limit: Number of anime to return

        Returns:
            List of top anime
        """
        try:
            response = self._make_request(
                "/top/anime", params={"limit": limit}, cache_strategy=CacheStrategy.MEDIUM
            )
            return response.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get top anime: {e}")
            return []

    def download_image(self, image_url: str, save_path: Path) -> bool:
        """Download and save anime cover image

        Args:
            image_url: URL of the image
            save_path: Path to save the image

        Returns:
            True if successful, False otherwise
        """
        try:
            # No rate limiting for image downloads (different server)
            request = urllib.request.Request(
                image_url, headers={"User-Agent": "AnimeTracker/0.2.0"}
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(response.read())
                    return True
            return False

        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get service statistics

        Returns:
            Dictionary with service stats
        """
        uptime = time.time() - self.session_start
        return {
            "requests_made": self.request_count,
            "uptime_seconds": uptime,
            "rate_limit": "60/min",
            "last_error": self.last_error,
            "cache_size": self._get_cache_size(),
        }

    def _get_cache_size(self) -> int:
        """Get number of cached entries"""
        try:
            with sqlite3.connect(self.cache.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                return cursor.fetchone()[0]
        except:
            return 0

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("MAL cache cleared")
