"""
First Run Dialog for welcoming users and setting up protocol registration
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import sys
import logging
from typing import Optional
from pathlib import Path

# Import managers
from utils.first_run import FirstRunManager
from utils.protocol_manager import ProtocolManager

logger = logging.getLogger(__name__)


class FirstRunDialog:
    """First run welcome dialog with protocol registration"""
    
    def __init__(self, parent, first_run_manager: FirstRunManager, protocol_manager: ProtocolManager):
        """
        Initialize First Run Dialog
        
        Args:
            parent: Parent window
            first_run_manager: First run manager instance
            protocol_manager: Protocol manager instance
        """
        self.parent = parent
        self.first_run_manager = first_run_manager
        self.protocol_manager = protocol_manager
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Welcome to Mirenku")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Variables
        self.register_protocol_var = tk.BooleanVar(value=True)
        
        # Create UI
        self._create_ui()
        
        # Bind keys
        self.dialog.bind('<Escape>', self._on_escape)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_skip)
        
        # Center dialog
        self._center_dialog()
        
        # Focus
        self.dialog.focus_force()
    
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
            title_frame,
            text="Welcome to Mirenku!",
            font=('Segoe UI', 24, 'bold')
        )
        self.welcome_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Your personal anime tracking companion",
            font=('Segoe UI', 11),
            foreground='gray'
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=20)
        
        # Information text
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        info_text = (
            "To provide the best experience with MyAnimeList integration, "
            "Mirenku needs to register a custom protocol handler. This allows "
            "secure OAuth authentication without running a local server."
        )
        
        info_label = ttk.Label(
            info_frame,
            text=info_text,
            wraplength=500,
            justify=tk.LEFT,
            font=('Segoe UI', 10)
        )
        info_label.pack()
        
        # Benefits list
        benefits_frame = ttk.Frame(main_frame)
        benefits_frame.pack(fill=tk.X, pady=(0, 20))
        
        benefits_title = ttk.Label(
            benefits_frame,
            text="What this enables:",
            font=('Segoe UI', 11, 'bold')
        )
        benefits_title.pack(anchor=tk.W, pady=(0, 10))
        
        benefits = [
            "✓ Secure MyAnimeList authentication",
            "✓ No browser security warnings",
            "✓ Automatic token management",
            "✓ Seamless integration with MAL"
        ]
        
        for benefit in benefits:
            benefit_label = ttk.Label(
                benefits_frame,
                text=benefit,
                font=('Segoe UI', 10)
            )
            benefit_label.pack(anchor=tk.W, pady=2)
        
        # Protocol registration checkbox
        checkbox_frame = ttk.Frame(main_frame)
        checkbox_frame.pack(fill=tk.X, pady=(20, 10))
        
        self.protocol_checkbox = ttk.Checkbutton(
            checkbox_frame,
            text="Register Mirenku protocol handler (recommended)",
            variable=self.register_protocol_var,
            style='Custom.TCheckbutton'
        )
        self.protocol_checkbox.pack(anchor=tk.W)
        
        # Learn more link
        self.learn_more_label = ttk.Label(
            checkbox_frame,
            text="Learn more about protocol handlers",
            font=('Segoe UI', 9, 'underline'),
            foreground='blue',
            cursor='hand2'
        )
        self.learn_more_label.pack(anchor=tk.W, padx=(22, 0), pady=(5, 0))
        self.learn_more_label.bind('<Button-1>', self._on_learn_more)
        
        # Privacy note
        privacy_frame = ttk.Frame(main_frame)
        privacy_frame.pack(fill=tk.X, pady=(20, 0))
        
        privacy_text = (
            "Note: This only affects your local system. No data is sent "
            "to external servers. You can change this setting at any time "
            "in the application settings."
        )
        
        privacy_label = ttk.Label(
            privacy_frame,
            text=privacy_text,
            wraplength=500,
            justify=tk.LEFT,
            font=('Segoe UI', 9),
            foreground='gray'
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
            width=10
        )
        self.skip_button.pack(side=tk.LEFT)
        
        # Continue button (right side, primary)
        self.continue_button = ttk.Button(
            button_frame,
            text="Continue",
            command=self._on_continue,
            width=15,
            style='Accent.TButton'
        )
        self.continue_button.pack(side=tk.RIGHT)
        self.continue_button.focus_set()
        
        # Style configuration
        self._configure_styles()
    
    def _configure_styles(self):
        """Configure custom styles"""
        style = ttk.Style()
        
        # Accent button style (primary action)
        style.configure(
            'Accent.TButton',
            font=('Segoe UI', 10, 'bold')
        )
        
        # Custom checkbox style
        style.configure(
            'Custom.TCheckbutton',
            font=('Segoe UI', 10)
        )
    
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
        # Get current executable path
        exe_path = sys.executable
        
        # Save app location
        self.first_run_manager.save_app_location(exe_path)
        
        # Register protocol if checked
        if self.register_protocol_var.get():
            logger.info("Registering protocol handler")
            success = self.protocol_manager.register_protocol(exe_path)
            
            if success:
                self.first_run_manager.set_preference("protocol_registered", True)
                logger.info("Protocol handler registered successfully")
            else:
                # Show warning but don't block
                messagebox.showwarning(
                    "Protocol Registration",
                    "Could not register the protocol handler. "
                    "You may need to run the application as administrator or "
                    "register it manually from settings.",
                    parent=self.dialog
                )
                self.first_run_manager.set_preference("protocol_registered", False)
        else:
            self.first_run_manager.set_preference("protocol_registered", False)
        
        # Mark first run complete
        self.first_run_manager.set_preference("welcome_shown", True)
        self.first_run_manager.mark_first_run_complete()
        
        # Set result and close
        self.result = "continue"
        self.dialog.destroy()
    
    def _on_skip(self):
        """Handle Skip button click"""
        logger.info("User skipped first run setup")
        
        # Mark as skipped
        self.first_run_manager.set_preference("first_run_skipped", True)
        self.first_run_manager.mark_first_run_complete()
        
        # Set result and close
        self.result = "skip"
        self.dialog.destroy()
    
    def _on_escape(self, event):
        """Handle ESC key press"""
        self._on_skip()
    
    def _on_learn_more(self, event):
        """Handle Learn More link click"""
        # Open documentation or help page
        url = "https://github.com/Aeturnis/mirenku/wiki/Protocol-Handlers"
        webbrowser.open(url)
    
    @staticmethod
    def should_show() -> bool:
        """
        Check if first run dialog should be shown
        
        Returns:
            True if dialog should be shown
        """
        first_run_mgr = FirstRunManager()
        
        # Show on first run
        if first_run_mgr.is_first_run():
            return True
        
        # Show if app moved and auto-reregister is enabled
        exe_path = sys.executable
        if first_run_mgr.has_app_moved(exe_path):
            if first_run_mgr.get_preference("auto_reregister", True):
                return True
        
        return False
    
    @staticmethod
    def show(parent) -> Optional[str]:
        """
        Show the first run dialog
        
        Args:
            parent: Parent window
            
        Returns:
            Dialog result ("continue" or "skip")
        """
        first_run_mgr = FirstRunManager()
        protocol_mgr = ProtocolManager()
        
        dialog = FirstRunDialog(parent, first_run_mgr, protocol_mgr)
        parent.wait_window(dialog.dialog)
        
        return dialog.result