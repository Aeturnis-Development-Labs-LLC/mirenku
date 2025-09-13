"""Notification and error handling system"""

import logging
import tkinter as tk
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification severity levels"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationManager:
    """Manages in-app notifications"""

    def __init__(self, parent_window: tk.Tk):
        """Initialize notification manager

        Args:
            parent_window: Parent tkinter window
        """
        self.parent = parent_window
        self.active_notifications = []
        self.notification_queue = []
        self.max_notifications = 3

        # Position tracking
        self.next_y_position = 10

    def show(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        duration: int = 3000,
        callback: Optional[Callable] = None,
    ):
        """Show a notification

        Args:
            message: Notification message
            level: Notification level
            duration: Display duration in milliseconds (0 for permanent)
            callback: Optional callback when clicked
        """
        # Create notification window
        notification = NotificationWindow(
            self.parent, message, level, duration, callback, self._on_notification_closed
        )

        # Position notification
        if len(self.active_notifications) < self.max_notifications:
            notification.show(self.next_y_position)
            self.next_y_position += 70
            self.active_notifications.append(notification)
        else:
            # Queue if too many notifications
            self.notification_queue.append((message, level, duration, callback))

    def _on_notification_closed(self, notification):
        """Handle notification closure

        Args:
            notification: Closed notification
        """
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            self._reposition_notifications()

            # Show queued notification if any
            if self.notification_queue:
                args = self.notification_queue.pop(0)
                self.show(*args)

    def _reposition_notifications(self):
        """Reposition active notifications"""
        self.next_y_position = 10
        for notification in self.active_notifications:
            notification.move_to_y(self.next_y_position)
            self.next_y_position += 70

    def clear_all(self):
        """Clear all notifications"""
        for notification in self.active_notifications[:]:
            notification.close()
        self.notification_queue.clear()


class NotificationWindow:
    """Individual notification window"""

    def __init__(
        self,
        parent: tk.Tk,
        message: str,
        level: NotificationLevel,
        duration: int,
        callback: Optional[Callable],
        on_close: Callable,
    ):
        """Initialize notification window

        Args:
            parent: Parent window
            message: Notification message
            level: Notification level
            duration: Display duration
            callback: Click callback
            on_close: Close callback
        """
        self.parent = parent
        self.message = message
        self.level = level
        self.duration = duration
        self.callback = callback
        self.on_close = on_close

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        # Set colors based on level
        self.colors = {
            NotificationLevel.INFO: ("#2196F3", "#FFFFFF"),
            NotificationLevel.SUCCESS: ("#4CAF50", "#FFFFFF"),
            NotificationLevel.WARNING: ("#FF9800", "#FFFFFF"),
            NotificationLevel.ERROR: ("#F44336", "#FFFFFF"),
        }

        bg_color, fg_color = self.colors.get(level, ("#333333", "#FFFFFF"))

        # Create frame
        self.frame = tk.Frame(self.window, bg=bg_color, relief=tk.RAISED, borderwidth=2)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Icon label
        icons = {
            NotificationLevel.INFO: "ℹ",
            NotificationLevel.SUCCESS: "✓",
            NotificationLevel.WARNING: "⚠",
            NotificationLevel.ERROR: "✕",
        }

        icon_label = tk.Label(
            self.frame,
            text=icons.get(level, ""),
            bg=bg_color,
            fg=fg_color,
            font=("Arial", 16, "bold"),
        )
        icon_label.pack(side=tk.LEFT, padx=10)

        # Message label
        msg_label = tk.Label(
            self.frame,
            text=message,
            bg=bg_color,
            fg=fg_color,
            font=("Arial", 10),
            wraplength=250,
            justify=tk.LEFT,
        )
        msg_label.pack(side=tk.LEFT, padx=5, pady=10)

        # Close button
        close_btn = tk.Label(
            self.frame, text="✕", bg=bg_color, fg=fg_color, font=("Arial", 12), cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.close())

        # Bind click event
        if callback:
            self.frame.bind("<Button-1>", lambda e: callback())
            msg_label.bind("<Button-1>", lambda e: callback())
            self.window.config(cursor="hand2")

        # Auto-close timer
        if duration > 0:
            self.window.after(duration, self.close)

    def show(self, y_position: int):
        """Show notification at specified position

        Args:
            y_position: Y coordinate
        """
        # Position at top-right of parent window
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()

        width = 300
        height = 60

        x = parent_x + parent_width - width - 20
        y = parent_y + y_position + 30

        self.window.geometry(f"{width}x{height}+{x}+{y}")

        # Fade in effect
        self.window.attributes("-alpha", 0.0)
        self._fade_in()

    def move_to_y(self, y_position: int):
        """Move notification to new Y position

        Args:
            y_position: New Y coordinate
        """
        current_geometry = self.window.geometry()
        width_height = current_geometry.split("+")[0]
        x = current_geometry.split("+")[1]

        parent_y = self.parent.winfo_y()
        new_y = parent_y + y_position + 30

        self.window.geometry(f"{width_height}+{x}+{new_y}")

    def close(self):
        """Close notification"""
        try:
            self._fade_out()
        except:
            pass

    def _fade_in(self):
        """Fade in animation"""
        alpha = self.window.attributes("-alpha")
        if alpha < 1.0:
            alpha += 0.1
            self.window.attributes("-alpha", alpha)
            self.window.after(20, self._fade_in)

    def _fade_out(self):
        """Fade out animation"""
        try:
            alpha = self.window.attributes("-alpha")
            if alpha > 0.0:
                alpha -= 0.1
                self.window.attributes("-alpha", alpha)
                self.window.after(20, self._fade_out)
            else:
                self.window.destroy()
                self.on_close(self)
        except:
            # Window might be destroyed
            pass


