"""Tests for anime service"""

import unittest
import tempfile
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.database import Database
from models.anime import Anime
from services.anime_service import AnimeService


class TestAnimeService(unittest.TestCase):
    """Test anime service functionality"""
    
    def setUp(self):
        """Set up test database and service"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()
        
        # Initialize database and service
        self.db = Database(self.db_path)
        self.db.initialize()
        self.service = AnimeService(self.db)
    
    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()
        if self.db_path.exists():
            os.unlink(self.db_path)
    
    def test_add_anime(self):
        """Test adding anime through service"""
        success, message, anime_id = self.service.add_anime(
            title="Test Anime",
            status="Watching",
            episodes_watched=5,
            total_episodes=12,
            score=8
        )
        
        self.assertTrue(success)
        self.assertIn("Successfully added", message)
        self.assertIsNotNone(anime_id)
        
        # Verify anime was created
        anime = self.service.get_anime(anime_id)
        self.assertIsNotNone(anime)
        self.assertEqual(anime.title, "Test Anime")
    
    def test_add_duplicate_anime(self):
        """Test adding duplicate anime"""
        # Add first anime
        self.service.add_anime(title="Duplicate Test")
        
        # Try to add duplicate
        success, message, anime_id = self.service.add_anime(title="Duplicate Test")
        
        self.assertFalse(success)
        self.assertIn("already exists", message)
        self.assertIsNone(anime_id)
    
    def test_add_anime_validation(self):
        """Test anime validation on add"""
        # Invalid status
        success, message, _ = self.service.add_anime(
            title="Test",
            status="InvalidStatus"
        )
        self.assertFalse(success)
        self.assertIn("Invalid status", message)
        
        # Invalid score
        success, message, _ = self.service.add_anime(
            title="Test",
            score=11
        )
        self.assertFalse(success)
        self.assertIn("Score must be", message)
    
    def test_update_anime(self):
        """Test updating anime"""
        # Add anime
        _, _, anime_id = self.service.add_anime(
            title="Update Test",
            status="Watching",
            episodes_watched=5
        )
        
        # Update anime
        success, message = self.service.update_anime(
            anime_id,
            status="Completed",
            episodes_watched=12,
            score=9
        )
        
        self.assertTrue(success)
        self.assertIn("Successfully updated", message)
        
        # Verify update
        anime = self.service.get_anime(anime_id)
        self.assertEqual(anime.status, "Completed")
        self.assertEqual(anime.episodes_watched, 12)
        self.assertEqual(anime.score, 9)
    
    def test_delete_anime(self):
        """Test deleting anime"""
        # Add anime
        _, _, anime_id = self.service.add_anime(title="Delete Test")
        
        # Delete anime
        success, message = self.service.delete_anime(anime_id)
        
        self.assertTrue(success)
        self.assertIn("Successfully deleted", message)
        
        # Verify deletion
        anime = self.service.get_anime(anime_id)
        self.assertIsNone(anime)
    
    def test_search_anime(self):
        """Test searching anime"""
        # Add test anime
        self.service.add_anime(title="Attack on Titan")
        self.service.add_anime(title="Death Note")
        self.service.add_anime(title="Titan Fall")
        
        # Search
        results = self.service.search_anime("Titan")
        self.assertEqual(len(results), 2)
        
        # Empty search
        results = self.service.search_anime("")
        self.assertEqual(len(results), 0)
        
        # Short search
        results = self.service.search_anime("a")
        self.assertEqual(len(results), 0)
    
    def test_filter_anime(self):
        """Test filtering anime"""
        # Add diverse anime
        self.service.add_anime(title="A1", status="Watching", score=8)
        self.service.add_anime(title="A2", status="Watching", score=6)
        self.service.add_anime(title="A3", status="Completed", score=9)
        
        # Filter by status
        results = self.service.filter_anime(status="Watching")
        self.assertEqual(len(results), 2)
        
        # Filter by score range
        results = self.service.filter_anime(min_score=7, max_score=8)
        self.assertEqual(len(results), 1)
    
    def test_quick_add(self):
        """Test quick add functionality"""
        success, message, anime_id = self.service.quick_add("Quick Test")
        
        self.assertTrue(success)
        self.assertIsNotNone(anime_id)
        
        anime = self.service.get_anime(anime_id)
        self.assertEqual(anime.status, "Plan to Watch")
        self.assertEqual(anime.episodes_watched, 0)
    
    def test_mark_completed(self):
        """Test marking anime as completed"""
        # Add anime with total episodes
        _, _, anime_id = self.service.add_anime(
            title="Complete Test",
            status="Watching",
            episodes_watched=5,
            total_episodes=12
        )
        
        # Mark as completed
        success, message = self.service.mark_completed(anime_id)
        
        self.assertTrue(success)
        
        anime = self.service.get_anime(anime_id)
        self.assertEqual(anime.status, "Completed")
        self.assertEqual(anime.episodes_watched, 12)
    
    def test_update_progress(self):
        """Test updating episode progress"""
        # Add anime
        _, _, anime_id = self.service.add_anime(
            title="Progress Test",
            status="Watching",
            episodes_watched=5,
            total_episodes=12
        )
        
        # Update progress
        success, message = self.service.update_progress(anime_id, 10)
        
        self.assertTrue(success)
        self.assertIn("Updated progress", message)
        
        # Update to completion
        success, message = self.service.update_progress(anime_id, 12)
        
        self.assertTrue(success)
        self.assertIn("Completed", message)
        
        anime = self.service.get_anime(anime_id)
        self.assertEqual(anime.status, "Completed")
    
    def test_increment_decrement_episode(self):
        """Test incrementing and decrementing episodes"""
        # Add anime
        _, _, anime_id = self.service.add_anime(
            title="Inc/Dec Test",
            status="Watching",
            episodes_watched=5,
            total_episodes=10
        )
        
        # Increment
        success, message = self.service.increment_episode(anime_id)
        self.assertTrue(success)
        self.assertIn("6/10", message)
        
        # Decrement
        success, message = self.service.decrement_episode(anime_id)
        self.assertTrue(success)
        self.assertIn("5/10", message)
        
        # Increment to completion
        for _ in range(5):
            self.service.increment_episode(anime_id)
        
        anime = self.service.get_anime(anime_id)
        self.assertEqual(anime.status, "Completed")
    
    def test_get_statistics(self):
        """Test getting statistics"""
        # Add test data
        self.service.add_anime(title="A1", status="Watching", score=8, episodes_watched=10)
        self.service.add_anime(title="A2", status="Watching", score=7, episodes_watched=5)
        self.service.add_anime(title="A3", status="Completed", score=9, episodes_watched=24)
        
        stats = self.service.get_statistics()
        
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['currently_watching'], 2)
        self.assertAlmostEqual(stats['completion_rate'], 33.3, places=1)
        self.assertEqual(stats['total_episodes_watched'], 39)
        self.assertGreater(stats['total_watch_time_hours'], 0)
    
    def test_get_watching_anime(self):
        """Test getting currently watching anime"""
        # Add anime
        self.service.add_anime(title="W1", status="Watching")
        self.service.add_anime(title="W2", status="Watching")
        self.service.add_anime(title="C1", status="Completed")
        
        watching = self.service.get_watching_anime()
        self.assertEqual(len(watching), 2)
        self.assertTrue(all(a.status == "Watching" for a in watching))
    
    def test_bulk_update_status(self):
        """Test bulk status update"""
        # Add anime
        ids = []
        for i in range(3):
            _, _, anime_id = self.service.add_anime(
                title=f"Bulk {i}",
                status="Watching"
            )
            ids.append(anime_id)
        
        # Bulk update
        success, message = self.service.bulk_update_status(ids, "On Hold")
        
        self.assertTrue(success)
        self.assertIn("3 anime", message)
        
        # Verify updates
        for anime_id in ids:
            anime = self.service.get_anime(anime_id)
            self.assertEqual(anime.status, "On Hold")
    
    def test_import_anime_list(self):
        """Test importing anime list"""
        import_data = [
            {"title": "Import 1", "status": "Watching", "score": 8},
            {"title": "Import 2", "status": "Completed", "score": 9},
            {"title": "Import 3"}  # Minimal data
        ]
        
        imported, failed, errors = self.service.import_anime_list(import_data)
        
        self.assertEqual(imported, 3)
        self.assertEqual(failed, 0)
        self.assertEqual(len(errors), 0)
        
        # Try importing duplicates
        imported, failed, errors = self.service.import_anime_list(import_data)
        
        self.assertEqual(imported, 0)
        self.assertEqual(failed, 3)
        self.assertEqual(len(errors), 3)
    
    def test_export_anime_list(self):
        """Test exporting anime list"""
        # Add anime
        self.service.add_anime(title="Export 1", score=8)
        self.service.add_anime(title="Export 2", score=9)
        
        export_data = self.service.export_anime_list()
        
        self.assertEqual(len(export_data), 2)
        self.assertTrue(all(isinstance(d, dict) for d in export_data))
        self.assertTrue(all('title' in d for d in export_data))
    
    def test_validate_import_data(self):
        """Test import data validation"""
        # Valid data
        errors = self.service.validate_import_data({
            "title": "Test",
            "status": "Watching",
            "score": 8
        })
        self.assertEqual(len(errors), 0)
        
        # Missing title
        errors = self.service.validate_import_data({
            "status": "Watching"
        })
        self.assertIn("Title is required", errors)
        
        # Invalid status
        errors = self.service.validate_import_data({
            "title": "Test",
            "status": "Invalid"
        })
        self.assertTrue(any("Invalid status" in e for e in errors))
        
        # Invalid score
        errors = self.service.validate_import_data({
            "title": "Test",
            "score": 11
        })
        self.assertTrue(any("Score must be" in e for e in errors))
    
    def test_caching(self):
        """Test caching functionality"""
        # Add anime
        self.service.add_anime(title="Cache Test")
        
        # First call - no cache
        anime_list1 = self.service.get_all_anime()
        
        # Second call - should use cache
        anime_list2 = self.service.get_all_anime()
        
        self.assertEqual(len(anime_list1), len(anime_list2))
        
        # Add another anime - should invalidate cache
        self.service.add_anime(title="Cache Test 2")
        
        # Should get fresh data
        anime_list3 = self.service.get_all_anime()
        self.assertEqual(len(anime_list3), len(anime_list1) + 1)


if __name__ == '__main__':
    unittest.main()