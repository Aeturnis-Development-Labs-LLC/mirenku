"""Main window for Anime Tracker application"""

import tkinter as tk
from tkinter import ttk, messagebox, Menu
from typing import Optional, List
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import Database
from models.anime import Anime
from services.anime_service import AnimeService
from ui.dialogs import AddAnimeDialog, EditAnimeDialog
from ui.widgets import AnimeListView, SearchBar, StatusBar
from utils.config import Config
from utils.persistence import PersistenceManager
from utils.notifications import NotificationManager, NotificationLevel, ErrorHandler, setup_global_exception_handler

logger = logging.getLogger(__name__)


class MainWindow:
    """Main application window"""
    
    def __init__(self, root: tk.Tk, database: Database):
        """Initialize main window
        
        Args:
            root: Tkinter root window
            database: Database instance
        """
        self.root = root
        self.db = database
        self.service = AnimeService(database)
        self.config = Config()
        self.persistence = PersistenceManager(self.config, database)
        
        # Set up notification system
        self.notifications = NotificationManager(root)
        self.error_handler = ErrorHandler(self.notifications)
        setup_global_exception_handler(self.error_handler)
        
        # Load window state
        window_state = self.persistence.load_window_state()
        
        # Window configuration
        self.root.title("Anime Tracker v0.1.0")
        self.root.geometry(window_state["geometry"])
        self.root.minsize(800, 500)
        
        # Variables
        self.current_filter = tk.StringVar(value=window_state["filter"])
        self.search_var = tk.StringVar()
        
        # Setup UI
        self._create_menu()
        self._create_toolbar()
        self._create_main_content()
        self._create_status_bar()
        
        # Bind events
        self._bind_events()
        
        # Load initial data
        self.refresh_list()
        
        # Configure window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add Anime", command=self.add_anime, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Import...", command=self.import_data)
        file_menu.add_command(label="Export...", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Create Backup", command=self.create_backup)
        file_menu.add_command(label="Restore Backup...", command=self.restore_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Alt+F4")
        
        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Edit Selected", command=self.edit_selected, accelerator="Ctrl+E")
        edit_menu.add_command(label="Delete Selected", command=self.delete_selected, accelerator="Delete")
        edit_menu.add_separator()
        edit_menu.add_command(label="Mark as Completed", command=self.mark_completed)
        edit_menu.add_command(label="Increment Episode", command=self.increment_episode, accelerator="+")
        edit_menu.add_command(label="Decrement Episode", command=self.decrement_episode, accelerator="-")
        
        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_list, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="Statistics", command=self.show_statistics)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Add button
        self.add_btn = ttk.Button(
            toolbar,
            text="➕ Add Anime",
            command=self.add_anime
        )
        self.add_btn.pack(side=tk.LEFT, padx=2)
        
        # Search bar
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=30
        )
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        # Filter dropdown
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.current_filter,
            values=["All"] + Anime.STATUS_OPTIONS,
            state="readonly",
            width=15
        )
        self.filter_combo.pack(side=tk.LEFT)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())
    
    def _create_main_content(self):
        """Create main content area"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for anime list
        self.tree = ttk.Treeview(
            main_frame,
            columns=("title", "progress", "status", "score"),
            show="tree headings",
            selectmode="browse"
        )
        
        # Configure columns
        self.tree.heading("#0", text="ID")
        self.tree.heading("title", text="Title")
        self.tree.heading("progress", text="Progress")
        self.tree.heading("status", text="Status")
        self.tree.heading("score", text="Score")
        
        # Column widths
        self.tree.column("#0", width=50, stretch=False)
        self.tree.column("title", width=400)
        self.tree.column("progress", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("score", width=80, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right-click context menu
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Edit", command=self.edit_selected)
        self.context_menu.add_command(label="Delete", command=self.delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Mark as Completed", command=self.mark_completed)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Increment Episode", command=self.increment_episode)
        self.context_menu.add_command(label="Decrement Episode", command=self.decrement_episode)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            self.status_bar,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
        
        self.count_label = ttk.Label(
            self.status_bar,
            text="0 anime",
            relief=tk.SUNKEN,
            anchor=tk.E
        )
        self.count_label.pack(side=tk.RIGHT, padx=5, pady=2)
    
    def _bind_events(self):
        """Bind keyboard and mouse events"""
        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.add_anime())
        self.root.bind("<Control-e>", lambda e: self.edit_selected())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<F5>", lambda e: self.refresh_list())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus())
        
        # Plus/Minus for episodes
        self.root.bind("<plus>", lambda e: self.increment_episode())
        self.root.bind("<KP_Add>", lambda e: self.increment_episode())
        self.root.bind("<minus>", lambda e: self.decrement_episode())
        self.root.bind("<KP_Subtract>", lambda e: self.decrement_episode())
        
        # Tree events
        self.tree.bind("<Double-Button-1>", lambda e: self.edit_selected())
        self.tree.bind("<Button-3>", self.show_context_menu)  # Right-click
        
        # Search events
        self.search_var.trace("w", lambda *args: self.apply_filter())
    
    def refresh_list(self):
        """Refresh anime list"""
        try:
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Get filtered anime
            filter_status = None if self.current_filter.get() == "All" else self.current_filter.get()
            search_term = self.search_var.get()
            
            anime_list = self.service.filter_anime(
                status=filter_status,
                search=search_term if search_term else None
            )
            
            # Populate tree
            for anime in anime_list:
                score_display = str(anime.score) if anime.score else "-"
                
                self.tree.insert(
                    "",
                    tk.END,
                    text=str(anime.id),
                    values=(
                        anime.title,
                        anime.display_progress,
                        anime.status,
                        score_display
                    )
                )
            
            # Update status bar
            self.update_status_bar(len(anime_list))
            
        except Exception as e:
            self.error_handler.handle_error(e, "Failed to refresh list")
    
    def apply_filter(self):
        """Apply current filter and search"""
        self.refresh_list()
    
    def add_anime(self):
        """Show add anime dialog"""
        from ui.dialogs import AddAnimeDialog
        
        dialog = AddAnimeDialog(self.root, self.service)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_list()
            self.set_status(f"Added: {dialog.result}")
            self.notifications.show(
                f"Successfully added '{dialog.result}'",
                NotificationLevel.SUCCESS
            )
    
    def edit_selected(self):
        """Edit selected anime"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an anime to edit")
            return
        
        # Get anime ID from tree
        item = self.tree.item(selection[0])
        anime_id = int(item['text'])
        
        # Get anime data
        anime = self.service.get_anime(anime_id)
        if not anime:
            messagebox.showerror("Error", "Could not load anime data")
            return
        
        from ui.dialogs import EditAnimeDialog
        
        dialog = EditAnimeDialog(self.root, self.service, anime)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_list()
            self.set_status(f"Updated: {anime.title}")
            self.notifications.show(
                f"Updated '{anime.title}'",
                NotificationLevel.SUCCESS
            )
    
    def delete_selected(self):
        """Delete selected anime"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an anime to delete")
            return
        
        # Get anime info
        item = self.tree.item(selection[0])
        anime_id = int(item['text'])
        title = item['values'][0]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Delete '{title}'?"):
            success, message = self.service.delete_anime(anime_id)
            
            if success:
                self.refresh_list()
                self.set_status(message)
                self.notifications.show(f"Deleted '{title}'", NotificationLevel.SUCCESS)
            else:
                self.error_handler.handle_error(Exception(message), "Delete failed")
    
    def mark_completed(self):
        """Mark selected anime as completed"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        anime_id = int(item['text'])
        
        success, message = self.service.mark_completed(anime_id)
        
        if success:
            self.refresh_list()
            self.set_status(message)
        else:
            messagebox.showerror("Error", message)
    
    def increment_episode(self):
        """Increment episode for selected anime"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        anime_id = int(item['text'])
        
        success, message = self.service.increment_episode(anime_id)
        
        if success:
            self.refresh_list()
            self.set_status(message)
    
    def decrement_episode(self):
        """Decrement episode for selected anime"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        anime_id = int(item['text'])
        
        success, message = self.service.decrement_episode(anime_id)
        
        if success:
            self.refresh_list()
            self.set_status(message)
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def import_data(self):
        """Import anime data"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Import Anime Data",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        file_path = Path(file_path)
        
        # Determine file type and import
        if file_path.suffix.lower() == '.json':
            imported, failed, errors = self.persistence.import_from_json(file_path)
        elif file_path.suffix.lower() == '.csv':
            imported, failed, errors = self.persistence.import_from_csv(file_path)
        else:
            messagebox.showerror("Error", "Unsupported file format")
            return
        
        # Show results
        if imported > 0:
            self.refresh_list()
            message = f"Successfully imported {imported} anime"
            if failed > 0:
                message += f"\n{failed} failed to import"
                if errors:
                    message += f"\n\nErrors:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Import Complete", message)
        else:
            message = f"No anime imported. {failed} failed."
            if errors:
                message += f"\n\nErrors:\n" + "\n".join(errors[:5])
            messagebox.showerror("Import Failed", message)
    
    def export_data(self):
        """Export anime data"""
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="Export Anime Data",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        file_path = Path(file_path)
        
        # Determine file type and export
        if file_path.suffix.lower() == '.json':
            success = self.persistence.export_to_json(file_path)
        elif file_path.suffix.lower() == '.csv':
            success = self.persistence.export_to_csv(file_path)
        else:
            messagebox.showerror("Error", "Unsupported file format")
            return
        
        if success:
            messagebox.showinfo("Export Complete", f"Data exported to:\n{file_path}")
        else:
            messagebox.showerror("Export Failed", "Failed to export data")
    
    def show_statistics(self):
        """Show statistics dialog"""
        stats = self.service.get_statistics()
        
        message = f"""Anime Statistics:
        