class ErrorHandler:
    """Global error handler"""

    def __init__(self, notification_manager: Optional[NotificationManager] = None):
        """Initialize error handler

        Args:
            notification_manager: Optional notification manager
        """
        self.notification_manager = notification_manager
        self.error_log = []
        self.max_log_size = 100

        # Set up logging handler
        self.setup_logging()

    def setup_logging(self):
        """Set up custom logging handler"""
        handler = NotificationLogHandler(self)
        handler.setLevel(logging.WARNING)

        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Add to root logger
        logging.getLogger().addHandler(handler)

    def handle_error(
        self, error: Exception, context: str = "", show_notification: bool = True
    ) -> str:
        """Handle an error

        Args:
            error: Exception to handle
            context: Error context
            show_notification: Whether to show notification

        Returns:
            str: User-friendly error message
        """
        # Create error entry
        error_entry = {
            "timestamp": datetime.now(),
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
        }

        # Add to log
        self.error_log.append(error_entry)
        if len(self.error_log) > self.max_log_size:
            self.error_log.pop(0)

        # Generate user-friendly message
        user_message = self.get_user_message(error, context)

        # Show notification if manager available
        if show_notification and self.notification_manager:
            self.notification_manager.show(user_message, NotificationLevel.ERROR, duration=5000)

        # Log the error
        logger.error(f"{context}: {error}", exc_info=True)

        return user_message

    def get_user_message(self, error: Exception, context: str = "") -> str:
        """Get user-friendly error message

        Args:
            error: Exception
            context: Error context

        Returns:
            str: User-friendly message
        """
        error_messages = {
            # Database errors
            "sqlite3.DatabaseError": "Database error occurred. Please try again.",
            "sqlite3.IntegrityError": "Data conflict detected. The item may already exist.",
            "sqlite3.OperationalError": "Database is locked or unavailable.",
            # File errors
            "FileNotFoundError": "File not found. Please check the path.",
            "PermissionError": "Permission denied. Please check file permissions.",
            "IOError": "File operation failed. Please try again.",
            # Data errors
            "ValueError": "Invalid data provided. Please check your input.",
            "KeyError": "Required data is missing.",
            "TypeError": "Data type error. Please check your input.",
            # Network errors (for future MAL integration)
            "ConnectionError": "Network connection failed.",
            "TimeoutError": "Operation timed out. Please try again.",
            # JSON errors
            "json.JSONDecodeError": "Invalid JSON format in file.",
        }

        error_type = f"{error.__class__.__module__}.{error.__class__.__name__}"

        # Check for specific error message
        for error_key, message in error_messages.items():
            if error_key in error_type:
                if context:
                    return f"{context}: {message}"
                return message

        # Default message
        if context:
            return f"{context}: {error!s}"
        return f"An error occurred: {error!s}"

    def get_error_log(self) -> list:
        """Get error log

        Returns:
            list: List of error entries
        """
        return self.error_log.copy()

    def clear_error_log(self):
        """Clear error log"""
        self.error_log.clear()
        logger.info("Error log cleared")


class NotificationLogHandler(logging.Handler):
    """Custom logging handler for notifications"""

    def __init__(self, error_handler: ErrorHandler):
        """Initialize handler

        Args:
            error_handler: Error handler instance
        """
        super().__init__()
        self.error_handler = error_handler

    def emit(self, record):
        """Emit a log record

        Args:
            record: Log record
        """
        if not self.error_handler.notification_manager:
            return

        # Skip token-related errors - these are expected and handled gracefully
        message = record.getMessage()
        if "Token refresh failed" in message or "Failed to save tokens with keyring" in message:
            return

        # Determine notification level
        if record.levelno >= logging.ERROR:
            level = NotificationLevel.ERROR
        elif record.levelno >= logging.WARNING:
            level = NotificationLevel.WARNING
        else:
            level = NotificationLevel.INFO

        # Show notification for warnings and errors
        if record.levelno >= logging.WARNING:
            try:
                message = self.format(record)
                # Truncate long messages
                if len(message) > 100:
                    message = message[:97] + "..."

                self.error_handler.notification_manager.show(
                    message, level, duration=4000 if level == NotificationLevel.WARNING else 5000
                )
            except:
                # Don't let notification errors break logging
                pass


def setup_global_exception_handler(error_handler: ErrorHandler):
    """Set up global exception handler for uncaught exceptions

    Args:
        error_handler: Error handler instance
    """

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exception"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Let keyboard interrupt pass through
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Handle the error
        error_handler.handle_error(exc_value, context="Unexpected error", show_notification=True)

        # Log the full traceback
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    import sys

    sys.excepthook = handle_exception
