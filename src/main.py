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

from models.database import Database
from ui.first_run_dialog import FirstRunDialog
from ui.main_window import MainWindow
from utils.config import Config
from utils.first_run import FirstRunManager
from utils.icon_helper import set_app_icon, set_taskbar_icon
from utils.logging_config import clean_old_logs, setup_logging
from utils.protocol_handler import ProtocolHandler
from utils.single_instance import SingleInstanceManager
from utils.windows_icon_fix import force_windows_icon, set_console_icon


def handle_protocol_url(url: str, app_window=None):
    """Handle incoming protocol URL"""
    logging.info(f"Handling protocol URL: {url}")

    # If we have an app window and it's an OAuth callback
    if app_window and "mirenku://auth" in url:
        # Pass the OAuth callback to the app window's MAL auth manager
        if hasattr(app_window, "mal_auth_manager") and app_window.mal_auth_manager:
            # Parse the URL to get parameters
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(url)
            params = parse_qs(parsed.query) if parsed.query else {}

            # Extract parameters
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            error = params.get("error", [None])[0]

            # Pass to the OAuth client for processing
            if hasattr(app_window.mal_auth_manager, "oauth_client"):
                oauth_client = app_window.mal_auth_manager.oauth_client
                logging.info("Processing OAuth callback")

                # Use the proper OAuth callback handler instead of bypassing it
                oauth_client._handle_oauth_callback(code, state, error)

                # Check if authorization was successful
                if oauth_client.auth_received.is_set() and not oauth_client.auth_error:
                    logging.info("OAuth authorization successful, updating UI")
                    # Update UI on success
                    app_window._mal_auth_success()
                    # Open success page to close the OAuth flow
                    import os
                    import webbrowser

                    success_page = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)), "oauth_success.html"
                    )
                    if os.path.exists(success_page):
                        webbrowser.open(f"file:///{success_page}")
                elif oauth_client.auth_error:
                    logging.error(f"OAuth authorization failed: {oauth_client.auth_error}")
            else:
                logging.error("MAL auth manager doesn't have OAuth client")
        else:
            logging.error("App window doesn't have MAL auth manager")
    else:
        # Handle other protocol URLs
        handler = ProtocolHandler()
        handler.handle_url(url)


def handle_message(message: dict, app_window=None):
    """Handle IPC message from another instance"""
    action = message.get("action")

    if action == "protocol_url" or action == "open_url":
        url = message.get("url")
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
                instance_mgr.send_message_to_primary(
                    {"action": "protocol_url", "url": protocol_url}
                )
            else:
                # Just bring the primary instance to front
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

        app = MainWindow(root, db)

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
        from tkinter import messagebox

        messagebox.showerror(
            "Startup Error", f"Failed to start Mirenku:\n\n{e!s}\n\nCheck the logs for details."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