Total Anime: {stats.get('total', 0)}
Currently Watching: {stats.get('currently_watching', 0)}
Completed: {stats.get('by_status', {}).get('Completed', 0)}
Completion Rate: {stats.get('completion_rate', 0)}%

Total Episodes Watched: {stats.get('total_episodes_watched', 0)}
Total Watch Time: {stats.get('total_watch_time_hours', 0)} hours
Average Score: {stats.get('average_score', 0)}

Added This Week: {stats.get('added_this_week', 0)}"""
        
        messagebox.showinfo("Statistics", message)
    
    def create_backup(self):
        """Create database backup"""
        backup_path = self.persistence.create_backup()
        
        if backup_path:
            messagebox.showinfo("Backup Created", f"Backup saved to:\n{backup_path}")
        else:
            messagebox.showerror("Backup Failed", "Failed to create backup")
    
    def restore_backup(self):
        """Restore from backup"""
        # Get list of backups
        backups = self.persistence.get_backup_list()
        
        if not backups:
            messagebox.showinfo("No Backups", "No backup files found")
            return
        
        # Create selection dialog
        from tkinter import simpledialog
        
        backup_names = [f"{b['name']} ({b['size_mb']} MB) - {b['created'].strftime('%Y-%m-%d %H:%M')}" 
                       for b in backups]
        
        # Simple selection using messagebox
        if len(backups) == 1:
            if messagebox.askyesno("Restore Backup", 
                                  f"Restore from:\n{backup_names[0]}?\n\nThis will replace current data!"):
                backup_file = backups[0]['path']
            else:
                return
        else:
            # For multiple backups, use the most recent one with confirmation
            if messagebox.askyesno("Restore Backup", 
                                  f"Restore from most recent backup:\n{backup_names[0]}?\n\nThis will replace current data!"):
                backup_file = backups[0]['path']
            else:
                return
        
        # Restore
        if self.persistence.restore_from_backup(backup_file):
            self.refresh_list()
            messagebox.showinfo("Restore Complete", "Database restored successfully")
        else:
            messagebox.showerror("Restore Failed", "Failed to restore from backup")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Anime Tracker v0.1.0
        
A desktop application for tracking anime viewing progress.

Created by Aeturnis Development Labs LLC
https://github.com/Aeturnis-Development-Labs-LLC/anime-tracker

© 2025 Aeturnis Development Labs LLC
Licensed under MIT License"""
        
        messagebox.showinfo("About Anime Tracker", about_text)
    
    def set_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)
    
    def update_status_bar(self, count: int):
        """Update status bar counts"""
        anime_text = "anime" if count == 1 else "anime"
        self.count_label.config(text=f"{count} {anime_text}")
        
        # Get status breakdown
        stats = self.service.get_statistics()
        watching = stats.get('currently_watching', 0)
        completed = stats.get('by_status', {}).get('Completed', 0)
        
        if watching > 0 or completed > 0:
            status_text = f"Total: {count}"
            if watching > 0:
                status_text += f" | Watching: {watching}"
            if completed > 0:
                status_text += f" | Completed: {completed}"
            self.set_status(status_text)
    
    def on_closing(self):
        """Handle window closing"""
        # Save window state
        self.persistence.save_window_state(
            geometry=self.root.geometry(),
            filter_status=self.current_filter.get()
        )
        
        # Stop auto-save
        self.persistence.stop_auto_save_thread()
        
        # Final backup
        self.persistence.create_backup()
        
        # Disconnect database
        self.db.disconnect()
        self.root.destroy()