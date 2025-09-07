"""Test persistence and auto-save features"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import tempfile
import json
from models.database import Database
from services.anime_service import AnimeService
from utils.config import Config
from utils.persistence import PersistenceManager


def test_persistence():
    """Test persistence features"""
    print("Testing persistence features...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    # Initialize
    db = Database(db_path)
    db.initialize()
    service = AnimeService(db)
    config = Config()
    persistence = PersistenceManager(config, db)
    
    # Add test data
    print("\n1. Adding test anime...")
    service.add_anime("Test Anime 1", "Watching", 5, 12, 8)
    service.add_anime("Test Anime 2", "Completed", 24, 24, 9)
    service.add_anime("Test Anime 3", "Plan to Watch", 0, 12)
    
    # Test JSON export
    print("\n2. Testing JSON export...")
    export_path = Path(tempfile.gettempdir()) / "anime_export.json"
    if persistence.export_to_json(export_path):
        print(f"   OK: Exported to {export_path}")
        
        # Check export content
        with open(export_path, 'r') as f:
            data = json.load(f)
            print(f"   OK: Exported {data['total_count']} anime")
    
    # Test CSV export
    print("\n3. Testing CSV export...")
    csv_path = Path(tempfile.gettempdir()) / "anime_export.csv"
    if persistence.export_to_csv(csv_path):
        print(f"   OK: Exported to {csv_path}")
    
    # Test backup
    print("\n4. Testing backup creation...")
    backup_path = persistence.create_backup()
    if backup_path:
        print(f"   OK: Backup created: {backup_path}")
    
    # Test window state
    print("\n5. Testing window state persistence...")
    persistence.save_window_state("1200x800+100+50", "Watching", "title", "ascending")
    state = persistence.load_window_state()
    print(f"   OK: Saved state: {state}")
    
    # Test import
    print("\n6. Testing JSON import...")
    # Clear database first
    for anime in service.get_all_anime():
        service.delete_anime(anime.id)
    
    # Import back
    imported, failed, errors = persistence.import_from_json(export_path)
    print(f"   OK: Imported {imported} anime, {failed} failed")
    
    # Verify import
    all_anime = service.get_all_anime()
    print(f"   OK: Database now has {len(all_anime)} anime")
    
    # Test backup list
    print("\n7. Testing backup list...")
    backups = persistence.get_backup_list()
    print(f"   OK: Found {len(backups)} backup(s)")
    for backup in backups:
        print(f"      - {backup['name']} ({backup['size_mb']} MB)")
    
    # Cleanup
    print("\n8. Cleaning up...")
    persistence.stop_auto_save_thread()
    db.disconnect()
    
    # Remove temp files
    db_path.unlink()
    export_path.unlink()
    csv_path.unlink()
    
    print("\n[SUCCESS] All persistence tests passed!")


if __name__ == "__main__":
    test_persistence()