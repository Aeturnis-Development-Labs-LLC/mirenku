"""End-to-end tests for complete CRUD workflow"""

import unittest
import tempfile
from pathlib import Path
import sys
import json
import csv
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.database import Database
from models.anime import Anime
from services.anime_service import AnimeService
from models.anime_repository import AnimeRepository
from utils.config import Config
from utils.persistence import PersistenceManager


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete CRUD workflow end-to-end"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()
        
        # Initialize all components as they would be in the real app
        self.db = Database(self.db_path)
        self.db.initialize()
        self.repository = AnimeRepository(self.db)
        self.service = AnimeService(self.db)
        self.config = Config()
        self.persistence = PersistenceManager(self.config, self.db)
        
        # Create temp directory for exports
        self.temp_dir = tempfile.mkdtemp()
    
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
    
    def test_complete_user_workflow(self):
        """Test a complete user workflow from start to finish"""
        print("\n=== Testing Complete User Workflow ===")
        
        # Step 1: User adds their first anime
        print("1. Adding first anime...")
        success, message, anime1_id = self.service.add_anime(
            title="Attack on Titan",
            status="Watching",
            episodes_watched=25,
            total_episodes=87,
            score=9,
            notes="Amazing story and animation!"
        )
        self.assertTrue(success)
        self.assertIsNotNone(anime1_id)
        print(f"   OK: Added: {message}")
        
        # Step 2: User adds more anime
        print("2. Adding more anime...")
        success, _, anime2_id = self.service.add_anime(
            title="Death Note",
            status="Completed",
            episodes_watched=37,
            total_episodes=37,
            score=10,
            notes="Masterpiece!"
        )
        self.assertTrue(success)
        
        success, _, anime3_id = self.service.add_anime(
            title="Steins;Gate",
            status="Plan to Watch",
            episodes_watched=0,
            total_episodes=24
        )
        self.assertTrue(success)
        print("   OK: Added 2 more anime")
        
        # Step 3: User searches for anime
        print("3. Searching for anime...")
        search_results = self.service.search_anime("titan")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].title, "Attack on Titan")
        print("   OK: Search working correctly")
        
        # Step 4: User filters by status
        print("4. Filtering by status...")
        watching = self.service.filter_anime(status="Watching")
        self.assertEqual(len(watching), 1)
        completed = self.service.filter_anime(status="Completed")
        self.assertEqual(len(completed), 1)
        print("   OK: Filtering working correctly")
        
        # Step 5: User updates episode progress
        print("5. Updating episode progress...")
        success, message = self.service.update_progress(anime1_id, 30)
        self.assertTrue(success)
        anime = self.service.get_anime(anime1_id)
        self.assertEqual(anime.episodes_watched, 30)
        print(f"   OK: Progress updated: {message}")
        
        # Step 6: User increments episodes
        print("6. Incrementing episodes...")
        success, message = self.service.increment_episode(anime1_id)
        self.assertTrue(success)
        anime = self.service.get_anime(anime1_id)
        self.assertEqual(anime.episodes_watched, 31)
        print(f"   OK: Incremented: {message}")
        
        # Step 7: User edits anime details
        print("7. Editing anime details...")
        success, message = self.service.update_anime(
            anime3_id,
            status="Watching",
            episodes_watched=5,
            score=8
        )
        self.assertTrue(success)
        anime = self.service.get_anime(anime3_id)
        self.assertEqual(anime.status, "Watching")
        self.assertEqual(anime.episodes_watched, 5)
        print("   OK: Anime details updated")
        
        # Step 8: User marks anime as completed
        print("8. Marking anime as completed...")
        success, message = self.service.mark_completed(anime3_id)
        self.assertTrue(success)
        anime = self.service.get_anime(anime3_id)
        self.assertEqual(anime.status, "Completed")
        self.assertEqual(anime.episodes_watched, 24)  # Should auto-set to total
        print("   OK: Marked as completed")
        
        # Step 9: User checks statistics
        print("9. Getting statistics...")
        stats = self.service.get_statistics()
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['by_status']['Completed'], 2)
        self.assertEqual(stats['by_status']['Watching'], 1)
        self.assertGreater(stats['total_episodes_watched'], 0)
        print(f"   OK: Stats: {stats['total']} anime, {stats['total_episodes_watched']} episodes watched")
        
        # Step 10: User exports data
        print("10. Exporting data...")
        export_path = Path(self.temp_dir) / "anime_backup.json"
        success = self.persistence.export_to_json(export_path)
        self.assertTrue(success)
        self.assertTrue(export_path.exists())
        print("   OK: Data exported to JSON")
        
        # Step 11: User deletes an anime
        print("11. Deleting anime...")
        success, message = self.service.delete_anime(anime2_id)
        self.assertTrue(success)
        all_anime = self.service.get_all_anime()
        self.assertEqual(len(all_anime), 2)
        print("   OK: Anime deleted")
        
        # Step 12: User imports data back
        print("12. Importing data...")
        imported, failed, errors = self.persistence.import_from_json(export_path)
        # Should only import the deleted one (Death Note)
        self.assertEqual(imported, 1)
        all_anime = self.service.get_all_anime(use_cache=False)
        self.assertEqual(len(all_anime), 3)
        print("   OK: Data imported successfully")
        
        print("\n=== All workflow steps completed successfully! ===")
    
    def test_data_persistence_workflow(self):
        """Test data persistence across sessions"""
        print("\n=== Testing Data Persistence ===")
        
        # Simulate first session
        print("1. First session - adding anime...")
        self.service.add_anime("Anime 1", "Watching", 5, 12, 8)
        self.service.add_anime("Anime 2", "Completed", 24, 24, 9)
        
        # Save window state
        self.persistence.save_window_state(
            "1200x800+100+50",
            "Watching",
            "score",
            "descending"
        )
        print("   OK: Data and settings saved")
        
        # Simulate app close and restart
        print("2. Simulating app restart...")
        self.db.disconnect()
        
        # Re-initialize (simulating new session)
        self.db = Database(self.db_path)
        self.db.connect()
        self.service = AnimeService(self.db)
        self.persistence = PersistenceManager(self.config, self.db)
        
        # Check data persisted
        print("3. Verifying data persistence...")
        all_anime = self.service.get_all_anime()
        self.assertEqual(len(all_anime), 2)
        
        # Check window state persisted
        state = self.persistence.load_window_state()
        self.assertEqual(state['geometry'], "1200x800+100+50")
        self.assertEqual(state['filter'], "Watching")
        print("   OK: All data persisted correctly")
    
    def test_backup_restore_workflow(self):
        """Test backup and restore workflow"""
        print("\n=== Testing Backup/Restore ===")
        
        # Add initial data
        print("1. Setting up initial data...")
        self.service.add_anime("Original 1", "Watching")
        self.service.add_anime("Original 2", "Completed")
        
        # Create backup
        print("2. Creating backup...")
        backup_path = self.persistence.create_backup()
        self.assertIsNotNone(backup_path)
        print(f"   OK: Backup created: {backup_path.name}")
        
        # Modify data
        print("3. Modifying data after backup...")
        self.service.add_anime("New After Backup", "Watching")
        all_anime = self.service.get_all_anime()
        self.assertEqual(len(all_anime), 3)
        
        # Restore from backup
        print("4. Restoring from backup...")
        success = self.persistence.restore_from_backup(backup_path)
        self.assertTrue(success)
        
        # Re-initialize service
        self.service = AnimeService(self.db)
        
        # Verify restoration
        print("5. Verifying restoration...")
        all_anime = self.service.get_all_anime(use_cache=False)
        self.assertEqual(len(all_anime), 2)
        titles = [a.title for a in all_anime]
        self.assertIn("Original 1", titles)
        self.assertIn("Original 2", titles)
        self.assertNotIn("New After Backup", titles)
        print("   OK: Data restored successfully")
    
    def test_import_export_workflow(self):
        """Test import/export workflow"""
        print("\n=== Testing Import/Export ===")
        
        # Add data
        print("1. Adding test data...")
        self.service.add_anime("Export Test 1", "Watching", 10, 24, 8)
        self.service.add_anime("Export Test 2", "Completed", 12, 12, 9)
        
        # Export to JSON
        print("2. Exporting to JSON...")
        json_path = Path(self.temp_dir) / "export.json"
        success = self.persistence.export_to_json(json_path)
        self.assertTrue(success)
        
        # Export to CSV
        print("3. Exporting to CSV...")
        csv_path = Path(self.temp_dir) / "export.csv"
        success = self.persistence.export_to_csv(csv_path)
        self.assertTrue(success)
        
        # Clear database
        print("4. Clearing database...")
        for anime in self.service.get_all_anime():
            self.service.delete_anime(anime.id)
        self.assertEqual(len(self.service.get_all_anime(use_cache=False)), 0)
        
        # Import from JSON
        print("5. Importing from JSON...")
        imported, failed, errors = self.persistence.import_from_json(json_path)
        self.assertEqual(imported, 2)
        self.assertEqual(failed, 0)
        
        # Verify import
        all_anime = self.service.get_all_anime(use_cache=False)
        self.assertEqual(len(all_anime), 2)
        print("   OK: Import/Export workflow completed")
    
    def test_error_handling_workflow(self):
        """Test error handling in workflows"""
        print("\n=== Testing Error Handling ===")
        
        # Try to add duplicate
        print("1. Testing duplicate prevention...")
        self.service.add_anime("Unique Title", "Watching")
        success, message, _ = self.service.add_anime("Unique Title", "Watching")
        self.assertFalse(success)
        self.assertIn("already exists", message)
        print("   OK: Duplicate prevented")
        
        # Try invalid data
        print("2. Testing validation...")
        success, message, _ = self.service.add_anime(
            title="",  # Empty title
            status="Watching"
        )
        self.assertFalse(success)
        self.assertIn("Title is required", message)
        print("   OK: Validation working")
        
        # Try invalid score
        print("3. Testing score validation...")
        success, message, _ = self.service.add_anime(
            title="Test",
            score=11  # Invalid score
        )
        self.assertFalse(success)
        self.assertIn("Score must be", message)
        print("   OK: Score validation working")
        
        # Try to update non-existent anime
        print("4. Testing update of non-existent anime...")
        success, message = self.service.update_anime(9999, status="Completed")
        self.assertFalse(success)
        self.assertIn("not found", message)
        print("   OK: Error handling working correctly")
    
    def test_performance_workflow(self):
        """Test performance with larger dataset"""
        print("\n=== Testing Performance ===")
        
        # Add many anime
        print("1. Adding 100 anime...")
        start_time = time.time()
        
        for i in range(100):
            self.service.add_anime(
                title=f"Anime {i+1}",
                status="Watching" if i % 3 == 0 else "Completed",
                episodes_watched=i % 24,
                total_episodes=24,
                score=(i % 10) + 1
            )
        
        add_time = time.time() - start_time
        print(f"   OK: Added 100 anime in {add_time:.2f} seconds")
        self.assertLess(add_time, 5)  # Should be fast
        
        # Test search performance
        print("2. Testing search performance...")
        start_time = time.time()
        results = self.service.search_anime("Anime 5")
        search_time = time.time() - start_time
        print(f"   OK: Search completed in {search_time:.3f} seconds")
        self.assertLess(search_time, 0.1)  # Should be very fast
        
        # Test filter performance
        print("3. Testing filter performance...")
        start_time = time.time()
        watching = self.service.filter_anime(status="Watching")
        filter_time = time.time() - start_time
        print(f"   OK: Filter completed in {filter_time:.3f} seconds")
        self.assertLess(filter_time, 0.1)
        
        # Test statistics performance
        print("4. Testing statistics performance...")
        start_time = time.time()
        stats = self.service.get_statistics()
        stats_time = time.time() - start_time
        print(f"   OK: Statistics calculated in {stats_time:.3f} seconds")
        self.assertLess(stats_time, 0.1)
        
        print(f"\n   Total anime: {stats['total']}")
        print(f"   Performance test passed!")


def run_end_to_end_tests():
    """Run all end-to-end tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEndToEndWorkflow)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("ANIME TRACKER - END-TO-END TEST SUITE")
    print("=" * 70)
    
    success = run_end_to_end_tests()
    
    print("=" * 70)
    if success:
        print("SUCCESS: ALL END-TO-END TESTS PASSED!")
    else:
        print("FAILED: SOME TESTS FAILED")
    print("=" * 70)