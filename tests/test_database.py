"""Tests for database module"""

import unittest
import tempfile
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.database import Database
from models.anime import Anime


class TestDatabase(unittest.TestCase):
    """Test database functionality"""
    
    def setUp(self):
        """Set up test database"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()
        
        # Initialize database
        self.db = Database(self.db_path)
        self.db.initialize()
    
    def tearDown(self):
        """Clean up test database"""
        self.db.disconnect()
        if self.db_path.exists():
            os.unlink(self.db_path)
    
    def test_database_initialization(self):
        """Test database initialization"""
        # Check that tables were created
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row['name'] for row in cursor.fetchall()]
            
            expected_tables = ['anime', 'schema_version', 'settings', 
                             'sync_history', 'watch_history']
            for table in expected_tables:
                self.assertIn(table, tables)
    
    def test_schema_version(self):
        """Test schema version tracking"""
        version = self.db._get_schema_version()
        self.assertEqual(version, Database.SCHEMA_VERSION)
    
    def test_insert_anime(self):
        """Test inserting anime"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO anime (title, status, episodes_watched)
                VALUES (?, ?, ?)
            """, ("Test Anime", "Watching", 5))
            
            anime_id = cursor.lastrowid
            self.assertIsNotNone(anime_id)
            
            # Verify insertion
            cursor.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
            row = cursor.fetchone()
            self.assertEqual(row['title'], "Test Anime")
            self.assertEqual(row['status'], "Watching")
            self.assertEqual(row['episodes_watched'], 5)
    
    def test_anime_constraints(self):
        """Test database constraints"""
        with self.db.get_cursor() as cursor:
            # Test status constraint
            with self.assertRaises(Exception):
                cursor.execute("""
                    INSERT INTO anime (title, status)
                    VALUES (?, ?)
                """, ("Test", "InvalidStatus"))
            
            # Test score constraint
            with self.assertRaises(Exception):
                cursor.execute("""
                    INSERT INTO anime (title, score)
                    VALUES (?, ?)
                """, ("Test", 11))
            
            # Test negative episodes constraint
            with self.assertRaises(Exception):
                cursor.execute("""
                    INSERT INTO anime (title, episodes_watched)
                    VALUES (?, ?)
                """, ("Test", -1))
    
    def test_database_stats(self):
        """Test getting database statistics"""
        # Insert test data
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO anime (title, status) VALUES 
                ('Anime 1', 'Watching'),
                ('Anime 2', 'Completed'),
                ('Anime 3', 'Watching')
            """)
        
        stats = self.db.get_stats()
        self.assertEqual(stats['total_anime'], 3)
        self.assertEqual(stats['by_status']['Watching'], 2)
        self.assertEqual(stats['by_status']['Completed'], 1)
        self.assertIn('db_size', stats)


class TestAnimeModel(unittest.TestCase):
    """Test Anime model"""
    
    def test_anime_creation(self):
        """Test creating anime instance"""
        anime = Anime(
            title="Test Anime",
            status="Watching",
            episodes_watched=12,
            total_episodes=24
        )
        
        self.assertEqual(anime.title, "Test Anime")
        self.assertEqual(anime.status, "Watching")
        self.assertEqual(anime.episodes_watched, 12)
        self.assertEqual(anime.total_episodes, 24)
    
    def test_anime_validation(self):
        """Test anime validation"""
        # Test invalid status
        with self.assertRaises(ValueError):
            Anime(title="Test", status="Invalid")
        
        # Test invalid score
        with self.assertRaises(ValueError):
            Anime(title="Test", score=11)
        
        # Test negative episodes
        with self.assertRaises(ValueError):
            Anime(title="Test", episodes_watched=-1)
    
    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        anime = Anime(
            title="Test",
            episodes_watched=12,
            total_episodes=24
        )
        
        self.assertEqual(anime.progress_percentage, 50.0)
        self.assertEqual(anime.display_progress, "12/24")
        
        # Test with unknown total
        anime2 = Anime(title="Test2", episodes_watched=5)
        self.assertIsNone(anime2.progress_percentage)
        self.assertEqual(anime2.display_progress, "5/??")
    
    def test_episode_increment(self):
        """Test incrementing episodes"""
        anime = Anime(
            title="Test",
            status="Watching",
            episodes_watched=23,
            total_episodes=24
        )
        
        # Increment to completion
        self.assertTrue(anime.increment_episode())
        self.assertEqual(anime.episodes_watched, 24)
        self.assertEqual(anime.status, "Completed")
        
        # Try to increment beyond total
        self.assertFalse(anime.increment_episode())
        self.assertEqual(anime.episodes_watched, 24)
    
    def test_episode_decrement(self):
        """Test decrementing episodes"""
        anime = Anime(
            title="Test",
            status="Completed",
            episodes_watched=24,
            total_episodes=24
        )
        
        # Decrement from completed
        self.assertTrue(anime.decrement_episode())
        self.assertEqual(anime.episodes_watched, 23)
        self.assertEqual(anime.status, "Watching")
        
        # Test decrement at zero
        anime2 = Anime(title="Test2", episodes_watched=0)
        self.assertFalse(anime2.decrement_episode())
        self.assertEqual(anime2.episodes_watched, 0)
    
    def test_auto_complete(self):
        """Test auto-completion when reaching total episodes"""
        anime = Anime(
            title="Test",
            status="Watching",
            episodes_watched=24,
            total_episodes=24
        )
        
        # Should auto-complete on initialization
        self.assertEqual(anime.status, "Completed")
    
    def test_to_dict_conversion(self):
        """Test converting anime to dictionary"""
        anime = Anime(
            title="Test",
            genres=["Action", "Adventure"],
            score=8
        )
        
        data = anime.to_dict()
        self.assertEqual(data['title'], "Test")
        self.assertEqual(data['score'], 8)
        self.assertIn('genres', data)
        # Genres should be JSON string
        self.assertEqual(data['genres'], '["Action", "Adventure"]')


if __name__ == '__main__':
    unittest.main()