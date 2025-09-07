"""Tests for anime repository"""

import unittest
import tempfile
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.database import Database
from models.anime import Anime
from models.anime_repository import AnimeRepository


class TestAnimeRepository(unittest.TestCase):
    """Test anime repository functionality"""
    
    def setUp(self):
        """Set up test database and repository"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()
        
        # Initialize database and repository
        self.db = Database(self.db_path)
        self.db.initialize()
        self.repo = AnimeRepository(self.db)
        
        # Create test data
        self.test_anime = Anime(
            title="Test Anime",
            status="Watching",
            episodes_watched=5,
            total_episodes=12,
            score=8
        )
    
    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()
        if self.db_path.exists():
            os.unlink(self.db_path)
    
    def test_create_anime(self):
        """Test creating anime"""
        anime_id = self.repo.create(self.test_anime)
        self.assertIsNotNone(anime_id)
        self.assertGreater(anime_id, 0)
        
        # Verify creation
        anime = self.repo.get_by_id(anime_id)
        self.assertIsNotNone(anime)
        self.assertEqual(anime.title, "Test Anime")
        self.assertEqual(anime.status, "Watching")
        self.assertEqual(anime.episodes_watched, 5)
    
    def test_get_by_id(self):
        """Test getting anime by ID"""
        anime_id = self.repo.create(self.test_anime)
        
        anime = self.repo.get_by_id(anime_id)
        self.assertIsNotNone(anime)
        self.assertEqual(anime.title, "Test Anime")
        
        # Test non-existent ID
        anime = self.repo.get_by_id(999)
        self.assertIsNone(anime)
    
    def test_get_all(self):
        """Test getting all anime"""
        # Create multiple anime
        anime1 = Anime(title="Anime A", status="Watching")
        anime2 = Anime(title="Anime B", status="Completed")
        anime3 = Anime(title="Anime C", status="On Hold")
        
        self.repo.create(anime1)
        self.repo.create(anime2)
        self.repo.create(anime3)
        
        # Get all anime
        all_anime = self.repo.get_all()
        self.assertEqual(len(all_anime), 3)
        
        # Test ordering
        titles = [a.title for a in all_anime]
        self.assertEqual(titles, ["Anime A", "Anime B", "Anime C"])
        
        # Test descending order
        all_anime_desc = self.repo.get_all(ascending=False)
        titles_desc = [a.title for a in all_anime_desc]
        self.assertEqual(titles_desc, ["Anime C", "Anime B", "Anime A"])
    
    def test_get_by_status(self):
        """Test getting anime by status"""
        # Create anime with different statuses
        self.repo.create(Anime(title="Watching 1", status="Watching"))
        self.repo.create(Anime(title="Watching 2", status="Watching"))
        self.repo.create(Anime(title="Completed 1", status="Completed"))
        
        # Get by status
        watching = self.repo.get_by_status("Watching")
        self.assertEqual(len(watching), 2)
        
        completed = self.repo.get_by_status("Completed")
        self.assertEqual(len(completed), 1)
        
        on_hold = self.repo.get_by_status("On Hold")
        self.assertEqual(len(on_hold), 0)
    
    def test_search(self):
        """Test searching anime"""
        # Create anime with searchable content
        self.repo.create(Anime(title="Attack on Titan", notes="Great action"))
        self.repo.create(Anime(title="Death Note", notes="Psychological thriller"))
        self.repo.create(Anime(title="Titan Fall", notes="Mecha anime"))
        
        # Search by title
        results = self.repo.search("Titan")
        self.assertEqual(len(results), 2)
        
        # Search by notes
        results = self.repo.search("thriller")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Death Note")
        
        # Search with no results
        results = self.repo.search("Nonexistent")
        self.assertEqual(len(results), 0)
    
    def test_filter(self):
        """Test filtering anime"""
        # Create diverse anime
        self.repo.create(Anime(title="A1", status="Watching", score=8))
        self.repo.create(Anime(title="A2", status="Watching", score=6))
        self.repo.create(Anime(title="A3", status="Completed", score=9))
        self.repo.create(Anime(title="A4", status="Completed", score=7))
        
        # Filter by status
        results = self.repo.filter(status="Watching")
        self.assertEqual(len(results), 2)
        
        # Filter by score range
        results = self.repo.filter(min_score=7, max_score=8)
        self.assertEqual(len(results), 2)
        
        # Combined filters
        results = self.repo.filter(status="Completed", min_score=8)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "A3")
    
    def test_update(self):
        """Test updating anime"""
        anime_id = self.repo.create(self.test_anime)
        
        # Get and update
        anime = self.repo.get_by_id(anime_id)
        anime.status = "Completed"
        anime.episodes_watched = 12
        anime.score = 9
        
        success = self.repo.update(anime)
        self.assertTrue(success)
        
        # Verify update
        updated = self.repo.get_by_id(anime_id)
        self.assertEqual(updated.status, "Completed")
        self.assertEqual(updated.episodes_watched, 12)
        self.assertEqual(updated.score, 9)
    
    def test_update_episodes(self):
        """Test quick episode update"""
        anime_id = self.repo.create(self.test_anime)
        
        # Update episodes
        success = self.repo.update_episodes(anime_id, 10)
        self.assertTrue(success)
        
        anime = self.repo.get_by_id(anime_id)
        self.assertEqual(anime.episodes_watched, 10)
        
        # Update to completion
        success = self.repo.update_episodes(anime_id, 12)
        self.assertTrue(success)
        
        anime = self.repo.get_by_id(anime_id)
        self.assertEqual(anime.episodes_watched, 12)
        self.assertEqual(anime.status, "Completed")
    
    def test_increment_decrement_episodes(self):
        """Test incrementing and decrementing episodes"""
        anime_id = self.repo.create(self.test_anime)
        
        # Increment
        success = self.repo.increment_episode(anime_id)
        self.assertTrue(success)
        
        anime = self.repo.get_by_id(anime_id)
        self.assertEqual(anime.episodes_watched, 6)
        
        # Decrement
        success = self.repo.decrement_episode(anime_id)
        self.assertTrue(success)
        
        anime = self.repo.get_by_id(anime_id)
        self.assertEqual(anime.episodes_watched, 5)
    
    def test_delete(self):
        """Test deleting anime"""
        anime_id = self.repo.create(self.test_anime)
        
        # Delete
        success = self.repo.delete(anime_id)
        self.assertTrue(success)
        
        # Verify deletion
        anime = self.repo.get_by_id(anime_id)
        self.assertIsNone(anime)
        
        # Try deleting non-existent
        success = self.repo.delete(999)
        self.assertFalse(success)
    
    def test_bulk_operations(self):
        """Test bulk create and delete"""
        # Bulk create
        anime_list = [
            Anime(title="Bulk 1"),
            Anime(title="Bulk 2"),
            Anime(title="Bulk 3")
        ]
        
        ids = self.repo.bulk_create(anime_list)
        self.assertEqual(len(ids), 3)
        
        # Verify creation
        all_anime = self.repo.get_all()
        self.assertEqual(len(all_anime), 3)
        
        # Bulk delete
        deleted = self.repo.bulk_delete(ids[:2])
        self.assertEqual(deleted, 2)
        
        # Verify deletion
        all_anime = self.repo.get_all()
        self.assertEqual(len(all_anime), 1)
    
    def test_statistics(self):
        """Test getting statistics"""
        # Create test data
        self.repo.create(Anime(title="A1", status="Watching", score=8, episodes_watched=10))
        self.repo.create(Anime(title="A2", status="Watching", score=7, episodes_watched=5))
        self.repo.create(Anime(title="A3", status="Completed", score=9, episodes_watched=24))
        
        stats = self.repo.get_statistics()
        
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['by_status']['Watching'], 2)
        self.assertEqual(stats['by_status']['Completed'], 1)
        self.assertEqual(stats['average_score'], 8.0)
        self.assertEqual(stats['total_episodes_watched'], 39)
        self.assertIn('added_this_week', stats)
    
    def test_exists(self):
        """Test checking if anime exists"""
        self.repo.create(self.test_anime)
        
        # Check by title
        exists = self.repo.exists("Test Anime")
        self.assertTrue(exists)
        
        exists = self.repo.exists("Nonexistent")
        self.assertFalse(exists)
    
    def test_mal_id_operations(self):
        """Test MAL ID related operations"""
        # Create anime with MAL ID
        anime = Anime(title="MAL Test", mal_id=12345)
        self.repo.create(anime)
        
        # Get by MAL ID
        result = self.repo.get_by_mal_id(12345)
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "MAL Test")
        
        # Check exists by MAL ID
        exists = self.repo.exists_mal_id(12345)
        self.assertTrue(exists)
        
        exists = self.repo.exists_mal_id(99999)
        self.assertFalse(exists)


if __name__ == '__main__':
    unittest.main()