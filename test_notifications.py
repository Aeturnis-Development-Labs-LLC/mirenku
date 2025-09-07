"""Test notification and error handling system"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import tkinter as tk
from utils.notifications import NotificationManager, NotificationLevel, ErrorHandler
import time


def test_notifications():
    """Test notification system"""
    # Create test window
    root = tk.Tk()
    root.title("Notification Test")
    root.geometry("800x600")
    
    # Create notification manager
    notifications = NotificationManager(root)
    error_handler = ErrorHandler(notifications)
    
    # Create test buttons
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack()
    
    tk.Label(frame, text="Notification System Test", font=("Arial", 16, "bold")).pack(pady=10)
    
    # Info notification
    def show_info():
        notifications.show(
            "This is an info notification",
            NotificationLevel.INFO,
            duration=3000
        )
    
    tk.Button(
        frame,
        text="Show Info",
        command=show_info,
        width=20
    ).pack(pady=5)
    
    # Success notification
    def show_success():
        notifications.show(
            "Operation completed successfully!",
            NotificationLevel.SUCCESS,
            duration=3000
        )
    
    tk.Button(
        frame,
        text="Show Success",
        command=show_success,
        width=20
    ).pack(pady=5)
    
    # Warning notification
    def show_warning():
        notifications.show(
            "Warning: Low disk space",
            NotificationLevel.WARNING,
            duration=4000
        )
    
    tk.Button(
        frame,
        text="Show Warning",
        command=show_warning,
        width=20
    ).pack(pady=5)
    
    # Error notification
    def show_error():
        notifications.show(
            "Error: Failed to save file",
            NotificationLevel.ERROR,
            duration=5000
        )
    
    tk.Button(
        frame,
        text="Show Error",
        command=show_error,
        width=20
    ).pack(pady=5)
    
    # Multiple notifications
    def show_multiple():
        notifications.show("First notification", NotificationLevel.INFO)
        notifications.show("Second notification", NotificationLevel.SUCCESS)
        notifications.show("Third notification", NotificationLevel.WARNING)
        notifications.show("Fourth (queued)", NotificationLevel.INFO)
    
    tk.Button(
        frame,
        text="Show Multiple",
        command=show_multiple,
        width=20
    ).pack(pady=5)
    
    # Test error handling
    def trigger_error():
        try:
            # Simulate database error
            raise ValueError("Invalid anime data: score must be between 0-10")
        except Exception as e:
            message = error_handler.handle_error(e, "Validation Error")
            print(f"Error handled: {message}")
    
    tk.Button(
        frame,
        text="Trigger Error",
        command=trigger_error,
        width=20
    ).pack(pady=5)
    
    # Test file error
    def trigger_file_error():
        try:
            # Simulate file error
            raise FileNotFoundError("anime_list.json not found")
        except Exception as e:
            message = error_handler.handle_error(e, "Import Failed")
            print(f"Error handled: {message}")
    
    tk.Button(
        frame,
        text="Trigger File Error",
        command=trigger_file_error,
        width=20
    ).pack(pady=5)
    
    # Clear all notifications
    tk.Button(
        frame,
        text="Clear All",
        command=notifications.clear_all,
        width=20
    ).pack(pady=10)
    
    # Show error log
    def show_error_log():
        log = error_handler.get_error_log()
        if log:
            print("\n=== Error Log ===")
            for entry in log:
                print(f"{entry['timestamp']}: {entry['type']} - {entry['message']}")
        else:
            print("No errors logged")
    
    tk.Button(
        frame,
        text="Show Error Log",
        command=show_error_log,
        width=20
    ).pack(pady=5)
    
    # Instructions
    tk.Label(
        frame,
        text="Click buttons to test different notification types.\n" +
             "Notifications appear in top-right corner.\n" +
             "They auto-dismiss after a few seconds.",
        justify=tk.CENTER
    ).pack(pady=20)
    
    print("Notification test window opened. Click buttons to test.")
    root.mainloop()


if __name__ == "__main__":
    test_notifications()