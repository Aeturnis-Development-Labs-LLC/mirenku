"""
Settings Dialog with Protocol Management
"""

import logging
import sys
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Optional

# Import managers
from src.utils.first_run import FirstRunManager
from src.utils.protocol_manager import ProtocolManager

logger = logging.getLogger(__name__)


class SettingsDialog:
    """Settings dialog with tabs for different configuration areas"""

    def __init__(
        self,
        parent,
        config=None,
        first_run_manager: FirstRunManager = None,
        protocol_manager: ProtocolManager = None,
        scrobbling_manager=None,
    ):
        """
        Initialize Settings Dialog

        Args:
            parent: Parent window
            first_run_manager: First run manager instance (optional)
            protocol_manager: Protocol manager instance (optional)
            scrobbling_manager: Scrobbling manager instance (optional)
        """
        self.parent = parent
        self.config = config  # Added config parameter
        self.first_run_manager = first_run_manager or FirstRunManager()
        self.protocol_manager = protocol_manager or ProtocolManager()
        self.scrobbling_manager = scrobbling_manager
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("700x500")
        self.dialog.resizable(False, False)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Variables
        self.auto_reregister_var = tk.BooleanVar(
            value=self.first_run_manager.get_preference("auto_reregister", True)
        )
        self.theme_var = tk.StringVar(
            value=self.first_run_manager.get_preference("theme", "System")
        )
        self.auto_sync_var = tk.BooleanVar(
            value=self.first_run_manager.get_preference("auto_sync", False)
        )
        self.sync_interval_var = tk.IntVar(
            value=self.first_run_manager.get_preference("sync_interval", 30)
        )
        self.conflict_var = tk.StringVar(
            value=self.first_run_manager.get_preference("conflict_resolution", "ask")
        )
        # Version check variables
        self.check_updates_var = tk.BooleanVar(
            value=self.config.get("check_for_updates", False) if self.config else False
        )
        self.show_update_dialog_var = tk.BooleanVar(
            value=self.config.get("show_update_dialog", True) if self.config else True
        )

        # Scrobbling variables (if manager is provided)
        if self.scrobbling_manager:
            self.scrobbling_enabled_var = tk.BooleanVar(value=self.scrobbling_manager.enabled)
            self.scrobbling_port_var = tk.StringVar(value=str(self.scrobbling_manager.port))

        # Create UI
        self._create_ui()

        # Bind keys
        self.dialog.bind("<Escape>", lambda e: self._on_cancel())
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center dialog
        self._center_dialog()

        # Focus
        self.dialog.focus_force()

    def _create_ui(self):
        """Create the dialog UI"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create tabs
        self._create_general_tab()
        self._create_protocol_tab()
        self._create_sync_tab()
        self._create_updates_tab()

        # Create scrobbling tab if manager is provided
        if self.scrobbling_manager:
            self._create_scrobbling_tab()

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel, width=10)
        cancel_button.pack(side=tk.LEFT, padx=(0, 5))

        # Save button
        save_button = ttk.Button(
            button_frame, text="Save", command=self._on_save, width=10, style="Accent.TButton"
        )
        save_button.pack(side=tk.RIGHT)

        # Configure styles
        self._configure_styles()

    def _create_general_tab(self):
        """Create General settings tab"""
        self.general_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.general_frame, text="General")

        # Theme selection
        theme_label = ttk.Label(self.general_frame, text="Theme:")
        theme_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        self.theme_combo = ttk.Combobox(
            self.general_frame,
            textvariable=self.theme_var,
            values=["System", "Light", "Dark"],
            state="readonly",
            width=20,
        )
        self.theme_combo.grid(row=0, column=1, sticky=tk.W, pady=(0, 10))

        # Separator
        ttk.Separator(self.general_frame, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=20
        )

        # Application info
        info_label = ttk.Label(
            self.general_frame, text="Mirenku v0.3.1", font=("Segoe UI", 10, "bold")
        )
        info_label.grid(row=2, column=0, columnspan=2, sticky=tk.W)

        info_text = ttk.Label(
            self.general_frame, text="Your personal anime tracking companion", foreground="gray"
        )
        info_text.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

    def _create_protocol_tab(self):
        """Create Protocol settings tab"""
        self.protocol_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.protocol_frame, text="Protocol")

        # Protocol status
        status_frame = ttk.LabelFrame(
            self.protocol_frame, text="Protocol Handler Status", padding="15"
        )
        status_frame.pack(fill=tk.X, pady=(0, 20))

        # Status label
        self.protocol_status_label = ttk.Label(
            status_frame, text="Checking status...", font=("Segoe UI", 10)
        )
        self.protocol_status_label.pack(anchor=tk.W)

        # Registered path (if applicable)
        self.path_label = ttk.Label(status_frame, text="", foreground="gray", font=("Segoe UI", 9))
        self.path_label.pack(anchor=tk.W, pady=(5, 0))

        # Actions frame
        actions_frame = ttk.LabelFrame(self.protocol_frame, text="Actions", padding="15")
        actions_frame.pack(fill=tk.X, pady=(0, 20))

        # Register/Unregister button (will be created dynamically)
        self.register_button = None
        self.unregister_button = None

        # Test protocol button
        self.test_button = ttk.Button(
            actions_frame, text="Test Protocol", command=self._on_test_protocol, width=20
        )
        self.test_button.pack(pady=5)

        # Options frame
        options_frame = ttk.LabelFrame(self.protocol_frame, text="Options", padding="15")
        options_frame.pack(fill=tk.X)

        # Auto-reregister checkbox
        self.auto_reregister_checkbox = ttk.Checkbutton(
            options_frame,
            text="Automatically re-register when application moves",
            variable=self.auto_reregister_var,
        )
        self.auto_reregister_checkbox.pack(anchor=tk.W)

        # Info text
        info_label = ttk.Label(
            options_frame,
            text=(
                "The protocol handler allows Mirenku to receive OAuth callbacks "
                "from MyAnimeList without running a local server."
            ),
            wraplength=500,
            foreground="gray",
            font=("Segoe UI", 9),
        )
        info_label.pack(anchor=tk.W, pady=(15, 0))

        # Refresh status
        self._refresh_protocol_status()

    def _create_sync_tab(self):
        """Create Sync settings tab"""
        self.sync_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.sync_frame, text="Sync")

        # Auto-sync settings
        sync_frame = ttk.LabelFrame(self.sync_frame, text="Automatic Sync", padding="15")
        sync_frame.pack(fill=tk.X, pady=(0, 20))

        # Auto-sync checkbox
        auto_sync_checkbox = ttk.Checkbutton(
            sync_frame,
            text="Enable automatic synchronization with MyAnimeList",
            variable=self.auto_sync_var,
            command=self._on_auto_sync_toggle,
        )
        auto_sync_checkbox.pack(anchor=tk.W)

        # Sync interval
        interval_frame = ttk.Frame(sync_frame)
        interval_frame.pack(anchor=tk.W, pady=(10, 0))

        ttk.Label(interval_frame, text="Sync interval:").pack(side=tk.LEFT)

        self.interval_spinbox = ttk.Spinbox(
            interval_frame,
            from_=5,
            to=120,
            width=10,
            textvariable=self.sync_interval_var,
            state="readonly" if not self.auto_sync_var.get() else "normal",
        )
        self.interval_spinbox.pack(side=tk.LEFT, padx=(10, 5))

        ttk.Label(interval_frame, text="minutes").pack(side=tk.LEFT)

        # Conflict resolution
        conflict_frame = ttk.LabelFrame(self.sync_frame, text="Conflict Resolution", padding="15")
        conflict_frame.pack(fill=tk.X)

        ttk.Label(
            conflict_frame, text="When conflicts occur during sync:", font=("Segoe UI", 10)
        ).pack(anchor=tk.W, pady=(0, 10))

        ttk.Radiobutton(
            conflict_frame, text="Ask me each time", variable=self.conflict_var, value="ask"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            conflict_frame, text="Always use local data", variable=self.conflict_var, value="local"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            conflict_frame, text="Always use MAL data", variable=self.conflict_var, value="mal"
        ).pack(anchor=tk.W)

    def _create_updates_tab(self):
        """Create Updates settings tab"""
        self.updates_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.updates_frame, text="Updates")

        # Update settings
        update_frame = ttk.LabelFrame(self.updates_frame, text="Update Checking", padding="15")
        update_frame.pack(fill=tk.X, pady=(0, 20))

        # Check for updates checkbox
        self.updates_checkbox = ttk.Checkbutton(
            update_frame,
            text="Check for updates automatically",
            variable=self.check_updates_var,
            command=self._on_update_check_toggle,
        )
        self.updates_checkbox.pack(anchor=tk.W)

        # Info about update frequency
        ttk.Label(
            update_frame,
            text="Checks once per week on startup",
            foreground="gray",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, padx=(22, 0), pady=(5, 10))

        # Show dialog option
        self.dialog_checkbox = ttk.Checkbutton(
            update_frame,
            text="Show detailed dialog when update is found",
            variable=self.show_update_dialog_var,
            state="normal" if self.check_updates_var.get() else "disabled",
        )
        self.dialog_checkbox.pack(anchor=tk.W, padx=(22, 0), pady=5)

        # Privacy notice
        privacy_frame = ttk.LabelFrame(self.updates_frame, text="Privacy Notice", padding="15")
        privacy_frame.pack(fill=tk.X)

        privacy_text = (
            "Update checking is completely private:\n\n"
            "• Only fetches public GitHub release information\n"
            "• No personal data is sent\n"
            "• No tracking or analytics\n"
            "• Can be disabled at any time\n\n"
            "This follows the Mirenku philosophy of respecting user privacy."
        )

        privacy_label = ttk.Label(
            privacy_frame,
            text=privacy_text,
            wraplength=500,
            foreground="#006600",
            font=("Segoe UI", 9),
        )
        privacy_label.pack(anchor=tk.W)

    def _on_update_check_toggle(self):
        """Handle update check toggle"""
        enabled = self.check_updates_var.get()
        self.dialog_checkbox.config(state="normal" if enabled else "disabled")

    def _refresh_protocol_status(self):
        """Refresh protocol registration status"""
        is_registered = self.protocol_manager.is_registered()

        if is_registered:
            self.protocol_status_label.config(
                text="✓ Protocol handler is registered", foreground="green"
            )

            # Show registered path
            path = self.protocol_manager.get_registered_path()
            if path:
                self.path_label.config(text=f"Location: {path}")

            # Create unregister button if needed
            if not self.unregister_button:
                if self.register_button:
                    self.register_button.destroy()
                    self.register_button = None

                actions_frame = self.test_button.master
                self.unregister_button = ttk.Button(
                    actions_frame,
                    text="Unregister Protocol",
                    command=self._on_unregister_protocol,
                    width=20,
                )
                self.unregister_button.pack(before=self.test_button, pady=5)
        else:
            self.protocol_status_label.config(
                text="✗ Protocol handler is not registered", foreground="red"
            )
            self.path_label.config(text="")

            # Create register button if needed
            if not self.register_button:
                if self.unregister_button:
                    self.unregister_button.destroy()
                    self.unregister_button = None

                actions_frame = self.test_button.master
                self.register_button = ttk.Button(
                    actions_frame,
                    text="Register Protocol",
                    command=self._on_register_protocol,
                    width=20,
                )
                self.register_button.pack(before=self.test_button, pady=5)

    def _on_register_protocol(self):
        """Handle register protocol button"""
        exe_path = sys.executable
        success = self.protocol_manager.register_protocol(exe_path)

        if success:
            self.first_run_manager.set_preference("protocol_registered", True)
            self.first_run_manager.save_app_location(exe_path)
            messagebox.showinfo(
                "Success", "Protocol handler registered successfully!", parent=self.dialog
            )
        else:
            messagebox.showerror(
                "Error",
                "Failed to register protocol handler. " "You may need administrator privileges.",
                parent=self.dialog,
            )

        self._refresh_protocol_status()

    def _on_unregister_protocol(self):
        """Handle unregister protocol button"""
        if not messagebox.askyesno(
            "Confirm",
            "Are you sure you want to unregister the protocol handler?\n\n"
            "This will prevent OAuth authentication from working.",
            parent=self.dialog,
        ):
            return

        success = self.protocol_manager.unregister_protocol()

        if success:
            self.first_run_manager.set_preference("protocol_registered", False)
            messagebox.showinfo(
                "Success", "Protocol handler unregistered successfully.", parent=self.dialog
            )
        else:
            messagebox.showerror(
                "Error", "Failed to unregister protocol handler.", parent=self.dialog
            )

        self._refresh_protocol_status()

    def _on_test_protocol(self):
        """Handle test protocol button"""
        test_url = "mirenku://test?message=Protocol_handler_is_working"
        webbrowser.open(test_url)

        messagebox.showinfo(
            "Test Protocol",
            "A test URL has been opened. If the protocol is registered correctly, "
            "Mirenku should handle the URL.\n\n"
            "If nothing happens or your browser shows an error, the protocol "
            "may not be registered.",
            parent=self.dialog,
        )

    def _on_auto_sync_toggle(self):
        """Handle auto-sync toggle"""
        state = "normal" if self.auto_sync_var.get() else "readonly"
        self.interval_spinbox.config(state=state)

    def _create_scrobbling_tab(self):
        """Create Scrobbling settings tab"""
        self.scrobbling_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.scrobbling_frame, text="Scrobbling")

        # Scrobbling settings frame
        settings_frame = ttk.LabelFrame(
            self.scrobbling_frame, text="WebSocket Server Settings", padding="15"
        )
        settings_frame.pack(fill=tk.X, pady=(0, 20))

        # Enable/disable checkbox
        self.scrobbling_checkbox = ttk.Checkbutton(
            settings_frame,
            text="Enable scrobbling server for browser extensions",
            variable=self.scrobbling_enabled_var,
            command=self._on_scrobbling_toggle,
        )
        self.scrobbling_checkbox.pack(anchor=tk.W)

        # Port configuration
        port_frame = ttk.Frame(settings_frame)
        port_frame.pack(anchor=tk.W, pady=(10, 0))

        ttk.Label(port_frame, text="Server port:").pack(side=tk.LEFT)

        self.scrobbling_port_entry = ttk.Entry(
            port_frame, textvariable=self.scrobbling_port_var, width=10
        )
        self.scrobbling_port_entry.pack(side=tk.LEFT, padx=(10, 5))
        self.scrobbling_port_entry.bind("<FocusOut>", lambda e: self._on_port_change())

        ttk.Label(port_frame, text="(default: 7834)").pack(side=tk.LEFT)

        # Status frame
        status_frame = ttk.LabelFrame(self.scrobbling_frame, text="Server Status", padding="15")
        status_frame.pack(fill=tk.X, pady=(0, 20))

        # Status label
        self.scrobbling_status_label = ttk.Label(
            status_frame, text="Checking status...", font=("Segoe UI", 10)
        )
        self.scrobbling_status_label.pack(anchor=tk.W)

        # Info frame
        info_frame = ttk.LabelFrame(self.scrobbling_frame, text="Information", padding="15")
        info_frame.pack(fill=tk.X)

        info_text = (
            "The scrobbling server allows browser extensions to communicate with Mirenku.\n\n"
            "• Runs a WebSocket server on localhost\n"
            "• Accepts connections from browser extensions\n"
            "• Automatically tracks anime watching progress\n"
            "• No external connections - fully private\n\n"
            "Install the Mirenku browser extension to start auto-scrobbling!"
        )

        info_label = ttk.Label(
            info_frame,
            text=info_text,
            wraplength=500,
            foreground="gray",
            font=("Segoe UI", 9),
        )
        info_label.pack(anchor=tk.W)

        # Update initial status
        self._update_scrobbling_status()
        self._update_scrobbling_ui_state()

    def _on_scrobbling_toggle(self):
        """Handle scrobbling enable/disable toggle"""
        if self.scrobbling_enabled_var.get():
            # Enable scrobbling
            success = self.scrobbling_manager.enable()
            if not success:
                self.scrobbling_enabled_var.set(False)
                messagebox.showerror(
                    "Error",
                    "Failed to start scrobbling server. "
                    "The port may be in use or another error occurred.",
                    parent=self.dialog,
                )
        else:
            # Disable scrobbling
            self.scrobbling_manager.disable()

        self._update_scrobbling_status()
        self._update_scrobbling_ui_state()

    def _on_port_change(self):
        """Handle port change"""
        try:
            port = int(self.scrobbling_port_var.get())
            if self._validate_port(str(port)):
                success = self.scrobbling_manager.set_port(port)
                if not success:
                    # Revert to current port if change failed
                    self.scrobbling_port_var.set(str(self.scrobbling_manager.port))
                    messagebox.showerror(
                        "Error",
                        f"Failed to change port to {port}.",
                        parent=self.dialog,
                    )
                else:
                    self._update_scrobbling_status()
            else:
                # Invalid port, revert
                self.scrobbling_port_var.set(str(self.scrobbling_manager.port))
                messagebox.showerror(
                    "Invalid Port",
                    "Port must be between 1024 and 65535.",
                    parent=self.dialog,
                )
        except ValueError:
            # Non-numeric input, revert
            self.scrobbling_port_var.set(str(self.scrobbling_manager.port))
            messagebox.showerror(
                "Invalid Port",
                "Please enter a valid port number.",
                parent=self.dialog,
            )

    def _validate_port(self, port_str):
        """Validate port number"""
        try:
            port = int(port_str)
            return 1024 <= port <= 65535
        except ValueError:
            return False

    def _update_scrobbling_status(self):
        """Update scrobbling server status display"""
        if not self.scrobbling_manager:
            return

        status = self.scrobbling_manager.get_status()

        if status["running"]:
            clients = status["clients"]
            sessions = status["sessions"]
            client_text = f"{clients} client{'s' if clients != 1 else ''}"
            session_text = f"{sessions} session{'s' if sessions != 1 else ''}"
            self.scrobbling_status_label.config(
                text=f"✓ Running on port {status['port']} - {client_text}, {session_text}",
                foreground="green",
            )
        elif status["enabled"]:
            self.scrobbling_status_label.config(
                text=f"⚠ Enabled but not running on port {status['port']}",
                foreground="orange",
            )
        else:
            self.scrobbling_status_label.config(text="✗ Disabled", foreground="red")

    def _update_scrobbling_ui_state(self):
        """Update UI state based on server status"""
        if not self.scrobbling_manager:
            return

        # Disable port entry when server is running
        if self.scrobbling_manager.is_running():
            self.scrobbling_port_entry.config(state="disabled")
        else:
            self.scrobbling_port_entry.config(state="normal")

    def _configure_styles(self):
        """Configure custom styles"""
        style = ttk.Style()

        # Accent button style
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

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

    def _save_settings(self):
        """Save settings method for testing compatibility"""
        self._on_save()

    def _on_save(self):
        """Handle Save button"""
        # Save all preferences
        self.first_run_manager.set_preference("auto_reregister", self.auto_reregister_var.get())
        self.first_run_manager.set_preference("theme", self.theme_var.get())
        self.first_run_manager.set_preference("auto_sync", self.auto_sync_var.get())
        self.first_run_manager.set_preference("sync_interval", self.sync_interval_var.get())
        self.first_run_manager.set_preference("conflict_resolution", self.conflict_var.get())

        # Save update preferences if config available
        if self.config:
            self.config.set("check_for_updates", self.check_updates_var.get())
            self.config.set("show_update_dialog", self.show_update_dialog_var.get())

            # Save scrobbling settings if manager is available
            if self.scrobbling_manager:
                scrobbling_config = {
                    "enabled": self.scrobbling_enabled_var.get(),
                    "port": int(self.scrobbling_port_var.get())
                }
                self.config.set("scrobbling", scrobbling_config)

            self.config.save()

        logger.info("Settings saved")

        self.result = True  # Changed from "save" to True for compatibility
        self.dialog.destroy()

    def _on_cancel(self):
        """Handle Cancel button"""
        self.result = "cancel"
        self.dialog.destroy()


def show_settings_dialog(parent) -> Optional[str]:
    """
    Show the settings dialog

    Args:
        parent: Parent window

    Returns:
        Dialog result ("save" or "cancel")
    """
    dialog = SettingsDialog(parent)
    parent.wait_window(dialog.dialog)
    return dialog.result
