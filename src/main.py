#!/usr/bin/env python3
"""
Mirenku - Main Entry Point
A desktop application for tracking anime viewing progress
"""

import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

import tkinter as tk

from app_context import AppContext
from models.database import Database
from ui.first_run_dialog import FirstRunDialog
from ui.main_window import MainWindow
from utils.config import Config
from utils.first_run import FirstRunManager
from utils.icon_helper import set_app_icon, set_taskbar_icon
from utils.legacy_cleanup import cleanup_legacy_protocol_registration
from utils.logging_config import clean_old_logs, setup_logging
from utils.single_instance import SingleInstanceManager
from utils.windows_icon_fix import force_windows_icon, set_console_icon


def handle_message(message: dict, root: "tk.Tk" = None):
    """Handle IPC message from another instance"""
    action = message.get("action")

    if action == "activate":
        if root is not None:
            root.deiconify()
            root.lift()
            root.focus_force()
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

        # Remove the legacy mirenku:// protocol registration if present
        cleanup_legacy_protocol_registration()

        # Initialize single instance manager
        instance_mgr = SingleInstanceManager()

        # Check if we're the primary instance
        if not instance_mgr.acquire_lock():
            logging.info("Another instance is already running")

            # Bring the primary instance to front
            instance_mgr.send_message_to_primary({"action": "activate"})

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
            if getattr(sys, "frozen", False):
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

        # Build all services (composition root); must run after tk.Tk()
        context = AppContext.build(config, db)

        app = MainWindow(root, context)

        # Center window on screen
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

        # Check if we should show first-run dialog
        first_run_mgr = FirstRunManager()
        if FirstRunDialog.should_show():
            logging.info("Showing first-run dialog")
            try:
                # Don't hide the root window, just show the dialog on top
                FirstRunDialog.show(root)
            except Exception as e:
                logging.error(f"Error showing first-run dialog: {e}", exc_info=True)

        # Start message listener for IPC (activate/bring-to-front from second instances)
        def message_callback(msg):
            # Run in main thread
            root.after(0, lambda: handle_message(msg, root))

        instance_mgr.register_message_callback(message_callback)
        instance_mgr.start_message_listener()

        # Start the application
        logging.info("Application ready")
        root.mainloop()

        # Cleanup
        instance_mgr.stop_message_listener()
        instance_mgr.release()

    except Exception as e:
        logging.critical(f"Failed to start application: {e}", exc_info=True)
        # Show error dialog if GUI fails
        from tkinter import messagebox

        messagebox.showerror(
            "Startup Error", f"Failed to start Mirenku:\n\n{e!s}\n\nCheck the logs for details."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
