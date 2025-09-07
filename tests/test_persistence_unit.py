"""Unit tests for persistence module"""

import unittest
import tempfile
from pathlib import Path
import sys
import json
import csv
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.database import Database
from services.anime_service import AnimeService
from utils.config import Config
from utils.persistence import PersistenceManager


class TestPersistenceManager(unittest.TestCase):
    """Test persistence manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()
        
        # Initialize components
        self.db = Database(self.db_path)
        self.db.initialize()
        self.service = AnimeService(self.db)
        self.config = Config()
        self.persistence = PersistenceManager(self.config, self.db)
        
        # Create temp directory for exports
        self.temp_dir = tempfile.mkdtemp()
        
        # Add test data
        self.test_anime_ids = []
        for i in range(3):
            success, msg, anime_id = self.service.add_anime(
                title=f"Test Anime {i+1}",
                status="Watching" if i == 0 else "Completed",
                episodes_watched=i * 10,
                total_episodes=24,
                score=7 + i
            )
            if success:
                self.test_anime_ids.append(anime_id)
    
    def tearDown(self):
        """Clean up test environment"""
        # Stop auto-save
        self.persistence.stop_auto_save_thread()
        
        # Disconnect database
        self.db.disconnect()
        
        # Clean up files
        import os
        import shutil
        
        if self.db_path.exists():
            os.unlink(self.db_path)
        
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_window_state_persistence(self):
        """Test saving and loading window state"""
        # Save window state
        self.persistence.save_window_state(
            geometry="1200x800+100+50",
            filter_status="Watching",
            sort_column="score",
            sort_order="descending"
        )
        
        # Load window state
        state = self.persistence.load_window_state()
        
        self.assertEqual(state["geometry"], "1200x800+100+50")
        self.assertEqual(state["filter"], "Watching")
        self.assertEqual(state["sort_column"], "score")
        self.assertEqual(state["sort_order"], "descending")
    
    def test_json_export(self):
        """Test JSON export functionality"""
        export_path = Path(self.temp_dir) / "test_export.json"
        
        # Export to JSON
        success = self.persistence.export_to_json(export_path)
        self.assertTrue(success)
        self.assertTrue(export_path.exists())
        
        # Verify content
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["total_count"], 3)
        self.assertIn("anime", data)
        self.assertEqual(len(data["anime"]), 3)
        
        # Check anime data
        anime = data["anime"][0]
        self.assertIn("title", anime)
        self.assertIn("status", anime)
        self.assertIn("episodes_watched", anime)
    
    def test_json_import(self):
        """Test JSON import functionality"""
        # Create import data
        import_data = {
            "version": "1.0",
            "anime": [
                {
                    "title": "Import Test 1",
                    "status": "Watching",
                    "episodes_watched": 5,
                    "total_episodes": 12,
                    "score": 8
                },
                {
                    "title": "Import Test 2",
                    "status": "Completed",
                    "episodes_watched": 24,
                    "total_episodes": 24,
                    "score": 9
                }
            ]
        }
        
        # Save to file
        import_path = Path(self.temp_dir) / "test_import.json"
        with open(import_path, 'w') as f:
            json.dump(import_data, f)
        
        # Import from JSON
        imported, failed, errors = self.persistence.import_from_json(import_path)
        
        self.assertEqual(imported, 2)
        self.assertEqual(failed, 0)
        self.assertEqual(len(errors), 0)
        
        # Verify imported anime exist
        all_anime = self.service.get_all_anime()
        titles = [a.title for a in all_anime]
        self.assertIn("Import Test 1", titles)
        self.assertIn("Import Test 2", titles)
    
    def test_csv_export(self):
        """Test CSV export functionality"""
        export_path = Path(self.temp_dir) / "test_export.csv"
        
        # Export to CSV
        success = self.persistence.export_to_csv(export_path)
        self.assertTrue(success)
        self.assertTrue(export_path.exists())
        
        # Verify content
        with open(export_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 3)
        
        # Check first row
        first = rows[0]
        self.assertEqual(first['title'], "Test Anime 1")
        self.assertEqual(first['status'], "Watching")
        self.assertEqual(first['episodes_watched'], "0")
    
    def test_csv_import(self):
        """Test CSV import functionality"""
        # Create CSV file
        import_path = Path(self.temp_dir) / "test_import.csv"
        
        with open(import_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'status', 'episodes_watched', 'score'])
            writer.writeheader()
            writer.writerow({
                'title': 'CSV Import 1',
                'status': 'Watching',
                'episodes_watched': '10',
                'score': '7'
            })
            writer.writerow({
                'title': 'CSV Import 2',
                'status': 'Completed',
                'episodes_watched': '12',
                'score': '8'
            })
        
        # Import from CSV
        imported, failed, errors = self.persistence.import_from_csv(import_path)
        
        self.assertEqual(imported, 2)
        self.assertEqual(failed, 0)
        
        # Verify imported anime
        all_anime = self.service.get_all_anime()
        titles = [a.title for a in all_anime]
        self.assertIn("CSV Import 1", titles)
        self.assertIn("CSV Import 2", titles)
    
    def test_backup_creation(self):
        """Test database backup creation"""
        # Create backup
        backup_path = self.persistence.create_backup()
        
        self.assertIsNotNone(backup_path)
        self.assertTrue(backup_path.exists())
        self.assertTrue(str(backup_path).endswith(".db"))
        
        # Verify backup is valid database
        backup_db = Database(backup_path)
        backup_db.connect()
        
        # Check data exists in backup
        with backup_db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM anime")
            count = cursor.fetchone()['count']
        
        self.assertEqual(count, 3)
        backup_db.disconnect()
    
    def test_backup_list(self):
        """Test getting backup list"""
        # Create multiple backups
        backup1 = self.persistence.create_backup()
        import time
        time.sleep(0.1)  # Ensure different timestamps
        backup2 = self.persistence.create_backup()
        
        # Get backup list
        backups = self.persistence.get_backup_list()
        
        self.assertGreaterEqual(len(backups), 2)
        
        # Check backup info
        for backup in backups:
            self.assertIn("path", backup)
            self.assertIn("name", backup)
            self.assertIn("size", backup)
            self.assertIn("created", backup)
            self.assertIn("size_mb", backup)
            
            self.assertTrue(backup["path"].exists())
            self.assertIsInstance(backup["created"], datetime)
    
    def test_backup_restore(self):
        """Test restoring from backup"""
        # Create backup
        backup_path = self.persistence.create_backup()
        
        # Add more data after backup
        self.service.add_anime("After Backup", "Watching")
        
        # Verify new anime exists
        all_anime = self.service.get_all_anime()
        self.assertEqual(len(all_anime), 4)
        
        # Restore from backup
        success = self.persistence.restore_from_backup(backup_path)
        self.assertTrue(success)
        
        # Re-initialize service after restore to get fresh data
        self.service = AnimeService(self.db)
        
        # Verify data restored to backup state
        all_anime = self.service.get_all_anime(use_cache=False)
        self.assertEqual(len(all_anime), 3)
        
        titles = [a.title for a in all_anime]
        self.assertNotIn("After Backup", titles)
    
    def test_database_optimization(self):
        """Test database optimization"""
        # Run optimization
        try:
            self.persistence.optimize_database()
            # If no exception, optimization succeeded
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Database optimization failed: {e}")
    
    def test_auto_save_thread(self):
        """Test auto-save thread management"""
        # Stop auto-save (from setUp)
        self.persistence.stop_auto_save_thread()
        
        # Start auto-save
        self.persistence.start_auto_save()
        
        # Verify thread is running
        self.assertIsNotNone(self.persistence.auto_save_thread)
        self.assertTrue(self.persistence.auto_save_thread.is_alive())
        
        # Stop auto-save
        self.persistence.stop_auto_save_thread()
        
        # Verify thread stopped
        self.assertTrue(self.persistence.stop_auto_save.is_set())


if __name__ == '__main__':
    unittest.main()