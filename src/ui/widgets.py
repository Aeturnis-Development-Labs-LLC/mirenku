"""Custom widgets for Anime Tracker"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class AnimeListView(ttk.Treeview):
    """Custom treeview for anime list display"""

    def __init__(self, parent, **kwargs):
        """Initialize anime list view

        Args:
            parent: Parent widget
            **kwargs: Additional treeview options
        """
        super().__init__(parent, **kwargs)

        # Configure for anime display
        self.configure(
            columns=("title", "progress", "status", "score"),
            show="tree headings",
            selectmode="browse",
        )

        # Setup columns
        self._setup_columns()

    def _setup_columns(self):
        """Configure column headings and widths"""
        self.heading("#0", text="ID")
        self.heading("title", text="Title")
        self.heading("progress", text="Progress")
        self.heading("status", text="Status")
        self.heading("score", text="Score")

        self.column("#0", width=50, stretch=False)
        self.column("title", width=400)
        self.column("progress", width=100, anchor="center")
        self.column("status", width=120, anchor="center")
        self.column("score", width=80, anchor="center")


class SearchBar(ttk.Frame):
    """Search bar widget"""

    def __init__(self, parent, search_callback: Optional[Callable] = None):
        """Initialize search bar

        Args:
            parent: Parent widget
            search_callback: Function to call on search
        """
        super().__init__(parent)

        self.search_callback = search_callback
        self.search_var = tk.StringVar()

        # Create widgets
        self._create_widgets()

        # Bind events
        if search_callback:
            self.search_var.trace("w", lambda *args: self.search_callback(self.search_var.get()))

    def _create_widgets(self):
        """Create search bar widgets"""
        ttk.Label(self, text="🔍").pack(side=tk.LEFT, padx=5)

        self.entry = ttk.Entry(self, textvariable=self.search_var, width=30)
        self.entry.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(self, text="✕", width=3, command=self.clear)
        self.clear_btn.pack(side=tk.LEFT)

    def clear(self):
        """Clear search field"""
        self.search_var.set("")
        self.entry.focus()

    def get_search_text(self) -> str:
        """Get current search text

        Returns:
            str: Search text
        """
        return self.search_var.get()


class StatusBar(ttk.Frame):
    """Status bar widget"""

    def __init__(self, parent):
        """Initialize status bar

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Status message
        self.status_label = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)

        # Count label
        self.count_label = ttk.Label(self, text="0 anime", relief=tk.SUNKEN, anchor=tk.E)
        self.count_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def set_status(self, message: str):
        """Set status message

        Args:
            message: Status message
        """
        self.status_label.config(text=message)

    def set_count(self, count: int):
        """Set anime count

        Args:
            count: Number of anime
        """
        text = f"{count} anime" if count != 1 else "1 anime"
        self.count_label.config(text=text)

    def update(self, message: str = None, count: int = None):
        """Update status bar

        Args:
            message: Optional status message
            count: Optional anime count
        """
        if message is not None:
            self.set_status(message)
        if count is not None:
            self.set_count(count)
