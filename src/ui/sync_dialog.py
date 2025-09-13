"""Sync dialog for choosing sync operations"""

import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class SyncDialog:
    """Dialog for choosing sync operation"""

    def __init__(self, parent, sync_service):
        """Initialize sync dialog

        Args:
            parent: Parent window
            sync_service: SyncService instance
        """
        self.parent = parent
        self.sync_service = sync_service
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sync with MyAnimeList")
        self.dialog.geometry("450x350")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 175
        self.dialog.geometry(f"450x350+{x}+{y}")

        self.create_widgets()

        # Bind escape key
        self.dialog.bind("<Escape>", lambda e: self.cancel())

    def create_widgets(self):
        """Create dialog widgets"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            main_frame, text="Choose Sync Operation", font=("TkDefaultFont", 12, "bold")
        )
        title_label.pack(pady=(0, 20))

        # Get sync statistics
        stats = self.sync_service.get_sync_statistics()
        queue_count = stats.get("queue_pending", 0)

        # Sync options frame
        options_frame = ttk.LabelFrame(main_frame, text="Sync Options", padding="15")
        options_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Push option
        push_frame = ttk.Frame(options_frame)
        push_frame.pack(fill="x", pady=(0, 15))

        ttk.Button(
            push_frame, text="Push to MAL →", command=lambda: self.select_sync("push"), width=20
        ).pack(side="left", padx=(0, 10))

        push_label = ttk.Label(
            push_frame,
            text=f"Upload local changes to MAL\n({queue_count} pending operations)",
            font=("TkDefaultFont", 9),
        )
        push_label.pack(side="left")

        # Pull option
        pull_frame = ttk.Frame(options_frame)
        pull_frame.pack(fill="x", pady=(0, 15))

        ttk.Button(
            pull_frame, text="← Pull from MAL", command=lambda: self.select_sync("pull"), width=20
        ).pack(side="left", padx=(0, 10))

        ttk.Label(
            pull_frame,
            text="Download your MAL list\n(Updates local data)",
            font=("TkDefaultFont", 9),
        ).pack(side="left")

        # Full sync option
        full_frame = ttk.Frame(options_frame)
        full_frame.pack(fill="x")

        ttk.Button(
            full_frame, text="↔ Full Sync", command=lambda: self.select_sync("full"), width=20
        ).pack(side="left", padx=(0, 10))

        ttk.Label(
            full_frame, text="Bidirectional sync\n(Push then pull)", font=("TkDefaultFont", 9)
        ).pack(side="left")

        # Status info
        info_frame = ttk.LabelFrame(main_frame, text="Sync Status", padding="10")
        info_frame.pack(fill="x", pady=(0, 20))

        status_text = []

        if stats.get("authenticated"):
            status_text.append("✓ Authenticated with MAL")
        else:
            status_text.append("✗ Not authenticated")

        if stats.get("last_sync"):
            status_text.append(f"Last sync: {stats['last_sync']}")
        else:
            status_text.append("Never synced")

        total_synced = stats.get("total_synced", 0)
        conflicts = stats.get("conflicts", 0)

        status_text.append(f"Synced items: {total_synced}")
        if conflicts > 0:
            status_text.append(f"Conflicts: {conflicts}")

        ttk.Label(
            info_frame, text="\n".join(status_text), font=("TkDefaultFont", 9), justify="left"
        ).pack()

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right")

    def select_sync(self, sync_type: str):
        """Select sync type and close dialog

        Args:
            sync_type: Type of sync (push, pull, full)
        """
        self.result = {"type": sync_type}
        self.dialog.destroy()

    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.dialog.destroy()
