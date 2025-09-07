"""Tests for notification and error handling system"""

import unittest
from pathlib import Path
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.notifications import (
    NotificationLevel, ErrorHandler, NotificationLogHandler,
    NotificationManager
)


class TestErrorHandler(unittest.TestCase):
    """Test error handler functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.error_handler = ErrorHandler()
    
    def test_error_handling(self):
        """Test basic error handling"""
        # Create test error
        error = ValueError("Test error message")
        
        # Handle error
        message = self.error_handler.handle_error(
            error,
            context="Test Context",
            show_notification=False
        )
        
        # Check message format
        self.assertIn("Test Context", message)
        self.assertIn("Invalid data", message)
        
        # Check error was logged
        log = self.error_handler.get_error_log()
        self.assertEqual(len(log), 1)
        
        entry = log[0]
        self.assertEqual(entry["type"], "ValueError")
        self.assertEqual(entry["message"], "Test error message")
        self.assertEqual(entry["context"], "Test Context")
        self.assertIsInstance(entry["timestamp"], datetime)
    
    def test_user_friendly_messages(self):
        """Test user-friendly error message generation"""
        # Test database error
        import sqlite3
        db_error = sqlite3.DatabaseError("database is locked")
        message = self.error_handler.get_user_message(db_error)
        self.assertIn("Database error occurred", message)
        
        # Test file error
        file_error = FileNotFoundError("file.txt")
        message = self.error_handler.get_user_message(file_error)
        self.assertIn("File not found", message)
        
        # Test permission error
        perm_error = PermissionError("Access denied")
        message = self.error_handler.get_user_message(perm_error)
        self.assertIn("Permission denied", message)
        
        # Test value error
        val_error = ValueError("Invalid input")
        message = self.error_handler.get_user_message(val_error)
        self.assertIn("Invalid data", message)
        
        # Test unknown error
        unknown_error = Exception("Unknown error")
        message = self.error_handler.get_user_message(unknown_error)
        self.assertIn("An error occurred", message)
    
    def test_error_log_management(self):
        """Test error log management"""
        # Add multiple errors
        for i in range(5):
            error = Exception(f"Error {i}")
            self.error_handler.handle_error(
                error,
                context=f"Context {i}",
                show_notification=False
            )
        
        # Check log size
        log = self.error_handler.get_error_log()
        self.assertEqual(len(log), 5)
        
        # Clear log
        self.error_handler.clear_error_log()
        log = self.error_handler.get_error_log()
        self.assertEqual(len(log), 0)
    
    def test_error_log_size_limit(self):
        """Test error log size limiting"""
        # Set max size
        self.error_handler.max_log_size = 10
        
        # Add more errors than max
        for i in range(15):
            error = Exception(f"Error {i}")
            self.error_handler.handle_error(
                error,
                show_notification=False
            )
        
        # Check log is limited
        log = self.error_handler.get_error_log()
        self.assertEqual(len(log), 10)
        
        # Check oldest errors were removed
        messages = [entry["message"] for entry in log]
        self.assertNotIn("Error 0", messages)
        self.assertNotIn("Error 4", messages)
        self.assertIn("Error 14", messages)
    
    def test_context_in_messages(self):
        """Test context inclusion in error messages"""
        error = ValueError("Test error")
        
        # With context
        message = self.error_handler.get_user_message(error, "Import failed")
        self.assertIn("Import failed", message)
        
        # Without context
        message = self.error_handler.get_user_message(error)
        self.assertNotIn("Import failed", message)


class TestNotificationLogHandler(unittest.TestCase):
    """Test notification log handler"""
    
    def test_log_handler_creation(self):
        """Test creating log handler"""
        error_handler = ErrorHandler()
        handler = NotificationLogHandler(error_handler)
        
        self.assertIsNotNone(handler)
        self.assertEqual(handler.error_handler, error_handler)
    
    def test_log_record_emission(self):
        """Test emitting log records"""
        # Create handler
        error_handler = ErrorHandler()
        handler = NotificationLogHandler(error_handler)
        
        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Test error message",
            args=(),
            exc_info=None
        )
        
        # Emit record (should not raise exception even without notification manager)
        try:
            handler.emit(record)
            # If no exception, test passes
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Handler emission failed: {e}")


class TestNotificationLevel(unittest.TestCase):
    """Test notification level enum"""
    
    def test_notification_levels(self):
        """Test notification level values"""
        self.assertEqual(NotificationLevel.INFO.value, "info")
        self.assertEqual(NotificationLevel.SUCCESS.value, "success")
        self.assertEqual(NotificationLevel.WARNING.value, "warning")
        self.assertEqual(NotificationLevel.ERROR.value, "error")
    
    def test_level_comparison(self):
        """Test level comparisons"""
        levels = list(NotificationLevel)
        self.assertEqual(len(levels), 4)
        
        # Check all levels are unique
        values = [level.value for level in levels]
        self.assertEqual(len(values), len(set(values)))


class TestLoggingIntegration(unittest.TestCase):
    """Test logging integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.error_handler = ErrorHandler()
        
        # Store original handlers
        self.original_handlers = logging.getLogger().handlers.copy()
    
    def tearDown(self):
        """Clean up test environment"""
        # Restore original handlers
        logging.getLogger().handlers = self.original_handlers
    
    def test_logging_setup(self):
        """Test logging setup"""
        # Setup logging
        self.error_handler.setup_logging()
        
        # Check handler was added
        handlers = logging.getLogger().handlers
        log_handlers = [h for h in handlers if isinstance(h, NotificationLogHandler)]
        
        self.assertGreaterEqual(len(log_handlers), 1)
    
    def test_logging_integration(self):
        """Test logging integration with error handler"""
        # Setup logging
        self.error_handler.setup_logging()
        
        # Create logger
        logger = logging.getLogger("test_logger")
        
        # Log an error (should be captured by error handler)
        logger.error("Test error from logger")
        
        # Note: Without a notification manager, this just tests that logging doesn't break
        # The actual notification display is tested in GUI tests
        self.assertTrue(True)  # If we get here without exception, integration works


if __name__ == '__main__':
    unittest.main()