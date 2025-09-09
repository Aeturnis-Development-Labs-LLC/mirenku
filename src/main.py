#!/usr/bin/env python3
"""
Mirenku - Main Entry Point
A desktop application for tracking anime viewing progress
"""

import sys
import os
from pathlib import Path
import logging
import threading

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow
import tkinter as tk
from utils.config import Config
from utils.logging_config import setup_logging, clean_old_logs
from utils.icon_helper import set_app_icon, set_taskbar_icon
from utils.windows_icon_fix import force_windows_icon, set_console_icon
from models.database import Database
from utils.single_instance import SingleInstanceManager
from utils.protocol_handler import ProtocolHandler
from utils.first_run import FirstRunManager
from ui.first_run_dialog import FirstRunDialog


def handle_protocol_url(url: str, app_window=None):
    """Handle incoming protocol URL"""
    logging.info(f"Handling protocol URL: {url}")
    
    # Parse and route the URL
    handler = ProtocolHandler()
    
    # If we have an app window, we can handle OAuth callbacks
    if app_window and "mirenku://auth" in url:
        # This will be handled by the OAuth client when user connects MAL
        from services.mal_oauth2_protocol import handle_protocol_url as handle_oauth
        handle_oauth(url)
    else:
        handler.handle_url(url)


def handle_message(message: dict, app_window=None):
    """Handle IPC message from another instance"""
    action = message.get('action')
    
    if action == 'protocol_url':
        url = message.get('url')
        if url:
            handle_protocol_url(url, app_window)
    elif action == 'open_url':
        url = message.get('url')
        if url:
            handle_protocol_url(url, app_window)
    else:
        logging.warning(f"Unknown message action: {action}")


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
        
        # Check for protocol URL in command line args
        protocol_url = None
        if len(sys.argv) > 1 and sys.argv[1].startswith("mirenku://"):
            protocol_url = sys.argv[1]
            logging.info(f"Received protocol URL from command line: {protocol_url}")
        
        # Initialize single instance manager
        instance_mgr = SingleInstanceManager()
        
        # Check if we're the primary instance
        if not instance_mgr.acquire_lock():
            logging.info("Another instance is already running")
            
            # If we have a protocol URL, forward it to the primary instance
            if protocol_url:
                logging.info("Forwarding protocol URL to primary instance")
                instance_mgr.send_message_to_primary({
                    'action': 'protocol_url',
                    'url': protocol_url
                })
            else:
                # Just bring the primary instance to front
                instance_mgr.send_message_to_primary({
                    'action': 'activate'
                })
            
            logging.info("Exiting - primary instance will handle the request")
            sys.exit(0)
        
        logging.info("Running as primary instance")
        
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
        
        # Check if we should show first-run dialog
        first_run_mgr = FirstRunManager()
        if FirstRunDialog.should_show():
            logging.info("Showing first-run dialog")
            root.withdraw()  # Hide main window temporarily
            FirstRunDialog.show(root)
            root.deiconify()  # Show main window again
        
        # Start message listener for IPC
        def message_callback(msg):
            # Run in main thread
            root.after(0, lambda: handle_message(msg, app))
        
        instance_mgr.register_message_callback(message_callback)
        listener_thread = instance_mgr.start_message_listener()
        
        # Handle any protocol URL that was passed on startup
        if protocol_url:
            root.after(100, lambda: handle_protocol_url(protocol_url, app))
        
        # Start the application
        logging.info("Application ready")
        root.mainloop()
        
        # Cleanup
        instance_mgr.stop_message_listener()
        instance_mgr.release()
        
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