"""Business logic service for anime operations"""

from typing import List, Optional, Dict, Any, Tuple
from models.anime import Anime
from models.anime_repository import AnimeRepository
from models.database import Database
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class AnimeService:
    """Service layer for anime business logic"""
    
    def __init__(self, database: Database):
        """Initialize service
        
        Args:
            database: Database instance
        """
        self.db = database
        self.repository = AnimeRepository(database)
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
        
    def add_anime(self, title: str, status: str = "Plan to Watch", 
                  episodes_watched: int = 0, total_episodes: Optional[int] = None,
                  score: Optional[int] = None, notes: Optional[str] = None,
                  **kwargs) -> Tuple[bool, str, Optional[int]]:
        """Add new anime with validation
        
        Args:
            title: Anime title
            status: Watch status
            episodes_watched: Episodes watched
            total_episodes: Total episode count
            score: Rating score
            notes: Personal notes
            **kwargs: Additional anime fields
            
        Returns:
            Tuple of (success, message, anime_id)
        """
        try:
            # Check for duplicates
            if self.repository.exists(title):
                return False, f"Anime '{title}' already exists", None
            
            # Create anime instance
            anime = Anime(
                title=title,
                status=status,
                episodes_watched=episodes_watched,
                total_episodes=total_episodes,
                score=score,
                notes=notes,
                **kwargs
            )
            
            # Validate
            errors = anime.validate()
            if errors:
                return False, "; ".join(errors), None
            
            # Save to database
            anime_id = self.repository.create(anime)
            self._invalidate_cache()
            
            logger.info(f"Added anime: {title} (ID: {anime_id})")
            return True, f"Successfully added '{title}'", anime_id
            
        except Exception as e:
            logger.error(f"Failed to add anime: {e}")
            return False, f"Failed to add anime: {str(e)}", None
    
    def update_anime(self, anime_id: int, **updates) -> Tuple[bool, str]:
        """Update anime with validation
        
        Args:
            anime_id: Anime ID
            **updates: Fields to update
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get existing anime
            anime = self.repository.get_by_id(anime_id)
            if not anime:
                return False, f"Anime with ID {anime_id} not found"
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(anime, field):
                    setattr(anime, field, value)
            
            # Validate
            errors = anime.validate()
            if errors:
                return False, "; ".join(errors)
            
            # Save to database
            success = self.repository.update(anime)
            if success:
                self._invalidate_cache()
                logger.info(f"Updated anime ID {anime_id}")
                return True, "Successfully updated anime"
            else:
                return False, "Failed to update anime"
                
        except Exception as e:
            logger.error(f"Failed to update anime: {e}")
            return False, f"Failed to update anime: {str(e)}"
    
    def delete_anime(self, anime_id: int) -> Tuple[bool, str]:
        """Delete anime
        
        Args:
            anime_id: Anime ID
            
        Returns:
            Tuple of (success, message)
        """
        try:
            anime = self.repository.get_by_id(anime_id)
            if not anime:
                return False, f"Anime with ID {anime_id} not found"
            
            title = anime.title
            success = self.repository.delete(anime_id)
            
            if success:
                self._invalidate_cache()
                logger.info(f"Deleted anime: {title} (ID: {anime_id})")
                return True, f"Successfully deleted '{title}'"
            else:
                return False, "Failed to delete anime"
                
        except Exception as e:
            logger.error(f"Failed to delete anime: {e}")
            return False, f"Failed to delete anime: {str(e)}"
    
    def get_anime(self, anime_id: int) -> Optional[Anime]:
        """Get anime by ID
        
        Args:
            anime_id: Anime ID
            
        Returns:
            Anime instance or None
        """
        return self.repository.get_by_id(anime_id)
    
    def get_all_anime(self, use_cache: bool = True) -> List[Anime]:
        """Get all anime with optional caching
        
        Args:
            use_cache: Whether to use cache
            
        Returns:
            List of anime
        """
        cache_key = "all_anime"
        
        if use_cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]["data"]
        
        anime_list = self.repository.get_all()
        self._update_cache(cache_key, anime_list)
        return anime_list
    
    def search_anime(self, query: str) -> List[Anime]:
        """Search anime
        
        Args:
            query: Search query
            
        Returns:
            List of matching anime
        """
        if not query or len(query.strip()) < 2:
            return []
        
        return self.repository.search(query.strip())
    
    def filter_anime(self, status: Optional[str] = None,
                    min_score: Optional[int] = None,
                    max_score: Optional[int] = None,
                    search: Optional[str] = None) -> List[Anime]:
        """Filter anime by criteria
        
        Args:
            status: Filter by status
            min_score: Minimum score
            max_score: Maximum score
            search: Search term
            
        Returns:
            Filtered anime list
        """
        return self.repository.filter(
            status=status,
            min_score=min_score,
            max_score=max_score,
            search_term=search
        )
    
    def quick_add(self, title: str) -> Tuple[bool, str, Optional[int]]:
        """Quick add anime with minimal info
        
        Args:
            title: Anime title
            
        Returns:
            Tuple of (success, message, anime_id)
        """
        return self.add_anime(title, status="Plan to Watch")
    
    def mark_completed(self, anime_id: int) -> Tuple[bool, str]:
        """Mark anime as completed
        
        Args:
            anime_id: Anime ID
            
        Returns:
            Tuple of (success, message)
        """
        anime = self.repository.get_by_id(anime_id)
        if not anime:
            return False, "Anime not found"
        
        updates = {"status": Anime.STATUS_COMPLETED}
        if anime.total_episodes:
            updates["episodes_watched"] = anime.total_episodes
        
        return self.update_anime(anime_id, **updates)
    
    def update_progress(self, anime_id: int, episodes: int) -> Tuple[bool, str]:
        """Update episode progress
        
        Args:
            anime_id: Anime ID
            episodes: New episode count
            
        Returns:
            Tuple of (success, message)
        """
        anime = self.repository.get_by_id(anime_id)
        if not anime:
            return False, "Anime not found"
        
        if episodes < 0:
            return False, "Episodes cannot be negative"
        
        if anime.total_episodes and episodes > anime.total_episodes:
            episodes = anime.total_episodes
        
        success = self.repository.update_episodes(anime_id, episodes)
        
        if success:
            self._invalidate_cache()
            
            # Check if completed
            anime = self.repository.get_by_id(anime_id)
            if anime.status == Anime.STATUS_COMPLETED:
                return True, f"Completed '{anime.title}'!"
            else:
                return True, f"Updated progress: {anime.display_progress}"
        else:
            return False, "Failed to update progress"
    
    def increment_episode(self, anime_id: int) -> Tuple[bool, str]:
        """Increment episode count
        
        Args:
            anime_id: Anime ID
            
        Returns:
            Tuple of (success, message)
        """
        success = self.repository.increment_episode(anime_id)
        
        if success:
            self._invalidate_cache()
            anime = self.repository.get_by_id(anime_id)
            
            if anime.status == Anime.STATUS_COMPLETED:
                return True, f"Completed '{anime.title}'!"
            else:
                return True, f"Progress: {anime.display_progress}"
        else:
            return False, "Cannot increment further"
    
    def decrement_episode(self, anime_id: int) -> Tuple[bool, str]:
        """Decrement episode count
        
        Args:
            anime_id: Anime ID
            
        Returns:
            Tuple of (success, message)
        """
        success = self.repository.decrement_episode(anime_id)
        
        if success:
            self._invalidate_cache()
            anime = self.repository.get_by_id(anime_id)
            return True, f"Progress: {anime.display_progress}"
        else:
            return False, "Cannot decrement below 0"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get anime statistics with additional calculations
        
        Returns:
            Enhanced statistics dictionary
        """
        stats = self.repository.get_statistics()
        
        # Add completion percentage
        total = stats.get('total', 0)
        if total > 0:
            completed = stats.get('by_status', {}).get('Completed', 0)
            stats['completion_rate'] = round((completed / total) * 100, 1)
        else:
            stats['completion_rate'] = 0
        
        # Add watching count
        stats['currently_watching'] = stats.get('by_status', {}).get('Watching', 0)
        
        # Calculate estimated watch time (25 min per episode average)
        total_episodes = stats.get('total_episodes_watched', 0)
        stats['total_watch_time_hours'] = round(total_episodes * 25 / 60, 1)
        
        return stats
    
    def get_recent_anime(self, days: int = 7) -> List[Anime]:
        """Get recently added anime
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of recent anime
        """
        all_anime = self.repository.get_all(order_by='date_added', ascending=False)
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent = []
        for anime in all_anime:
            if anime.date_added and anime.date_added >= cutoff_date:
                recent.append(anime)
            else:
                break  # Since ordered by date, we can stop here
        
        return recent
    
    def get_watching_anime(self) -> List[Anime]:
        """Get anime currently being watched
        
        Returns:
            List of anime with 'Watching' status
        """
        return self.repository.get_by_status(Anime.STATUS_WATCHING)
    
    def bulk_update_status(self, anime_ids: List[int], status: str) -> Tuple[bool, str]:
        """Update status for multiple anime
        
        Args:
            anime_ids: List of anime IDs
            status: New status
            
        Returns:
            Tuple of (success, message)
        """
        if status not in Anime.STATUS_OPTIONS:
            return False, f"Invalid status: {status}"
        
        updated = 0
        failed = 0
        
        for anime_id in anime_ids:
            success, _ = self.update_anime(anime_id, status=status)
            if success:
                updated += 1
            else:
                failed += 1
        
        self._invalidate_cache()
        
        if failed == 0:
            return True, f"Successfully updated {updated} anime"
        elif updated == 0:
            return False, f"Failed to update all {failed} anime"
        else:
            return True, f"Updated {updated} anime, {failed} failed"
    
    def import_anime_list(self, anime_list: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """Import multiple anime from list
        
        Args:
            anime_list: List of anime dictionaries
            
        Returns:
            Tuple of (imported_count, failed_count, error_messages)
        """
        imported = 0
        failed = 0
        errors = []
        
        for anime_data in anime_list:
            try:
                title = anime_data.get('title')
                if not title:
                    failed += 1
                    errors.append("Missing title in import data")
                    continue
                
                # Check if already exists
                if self.repository.exists(title):
                    failed += 1
                    errors.append(f"'{title}' already exists")
                    continue
                
                # Create anime
                success, message, _ = self.add_anime(**anime_data)
                if success:
                    imported += 1
                else:
                    failed += 1
                    errors.append(f"{title}: {message}")
                    
            except Exception as e:
                failed += 1
                errors.append(f"Import error: {str(e)}")
        
        return imported, failed, errors
    
    def export_anime_list(self) -> List[Dict[str, Any]]:
        """Export all anime as dictionary list
        
        Returns:
            List of anime dictionaries
        """
        anime_list = self.repository.get_all()
        return [anime.to_dict() for anime in anime_list]
    
    def validate_import_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate import data
        
        Args:
            data: Import data dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not data.get('title'):
            errors.append("Title is required")
        
        status = data.get('status')
        if status and status not in Anime.STATUS_OPTIONS:
            errors.append(f"Invalid status: {status}")
        
        score = data.get('score')
        if score is not None:
            try:
                score = int(score)
                if score < 0 or score > 10:
                    errors.append("Score must be between 0 and 10")
            except (ValueError, TypeError):
                errors.append("Invalid score value")
        
        episodes = data.get('episodes_watched')
        if episodes is not None:
            try:
                episodes = int(episodes)
                if episodes < 0:
                    errors.append("Episodes cannot be negative")
            except (ValueError, TypeError):
                errors.append("Invalid episode count")
        
        return errors
    
    def _invalidate_cache(self):
        """Invalidate all cache entries"""
        self._cache.clear()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is valid
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if valid
        """
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        age = (datetime.now() - entry["timestamp"]).total_seconds()
        return age < self._cache_timeout
    
    def _update_cache(self, key: str, data: Any):
        """Update cache entry
        
        Args:
            key: Cache key
            data: Data to cache
        """
        self._cache[key] = {
            "data": data,
            "timestamp": datetime.now()
        }