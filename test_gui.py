"""Quick test script for GUI functionality"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import tkinter as tk
from models.database import Database
from ui.main_window import MainWindow
import tempfile

def test_gui():
    """Test GUI with temporary database"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    # Initialize database
    db = Database(db_path)
    db.initialize()
    
    # Add some test data
    from services.anime_service import AnimeService
    service = AnimeService(db)
    
    # Add sample anime
    service.add_anime("Attack on Titan", "Watching", 65, 87, 9)
    service.add_anime("Death Note", "Completed", 37, 37, 10)
    service.add_anime("One Piece", "Watching", 1089, None, 8)
    service.add_anime("Steins;Gate", "Plan to Watch", 0, 24)
    
    # Create and run GUI
    root = tk.Tk()
    app = MainWindow(root, db)
    
    print("GUI test started. Close window to exit.")
    root.mainloop()
    
    # Cleanup
    db_path.unlink()
    print("Test completed.")

if __name__ == "__main__":
    test_gui()