#!/usr/bin/env python3
"""
Anime Tracker - Main Entry Point
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
from models.database import Database


def main():
    try:
        # Set up logging
        log_dir = setup_logging(log_level="INFO")
        clean_old_logs(log_dir, days_to_keep=7)
        
        # Initialize configuration
        config = Config()
        
        # Initialize database
        db = Database(config.get_db_path())
        db.initialize()
        
        # Create and run main application
        root = tk.Tk()
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
            f"Failed to start Anime Tracker:\n\n{str(e)}\n\nCheck the logs for details."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()