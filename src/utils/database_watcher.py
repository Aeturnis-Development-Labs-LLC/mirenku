"""
Database file watcher for automatic UI updates
Following The Mirenku Way: Simple, efficient, local monitoring
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class DatabaseWatcher:
    """Watches database file for changes and triggers callbacks"""

    def __init__(self, db_path: Path, callback: Callable, debounce_ms: int = 500):
        """
        Initialize database watcher

        Args:
            db_path: Path to database file
            callback: Function to call when database changes
            debounce_ms: Milliseconds to wait before triggering callback
        """
        self.db_path = db_path
        self.callback = callback
        self.debounce_ms = debounce_ms

        # Watching state
        self.watching = False
        self.watch_thread = None
        self.last_modified = None
        self.last_size = None

        # Debouncing
        self.pending_callback = False
        self.callback_timer = None

        # Thread safety
        self._lock = threading.Lock()

        # Initialize last known state
        if self.db_path.exists():
            self.last_modified = os.path.getmtime(self.db_path)
            self.last_size = os.path.getsize(self.db_path)

    def start(self):
        """Start watching the database file"""
        if self.watching:
            return

        self.watching = True
        self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.watch_thread.start()
        logger.info(f"Started watching database: {self.db_path}")

    def stop(self):
        """Stop watching the database file"""
        self.watching = False

        # Cancel pending callback
        if self.callback_timer:
            self.callback_timer.cancel()

        # Wait for thread to finish
        if self.watch_thread:
            self.watch_thread.join(timeout=1)

        logger.info("Stopped watching database")

    def _watch_loop(self):
        """Main watch loop running in separate thread"""
        while self.watching:
            try:
                if self.db_path.exists():
                    # Check for changes
                    current_modified = os.path.getmtime(self.db_path)
                    current_size = os.path.getsize(self.db_path)

                    # Detect changes (modified time or size)
                    if self.last_modified is not None and (
                        current_modified != self.last_modified or current_size != self.last_size
                    ):
                        logger.debug(
                            f"Database changed - Modified: {current_modified}, Size: {current_size}"
                        )
                        self._trigger_callback()

                    # Update last known state
                    self.last_modified = current_modified
                    self.last_size = current_size

                # Check every 250ms
                time.sleep(0.25)

            except Exception as e:
                logger.error(f"Error in database watch loop: {e}")
                time.sleep(1)  # Wait longer on error

    def _trigger_callback(self):
        """Trigger callback with debouncing"""
        with self._lock:
            # Cancel existing timer
            if self.callback_timer:
                self.callback_timer.cancel()

            # Schedule new callback
            self.callback_timer = threading.Timer(self.debounce_ms / 1000.0, self._execute_callback)
            self.callback_timer.daemon = True
            self.callback_timer.start()
            self.pending_callback = True

    def _execute_callback(self):
        """Execute the actual callback"""
        with self._lock:
            if self.pending_callback:
                try:
                    logger.debug("Executing database change callback")
                    self.callback()
                    self.pending_callback = False
                except Exception as e:
                    logger.error(f"Error in database change callback: {e}")

    def pause(self):
        """Temporarily pause watching (useful during bulk operations)"""
        self.watching = False

    def resume(self):
        """Resume watching after pause"""
        if not self.watching and self.watch_thread and self.watch_thread.is_alive():
            self.watching = True
        else:
            self.start()


class SmartDatabaseWatcher(DatabaseWatcher):
    """Enhanced database watcher with operation detection"""

    def __init__(self, db_path: Path, callback: Callable, debounce_ms: int = 500):
        super().__init__(db_path, callback, debounce_ms)

        # Track operations to avoid self-triggering
        self.ignore_next_change = False
        self.operation_in_progress = False

    def begin_operation(self):
        """Mark the beginning of a database operation"""
        self.operation_in_progress = True
        self.ignore_next_change = True
        logger.debug("Database operation started")

    def end_operation(self):
        """Mark the end of a database operation"""
        self.operation_in_progress = False
        # Small delay to ensure file write is complete
        threading.Timer(0.1, self._clear_ignore_flag).start()
        logger.debug("Database operation ended")

    def _clear_ignore_flag(self):
        """Clear the ignore flag after operation"""
        self.ignore_next_change = False

    def _trigger_callback(self):
        """Override to respect ignore flag"""
        if self.ignore_next_change:
            logger.debug("Ignoring self-triggered database change")
            self.ignore_next_change = False
            return

        super()._trigger_callback()
