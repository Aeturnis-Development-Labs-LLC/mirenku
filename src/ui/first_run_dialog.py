"""
First Run Dialog for welcoming users
"""

import logging
import sys
import tkinter as tk
from tkinter import ttk
from typing import Optional

from utils.first_run import FirstRunManager

logger = logging.getLogger(__name__)


class FirstRunDialog:
    """First run welcome dialog"""

    def __init__(self, parent, first_run_manager: FirstRunManager):
        """
        Initialize First Run Dialog

        Args:
            parent: Parent window
            first_run_manager: First run manager instance
        """
        logger.info("FirstRunDialog: Initializing")
        self.parent = parent
        self.first_run_manager = first_run_manager
        self.result = None

        # Create dialog window
        logger.info("FirstRunDialog: Creating Toplevel window")
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Welcome to Mirenku")
        self.dialog.geometry("650x480")
        self.dialog.resizable(False, False)
        logger.info("FirstRunDialog: Window created")

        # Make dialog modal - but don't make it transient as it might cause issues
        # self.dialog.transient(parent)  # Commented out - may cause the window to close
        self.dialog.grab_set()  # This makes it modal

        # Create UI
        logger.info("FirstRunDialog: Creating UI")
        try:
            self._create_ui()
            logger.info("FirstRunDialog: UI created successfully")
        except Exception as e:
            logger.error(f"FirstRunDialog: Error creating UI: {e}", exc_info=True)
            raise

        # Bind keys
        self.dialog.bind("<Escape>", self._on_escape)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_skip)

        # Center dialog
        logger.info("FirstRunDialog: Centering dialog")
        self._center_dialog()

        # Focus
        self.dialog.focus_force()

        # Make sure dialog is visible
        self.dialog.update_idletasks()
        self.dialog.update()  # Force update
        self.dialog.lift()
        self.dialog.attributes("-topmost", True)
        # Keep it on top for longer to ensure it's visible
        self.dialog.after(500, lambda: self.dialog.attributes("-topmost", False))

        # Ensure dialog is not minimized
        self.dialog.state("normal")
        self.dialog.deiconify()

        logger.info("FirstRunDialog: Initialization complete")

    def _create_ui(self):
        """Create the dialog UI"""
        # Main container with padding
        main_frame = ttk.Frame(self.dialog, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Logo/Title area
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))

        # Welcome message
        self.welcome_label = ttk.Label(
            title_frame, text="Welcome to Mirenku!", font=("Segoe UI", 24, "bold")
        )
        self.welcome_label.pack()

        subtitle_label = ttk.Label(
            title_frame,
            text="Your personal anime tracking companion",
            font=("Segoe UI", 11),
            foreground="gray",
        )
        subtitle_label.pack(pady=(5, 0))

        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill=tk.X, pady=20)

        # Information text
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 20))

        info_text = (
            "Track your anime locally — your data stays on this computer. "
            "Optionally connect your MyAnimeList account from the File menu "
            "to search, import, and sync your list."
        )

        info_label = ttk.Label(
            info_frame, text=info_text, wraplength=500, justify=tk.LEFT, font=("Segoe UI", 10)
        )
        info_label.pack()

        # Highlights list
        benefits_frame = ttk.Frame(main_frame)
        benefits_frame.pack(fill=tk.X, pady=(0, 20))

        benefits_title = ttk.Label(
            benefits_frame, text="What you get:", font=("Segoe UI", 11, "bold")
        )
        benefits_title.pack(anchor=tk.W, pady=(0, 10))

        benefits = [
            "✓ Local-first tracking — no account required",
            "✓ Optional MyAnimeList sync with secure OAuth",
            "✓ Episode progress, scores, and statistics",
            "✓ Import and export your list any time",
        ]

        for benefit in benefits:
            benefit_label = ttk.Label(benefits_frame, text=benefit, font=("Segoe UI", 10))
            benefit_label.pack(anchor=tk.W, pady=2)

        # Privacy note
        privacy_frame = ttk.Frame(main_frame)
        privacy_frame.pack(fill=tk.X, pady=(20, 0))

        privacy_text = (
            "Note: Your data is stored locally on this computer. Nothing is "
            "sent to external servers unless you connect a MyAnimeList account."
        )

        privacy_label = ttk.Label(
            privacy_frame,
            text=privacy_text,
            wraplength=500,
            justify=tk.LEFT,
            font=("Segoe UI", 9),
            foreground="gray",
        )
        privacy_label.pack()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

        # Skip button (left side)
        self.skip_button = ttk.Button(
            button_frame,
            text="Skip",
            command=self._on_skip,
            width=14,
        )
        self.skip_button.pack(side=tk.LEFT, padx=(0, 10))

        # Continue button (right side, primary)
        self.continue_button = ttk.Button(
            button_frame,
            text="Continue",
            command=self._on_continue,
            width=18,
            style="Accent.TButton",
        )
        self.continue_button.pack(side=tk.RIGHT)
        self.continue_button.focus_set()

    def _center_dialog(self):
        """Center the dialog on screen"""
        self.dialog.update_idletasks()

        # Get window dimensions
        window_width = self.dialog.winfo_width()
        window_height = self.dialog.winfo_height()

        # Get screen dimensions
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # Calculate position
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        self.dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _on_continue(self):
        """Handle Continue button click"""
        # Save app location
        self.first_run_manager.save_app_location(sys.executable)

        # Mark first run complete
        self.first_run_manager.set_preference("welcome_shown", True)
        self.first_run_manager.mark_first_run_complete()

        # Set result and close
        self.result = "continue"
        self.dialog.destroy()

    def _on_skip(self):
        """Handle Skip button click"""
        logger.info("FirstRunDialog: _on_skip called - User skipped first run setup")

        # Mark as skipped
        self.first_run_manager.set_preference("first_run_skipped", True)
        self.first_run_manager.mark_first_run_complete()

        # Set result and close
        self.result = "skip"
        logger.info("FirstRunDialog: Destroying dialog from _on_skip")
        self.dialog.destroy()

    def _on_escape(self, event):
        """Handle ESC key press"""
        logger.info("FirstRunDialog: ESC key pressed")
        self._on_skip()

    @staticmethod
    def should_show() -> bool:
        """
        Check if first run dialog should be shown

        Returns:
            True if dialog should be shown
        """
        return FirstRunManager().is_first_run()

    @staticmethod
    def show(parent) -> Optional[str]:
        """
        Show the first run dialog

        Args:
            parent: Parent window

        Returns:
            Dialog result ("continue" or "skip")
        """
        dialog = FirstRunDialog(parent, FirstRunManager())

        # Check if dialog window exists
        try:
            if dialog.dialog.winfo_exists():
                logger.info("FirstRunDialog: Dialog exists, waiting for window")
                parent.wait_window(dialog.dialog)
                logger.info("FirstRunDialog: Dialog closed")
            else:
                logger.error("FirstRunDialog: Dialog doesn't exist after creation!")
        except Exception as e:
            logger.error(f"FirstRunDialog: Error waiting for window: {e}")

        return dialog.result
