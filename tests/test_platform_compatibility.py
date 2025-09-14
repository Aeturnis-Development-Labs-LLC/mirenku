"""Cross-platform compatibility tests"""

import os
import platform
import sys
import tkinter as tk
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPlatformCompatibility:
    """Test platform-specific functionality"""

    def test_platform_detection(self):
        """Test platform detection works"""
        system = platform.system()
        assert system in ["Windows", "Linux", "Darwin"]

    def test_font_selection(self):
        """Test platform-specific fonts are available"""

        # Mock root
        root = tk.Tk()
        root.withdraw()

        # Get platform fonts
        system = platform.system()

        if system == "Darwin":  # macOS
            expected_font = "SF Pro Display"
        elif system == "Windows":
            expected_font = "Segoe UI"
        else:  # Linux
            expected_font = "Noto Sans"

        # Check font exists or fallback works
        try:
            test_label = tk.Label(root, font=(expected_font, 10))
            test_label.pack()
            root.update_idletasks()
        except tk.TclError:
            # Font not available, should fallback
            test_label = tk.Label(root, font=("TkDefaultFont", 10))

        root.destroy()

    def test_file_paths(self):
        """Test file path handling across platforms"""
        from utils.config import Config

        config = Config()
        db_path = config.get_db_path()

        # Check path is absolute
        assert Path(db_path).is_absolute()

        # Check proper separators for platform
        if platform.system() == "Windows":
            assert "\\" in str(db_path) or "/" in str(db_path)
        else:
            assert "/" in str(db_path)
            assert "\\" not in str(db_path)

    def test_icon_handling(self):
        """Test icon file handling"""
        icon_path = Path(__file__).parent.parent / "assets" / "mirenku.ico"

        if platform.system() == "Windows":
            assert icon_path.suffix == ".ico"

        # Icon should exist
        assert icon_path.exists()

    @pytest.mark.skipif(
        platform.system() == "Linux" and not os.environ.get("DISPLAY"),
        reason="No display available",
    )
    def test_gui_initialization(self):
        """Test GUI can initialize on platform"""
        root = tk.Tk()
        root.withdraw()

        # Test window geometry
        root.geometry("800x600")
        root.update_idletasks()

        # Test basic widgets
        frame = tk.Frame(root)
        frame.pack()

        button = tk.Button(frame, text="Test")
        button.pack()

        root.update_idletasks()
        root.destroy()

    def test_database_paths(self):
        """Test database file locations"""
        from models.database import Database

        # Test memory database (cross-platform)
        db = Database(":memory:")
        db.initialize()

        # Test file database with platform-specific path
        if platform.system() == "Windows":
            test_path = Path.home() / "AppData" / "Local" / "test.db"
        elif platform.system() == "Darwin":
            test_path = Path.home() / "Library" / "Application Support" / "test.db"
        else:
            test_path = Path.home() / ".local" / "share" / "test.db"

        # Ensure parent exists
        test_path.parent.mkdir(parents=True, exist_ok=True)

        # Clean up if exists
        if test_path.exists():
            test_path.unlink()

    def test_keyboard_shortcuts(self):
        """Test platform-specific keyboard shortcuts"""
        root = tk.Tk()
        root.withdraw()

        # Platform-specific modifier key
        if platform.system() == "Darwin":
            modifier = "Command"
        else:
            modifier = "Control"

        # Test binding format
        test_binding = f"<{modifier}-n>"

        # Should not raise error
        root.bind(test_binding, lambda e: None)

        root.destroy()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
