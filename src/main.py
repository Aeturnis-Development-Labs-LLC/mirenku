#!/usr/bin/env python3
"""
Mirenku - Main Entry Point
A desktop application for tracking anime viewing progress
"""

import sys
import os
from pathlib import Path
import logging

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow
import tkinter as tk
from utils.config import Config
from utils.logging_config import setup_logging, clean_old_logs
from utils.icon_helper import set_app_icon, set_taskbar_icon
from utils.windows_icon_fix import force_windows_icon, set_console_icon
from models.database import Database


def main():
    try:
        # Initialize configuration first
        config = Config()
        
        # Set up logging with config
        log_dir = setup_logging(log_level="INFO", config=config)
        clean_old_logs(log_dir, days_to_keep=7)
        
        # Log version
        from __init__ import __version__
        logging.info(f"Mirenku v{__version__} starting...")
        
        # Initialize database
        db = Database(config.get_db_path())
        db.initialize()
        
        # Apply Windows-specific icon fixes early
        force_windows_icon()
        set_console_icon()
        set_taskbar_icon()
        
        # Create and run main application
        root = tk.Tk()
        
        # Set application icon with proper path handling for frozen exe
        try:
            if getattr(sys, 'frozen', False):
                # Running as executable - use bundled icon
                icon_path = Path(sys._MEIPASS) / "assets" / "mirenku.ico"
            else:
                # Running as script
                icon_path = Path(__file__).parent.parent / "assets" / "mirenku.ico"
            
            if icon_path.exists():
                root.iconbitmap(default=str(icon_path))
                root.wm_iconbitmap(str(icon_path))
                logging.info(f"Icon set from: {icon_path}")
            else:
                logging.warning(f"Icon not found at: {icon_path}")
                # Try the icon helper as fallback
                set_app_icon(root)
        except Exception as e:
            logging.debug(f"Could not set icon: {e}")
            set_app_icon(root)
        
        # Apply Windows icon fix again after window creation
        root.update_idletasks()
        force_windows_icon()
        
        app = MainWindow(root, db)
        
        # Center window on screen
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Start the application
        logging.info("Application ready")
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"Failed to start application: {e}", exc_info=True)
        # Show error dialog if GUI fails
        import tkinter.messagebox as messagebox
        messagebox.showerror(
            "Startup Error",
            f"Failed to start Mirenku:\n\n{str(e)}\n\nCheck the logs for details."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()