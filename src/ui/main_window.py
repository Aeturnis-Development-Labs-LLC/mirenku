"""Main window for Mirenku application"""

import logging
import sys
import tkinter as tk
from pathlib import Path
from tkinter import Menu, messagebox, ttk

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.anime import Anime
from models.database import Database
from services.anime_service import AnimeService
from ui.dialogs import AddAnimeDialog, EditAnimeDialog
from utils.config import Config
from utils.database_watcher import SmartDatabaseWatcher
from utils.notifications import (
    ErrorHandler,
    NotificationLevel,
    NotificationManager,
    setup_global_exception_handler,
)
from utils.persistence import PersistenceManager

# Try to import version
try:
    from __init__ import __version__
except ImportError:
    __version__ = "unknown"

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

        # Set up MAL service
        from services.mal_service import MALService

        cache_dir = self.config.get_data_directory() / "mal_cache"
        self.mal_service = MALService(cache_dir)

        # Set up image service
        from services.image_service import ImageService

        image_cache_dir = self.config.get_data_directory() / "image_cache"
        self.image_service = ImageService(image_cache_dir)

        # Set up MAL OAuth2 authentication (Phase 3)
        from ui.mal_auth_dialog import MALAuthManager

        self.mal_auth_manager = MALAuthManager(
            self.config.get_data_directory()
            # Client ID is embedded in the application
        )

        # Set up ScrobblingManager for WebSocket server (v0.4.0)
        try:
            from services.scrobbling_manager import ScrobblingManager
            self.scrobbling_manager = ScrobblingManager(self.service, self.config)
            # Start server if enabled
            self.scrobbling_manager.start()
        except Exception as e:
            logger.warning(f"Failed to initialize ScrobblingManager: {e}")
            self.scrobbling_manager = None

        # Set up MAL API v2 service if authenticated (silent check at startup)
        self.mal_api_v2_service = None
        if self.mal_auth_manager.is_authenticated(silent=True):
            from services.mal_api_v2_service import MALAPIv2Service

            self.mal_api_v2_service = MALAPIv2Service(self.mal_auth_manager.oauth_client)

        # Set up sync service (Phase 3 functionality)
        from services.sync_service import SyncService

        self.sync_service = SyncService(
            database,
            self.mal_api_v2_service,
            self.mal_auth_manager.oauth_client
            if hasattr(self.mal_auth_manager, "oauth_client")
            else None,
        )

        # Set up notification system
        self.notifications = NotificationManager(root)
        self.error_handler = ErrorHandler(self.notifications)
        setup_global_exception_handler(self.error_handler)

        # Set up database watcher for auto-refresh
        db_path = self.config.get_db_path()
        self.db_watcher = SmartDatabaseWatcher(
            db_path=db_path,
            callback=self._on_database_change,
            debounce_ms=300,  # 300ms debounce to prevent excessive updates
        )
        self.auto_refresh_enabled = True
        self.manual_operation = False  # Flag to prevent self-triggering

        # Load window state
        window_state = self.persistence.load_window_state()

        # Initialize version checker (opt-in)
        self.check_for_updates_enabled = self.config.get("check_for_updates", False)
        self.last_update_check = self.config.get("last_update_check", None)
        self.version_checker = None  # Will be initialized if enabled

        # Window configuration
        try:
            from __init__ import __version__

            self.root.title(f"Mirenku v{__version__}")
        except ImportError:
            self.root.title("Mirenku")

        self.root.geometry(window_state["geometry"])
        self.root.minsize(800, 500)

        # Variables
        self.current_filter = tk.StringVar(value=window_state["filter"])
        self.search_var = tk.StringVar()

        # Configure styles with Mirenku colors and fonts
        style = ttk.Style()

        # Define Mirenku color palette
        MIRENKU_TEAL = "#2dd4bf"
        MIRENKU_TEAL_LIGHT = "#e6fffa"
        MIRENKU_TEAL_DARK = "#0d9488"

        # Define Mirenku fonts - clean, straightforward, no gimmicks
        import platform

        system = platform.system()

        if system == "Windows":
            # Windows: Use Segoe UI for UI, Consolas for data
            UI_FONT = ("Segoe UI", 9)
            UI_FONT_BOLD = ("Segoe UI", 9, "bold")
            DATA_FONT = ("Consolas", 9)
            HEADING_FONT = ("Segoe UI", 10, "bold")
        elif system == "Darwin":  # macOS
            UI_FONT = ("SF Pro Text", 9)
            UI_FONT_BOLD = ("SF Pro Text", 9, "bold")
            DATA_FONT = ("SF Mono", 9)
            HEADING_FONT = ("SF Pro Display", 10, "bold")
        else:  # Linux and others
            UI_FONT = ("Noto Sans", 9)
            UI_FONT_BOLD = ("Noto Sans", 9, "bold")
            DATA_FONT = ("Roboto Mono", 9)
            HEADING_FONT = ("Noto Sans", 10, "bold")

        # Apply fonts to default widgets
        self.root.option_add("*Font", UI_FONT)
        self.root.option_add("*Menu.Font", UI_FONT)
        self.root.option_add("*Menubutton.Font", UI_FONT)

        # Configure button styles
        style.configure(
            "TButton", font=UI_FONT, borderwidth=1, relief="flat", background=MIRENKU_TEAL_LIGHT
        )
        style.map("TButton", background=[("active", MIRENKU_TEAL), ("pressed", MIRENKU_TEAL_DARK)])

        # Configure frame styles
        style.configure("TFrame", background="white")
        style.configure("TLabelFrame", background="white", font=UI_FONT_BOLD)

        # Configure label styles
        style.configure("TLabel", background="white", font=UI_FONT)
        style.configure("Heading.TLabel", font=HEADING_FONT)

        # Configure entry styles
        style.configure("TEntry", font=UI_FONT)

        # Configure combobox styles
        style.configure("TCombobox", font=UI_FONT)

        # Store fonts for later use
        self.fonts = {
            "ui": UI_FONT,
            "ui_bold": UI_FONT_BOLD,
            "data": DATA_FONT,
            "heading": HEADING_FONT,
        }

        # Setup UI
        self._create_menu()
        self._create_toolbar()
        self._create_main_content()
        self._create_status_bar()

        # Bind events
        self._bind_events()

        # Load initial data
        self.refresh_list()

        # Start database watcher for auto-refresh
        self.db_watcher.start()
        logger.info("Auto-refresh enabled - UI will update automatically")

        # Start MAL status updates
        self.root.after(1000, self.update_mal_status)

        # Check for updates on startup (if enabled)
        if self.check_for_updates_enabled:
            self.root.after(2000, self.check_for_updates_on_startup)

        # Configure window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_menu(self):
        """Create menu bar"""
        menubar = Menu(self.root, font=self.fonts["ui"])
        self.root.config(menu=menubar)

        # File menu
        file_menu = Menu(menubar, tearoff=0, font=self.fonts["ui"])
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add Anime", command=self.add_anime, accelerator="Ctrl+N")
        file_menu.add_command(label="Search MAL...", command=self.search_mal, accelerator="Ctrl+M")
        file_menu.add_separator()
        file_menu.add_command(
            label="Import from File...", command=self.import_data, accelerator="Ctrl+I"
        )
        file_menu.add_command(label="Import from MAL User...", command=self.import_mal_user)
        file_menu.add_command(label="Export...", command=self.export_data, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Create Backup", command=self.create_backup)
        file_menu.add_command(label="Restore Backup...", command=self.restore_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Alt+F4")

        # Edit menu
        edit_menu = Menu(menubar, tearoff=0, font=self.fonts["ui"])
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="View Details", command=self.view_details)
        edit_menu.add_command(
            label="Edit Selected", command=self.edit_selected, accelerator="Ctrl+E"
        )
        edit_menu.add_command(
            label="Delete Selected", command=self.delete_selected, accelerator="Delete"
        )
        edit_menu.add_separator()
        edit_menu.add_command(label="Mark as Completed", command=self.mark_completed)
        edit_menu.add_command(
            label="Increment Episode", command=self.increment_episode, accelerator="+"
        )
        edit_menu.add_command(
            label="Decrement Episode", command=self.decrement_episode, accelerator="-"
        )

        # View menu
        view_menu = Menu(menubar, tearoff=0, font=self.fonts["ui"])
        menubar.add_cascade(label="View", menu=view_menu)

        # Track auto-refresh state
        self.auto_refresh_var = tk.BooleanVar(value=True)
        view_menu.add_command(label="Refresh", command=self.refresh_list, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Auto-refresh", command=self.toggle_auto_refresh, variable=self.auto_refresh_var
        )
        view_menu.add_separator()
        view_menu.add_command(
            label="Statistics", command=self.show_statistics, accelerator="Ctrl+T"
        )

        # Tools menu
        tools_menu = Menu(menubar, tearoff=0, font=self.fonts["ui"])
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(
            label="MAL Authentication...", command=self.show_mal_auth, accelerator="Ctrl+Shift+M"
        )
        tools_menu.add_command(
            label="Sync with MAL", command=self.sync_with_mal_v2, accelerator="Ctrl+Shift+S"
        )
        tools_menu.add_separator()
        tools_menu.add_command(label="Settings...", command=self.show_settings)

        # Help menu
        help_menu = Menu(menubar, tearoff=0, font=self.fonts["ui"])
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Check for Updates", command=self.check_for_updates_manual)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about, accelerator="F1")

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Add button
        self.add_btn = ttk.Button(toolbar, text="➕ Add Anime", command=self.add_anime)
        self.add_btn.pack(side=tk.LEFT, padx=2)

        # Search bar
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.LEFT, padx=20)

        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        # MAL toolbar section
        mal_frame = ttk.Frame(toolbar)
        mal_frame.pack(side=tk.LEFT, padx=20)

        # MAL Connect button (using tk.Button for color control)
        self.mal_connect_btn = tk.Button(
            mal_frame,
            text="🔗 Connect MAL",
            command=self.quick_mal_connect,
            font=("TkDefaultFont", 9),
            relief=tk.RAISED,
            bd=1,
            padx=8,
            pady=3,
        )
        self.mal_connect_btn.pack(side=tk.LEFT, padx=2)

        # Update button text based on auth status
        if self.mal_auth_manager.is_authenticated():
            self.mal_connect_btn.config(text="✓ MAL Connected", fg="green")

        # MAL search button
        ttk.Button(mal_frame, text="🌐 MAL Search", command=self.search_mal).pack(
            side=tk.LEFT, padx=2
        )

        # Sync button
        self.sync_button = ttk.Button(mal_frame, text="🔄 Sync", command=self.sync_with_mal_v2)
        self.sync_button.pack(side=tk.LEFT, padx=2)

        # Enable sync button if authenticated
        if self.mal_auth_manager.is_authenticated():
            self.sync_button.config(state="normal")
        else:
            self.sync_button.config(state="disabled")

        # Sync status label
        self.sync_status_label = ttk.Label(mal_frame, text="", foreground="gray")
        self.sync_status_label.pack(side=tk.LEFT, padx=5)

        # Filter dropdown
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.current_filter,
            values=["All"] + Anime.STATUS_OPTIONS,
            state="readonly",
            width=15,
        )
        self.filter_combo.pack(side=tk.LEFT)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

    def _create_main_content(self):
        """Create main content area"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure style for zebra stripes using Mirenku colors
        style = ttk.Style()
        # Mirenku teal/turquoise color
        style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
        style.map("Treeview", background=[("selected", "#2dd4bf")])  # Mirenku teal on selection

        # Create treeview for anime list (hide tree column with show="headings")
        self.tree = ttk.Treeview(
            main_frame,
            columns=("title", "progress", "status", "score", "mal"),
            show="headings",  # Hide the tree/ID column
            selectmode="browse",
        )

        # Configure tags for zebra stripes
        self.tree.tag_configure("oddrow", background="white")
        self.tree.tag_configure("evenrow", background="#e6fffa")  # Very light teal

        # Sort tracking
        self.sort_column = None
        self.sort_reverse = False

        # Configure columns with sorting
        self.tree.heading("title", text="Title", command=lambda: self._sort_column("title"))
        self.tree.heading(
            "progress", text="Progress", command=lambda: self._sort_column("progress")
        )
        self.tree.heading("status", text="Status", command=lambda: self._sort_column("status"))
        self.tree.heading("score", text="Score", command=lambda: self._sort_column("score"))
        self.tree.heading("mal", text="MAL", command=lambda: self._sort_column("mal"))

        # Column widths (redistribute ID column space to title)
        self.tree.column("title", width=400)
        self.tree.column("progress", width=100, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("score", width=80, anchor="center")
        self.tree.column("mal", width=50, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Right-click context menu
        self.context_menu = Menu(self.root, tearoff=0, font=self.fonts["ui"])
        self.context_menu.add_command(label="View Details", command=self.view_details)
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

        self.status_label = ttk.Label(self.status_bar, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)

        # MAL connection indicator
        self.mal_status_label = ttk.Label(
            self.status_bar, text="MAL: ✗", relief=tk.SUNKEN, anchor=tk.CENTER, foreground="red"
        )
        self.mal_status_label.pack(side=tk.LEFT, padx=5, pady=2)

        # Sync queue indicator
        self.sync_queue_label = ttk.Label(
            self.status_bar, text="Queue: 0", relief=tk.SUNKEN, anchor=tk.CENTER
        )
        self.sync_queue_label.pack(side=tk.LEFT, padx=5, pady=2)

        self.count_label = ttk.Label(self.status_bar, text="0 anime", relief=tk.SUNKEN, anchor=tk.E)
        self.count_label.pack(side=tk.RIGHT, padx=5, pady=2)

    def _bind_events(self):
        """Bind keyboard and mouse events"""
        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.add_anime())
        self.root.bind("<Control-e>", lambda e: self.edit_selected())
        self.root.bind("<Control-m>", lambda e: self.search_mal())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<F5>", lambda e: self.refresh_list())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus())
        self.root.bind("<Control-i>", lambda e: self.import_data())
        self.root.bind("<Control-s>", lambda e: self.export_data())
        self.root.bind("<Control-t>", lambda e: self.show_statistics())
        self.root.bind("<F1>", lambda e: self.show_about())
        self.root.bind("<Control-Shift-M>", lambda e: self.show_mal_auth())
        self.root.bind("<Control-Shift-S>", lambda e: self.sync_with_mal_v2())

        # Plus/Minus for episodes
        self.root.bind("<plus>", lambda e: self.increment_episode())
        self.root.bind("<KP_Add>", lambda e: self.increment_episode())
        self.root.bind("<minus>", lambda e: self.decrement_episode())
        self.root.bind("<KP_Subtract>", lambda e: self.decrement_episode())

        # Tree events
        self.tree.bind("<Double-Button-1>", lambda e: self.view_details())
        self.tree.bind("<Button-3>", self.show_context_menu)  # Right-click

        # Search events
        self.search_var.trace("w", lambda *args: self.apply_filter())

    def _sort_column(self, col):
        """Handle column header click for sorting"""
        # Toggle sort direction if clicking same column
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False

        self.sort_by_column(col, self.sort_reverse)

    def sort_by_column(self, col, reverse):
        """Sort tree contents by column"""
        # Get all items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]

        # Sort items
        try:
            # Try numeric sort for progress and score
            if col == "score":
                items.sort(
                    key=lambda x: float(x[0]) if x[0] and x[0] != "-" else 0, reverse=reverse
                )
            elif col == "progress":
                # Extract current episode number from "X/Y" format
                def get_episode_num(progress_str):
                    try:
                        return int(progress_str.split("/")[0])
                    except:
                        return 0

                items.sort(key=lambda x: get_episode_num(x[0]), reverse=reverse)
            elif col == "mal":
                # Sort by presence of MAL ID
                items.sort(key=lambda x: 1 if x[0] else 0, reverse=reverse)
            else:
                # String sort for other columns
                items.sort(key=lambda x: x[0].lower() if x[0] else "", reverse=reverse)
        except Exception as e:
            # Fallback to string sort
            logging.debug(f"Sort error: {e}")
            items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)

        # Rearrange items in sorted order
        for index, (val, item) in enumerate(items):
            self.tree.move(item, "", index)
            # Reapply zebra stripes
            tag = "evenrow" if index % 2 == 0 else "oddrow"
            self.tree.item(item, tags=(tag,))

    def refresh_list(self):
        """Refresh anime list"""
        try:
            # Clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Get filtered anime
            filter_status = (
                None if self.current_filter.get() == "All" else self.current_filter.get()
            )
            search_term = self.search_var.get()

            anime_list = self.service.filter_anime(
                status=filter_status, search=search_term if search_term else None
            )

            # Populate tree with zebra stripes
            for index, anime in enumerate(anime_list):
                score_display = str(anime.score) if anime.score else "-"
                mal_display = "✓" if anime.mal_id else ""

                # Apply alternating row colors
                tag = "evenrow" if index % 2 == 0 else "oddrow"

                self.tree.insert(
                    "",
                    tk.END,
                    text=str(anime.id),
                    values=(
                        anime.title,
                        anime.display_progress,
                        anime.status,
                        score_display,
                        mal_display,
                    ),
                    tags=(tag,),
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

        # Mark manual operation
        self.db_watcher.begin_operation()

        dialog = AddAnimeDialog(self.root, self.service)
        self.root.wait_window(dialog.dialog)

        if dialog.result:
            # Manual refresh (auto-refresh will be ignored)
            self.refresh_list()
            self.set_status(f"Added: {dialog.result}")
            self.notifications.show(
                f"Successfully added '{dialog.result}'", NotificationLevel.SUCCESS
            )

        # End manual operation
        self.db_watcher.end_operation()

    def edit_selected(self):
        """Edit selected anime"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an anime to edit")
            return

        # Get anime ID from tree
        item = self.tree.item(selection[0])
        anime_id = int(item["text"])

        # Get anime data
        anime = self.service.get_anime(anime_id)
        if not anime:
            messagebox.showerror("Error", "Could not load anime data")
            return

        # Mark manual operation
        self.db_watcher.begin_operation()

        dialog = EditAnimeDialog(self.root, self.service, anime)
        self.root.wait_window(dialog.dialog)

        if dialog.result:
            self.refresh_list()
            self.set_status(f"Updated: {anime.title}")
            self.notifications.show(f"Updated '{anime.title}'", NotificationLevel.SUCCESS)

        # End manual operation
        self.db_watcher.end_operation()

    def delete_selected(self):
        """Delete selected anime"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an anime to delete")
            return

        # Get anime info
        item = self.tree.item(selection[0])
        anime_id = int(item["text"])
        title = item["values"][0]

        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Delete '{title}'?"):
            success, message = self.service.delete_anime(anime_id)

            if success:
                self.refresh_list()
                self.set_status(message)
                self.notifications.show(f"Deleted '{title}'", NotificationLevel.SUCCESS)
            else:
                self.error_handler.handle_error(Exception(message), "Delete failed")

    def view_details(self):
        """View detailed anime information"""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        anime_id = int(item["text"])

        # Get anime data
        anime = self.service.get_anime(anime_id)
        if not anime:
            return

        # Open detail dialog
        from ui.anime_detail_dialog import AnimeDetailDialog

        AnimeDetailDialog(self.root, anime, self.service, self.image_service, self.mal_service)

        # Refresh list after dialog closes
        self.refresh_list()

    def mark_completed(self):
        """Mark selected anime as completed"""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        anime_id = int(item["text"])

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
        anime_id = int(item["text"])

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
        anime_id = int(item["text"])

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
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not file_path:
            return

        file_path = Path(file_path)

        # Determine file type and import
        if file_path.suffix.lower() == ".json":
            imported, failed, errors = self.persistence.import_from_json(file_path)
        elif file_path.suffix.lower() == ".csv":
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
                    message += "\n\nErrors:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Import Complete", message)
        else:
            message = f"No anime imported. {failed} failed."
            if errors:
                message += "\n\nErrors:\n" + "\n".join(errors[:5])
            messagebox.showerror("Import Failed", message)

    def export_data(self):
        """Export anime data"""
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title="Export Anime Data",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not file_path:
            return

        file_path = Path(file_path)

        # Determine file type and export
        if file_path.suffix.lower() == ".json":
            success = self.persistence.export_to_json(file_path)
        elif file_path.suffix.lower() == ".csv":
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

        backup_names = [
            f"{b['name']} ({b['size_mb']} MB) - {b['created'].strftime('%Y-%m-%d %H:%M')}"
            for b in backups
        ]

        # Simple selection using messagebox
        if len(backups) == 1:
            if messagebox.askyesno(
                "Restore Backup",
                f"Restore from:\n{backup_names[0]}?\n\nThis will replace current data!",
            ):
                backup_file = backups[0]["path"]
            else:
                return
        # For multiple backups, use the most recent one with confirmation
        elif messagebox.askyesno(
            "Restore Backup",
            f"Restore from most recent backup:\n{backup_names[0]}?\n\nThis will replace current data!",
        ):
            backup_file = backups[0]["path"]
        else:
            return

        # Restore
        if self.persistence.restore_from_backup(backup_file):
            self.refresh_list()
            messagebox.showinfo("Restore Complete", "Database restored successfully")
        else:
            messagebox.showerror("Restore Failed", "Failed to restore from backup")

    def search_mal(self):
        """Open MAL search dialog"""
        from ui.mal_search_dialog import MALSearchDialog

        MALSearchDialog(self.root, self.mal_service, self.service, self.refresh_list)

    def import_mal_user(self):
        """Import anime list from MAL user"""
        # Simple dialog to get username
        from tkinter import simpledialog

        username = simpledialog.askstring(
            "Import from MAL User", "Enter MyAnimeList username:", parent=self.root
        )

        if not username:
            return

        # Show progress
        self.notifications.show("Importing from MAL...", level="info")

        # Import in background thread
        import threading

        thread = threading.Thread(target=self._import_mal_user_thread, args=(username,))
        thread.daemon = True
        thread.start()

    def _import_mal_user_thread(self, username: str):
        """Background thread for importing MAL user list"""
        try:
            # Get user's anime list
            anime_list = self.mal_service.get_user_animelist(username)

            if not anime_list:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "No Anime Found",
                        f"No anime found for user '{username}'.\nThe list may be private or the username may be incorrect.",
                    ),
                )
                return

            # Prepare anime data for preview
            processed_list = []
            for mal_anime in anime_list:
                anime_data = mal_anime.get("anime", {})

                # Combine data from list and anime info
                combined = {
                    "mal_id": anime_data.get("mal_id"),
                    "title": anime_data.get("title", "Unknown"),
                    "title_english": anime_data.get("title_english"),
                    "title_japanese": anime_data.get("title_japanese"),
                    "episodes": anime_data.get("episodes"),
                    "num_episodes_watched": mal_anime.get("episodes_watched", 0),
                    "score": mal_anime.get("score"),
                    "watching_status": mal_anime.get("watching_status"),
                    "synopsis": anime_data.get("synopsis"),
                    "images": anime_data.get("images", {}),
                    "genres": anime_data.get("genres", []),
                    "studios": anime_data.get("studios", []),
                }

                # Map MAL status to readable format
                status_map = {
                    1: "watching",
                    2: "completed",
                    3: "on_hold",
                    4: "dropped",
                    6: "plan_to_watch",
                }
                combined["watching_status"] = status_map.get(
                    mal_anime.get("watching_status"), "unknown"
                )

                processed_list.append(combined)

            # Show preview dialog on main thread
            self.root.after(0, lambda: self._show_import_preview(processed_list))

        except Exception as e:
            logger.error(f"Import failed: {e}")
            self.root.after(
                0,
                lambda: messagebox.showerror("Import Failed", f"Failed to import from MAL: {e!s}"),
            )

    def _show_import_preview(self, anime_list):
        """Show import preview dialog"""
        from ui.mal_import_preview_dialog import MALImportPreviewDialog

        MALImportPreviewDialog(
            self.root, anime_list, self.service, self.mal_service, self.image_service
        )
        # Refresh list after dialog closes
        self.refresh_list()

    def _import_complete(self, imported: int, skipped: int):
        """Show import completion message"""
        self.refresh_list()
        message = f"Import complete!\n\nImported: {imported} anime"
        if skipped > 0:
            message += f"\nSkipped: {skipped} (already in list)"
        messagebox.showinfo("Import Complete", message)

    def update_mal_status(self):
        """Update MAL connection status in UI"""
        # Check OAuth authentication status
        if self.mal_auth_manager.is_authenticated():
            self.mal_status_label.config(text="MAL: ✓", foreground="green")
        else:
            self.mal_status_label.config(text="MAL: ✗", foreground="red")

        # Update sync queue count
        queue_count = self.sync_service.get_sync_queue_count()
        self.sync_queue_label.config(text=f"Queue: {queue_count}")

        # Update sync button state based on authentication
        if self.mal_auth_manager.is_authenticated():
            self.sync_button.config(state="normal")
            self.sync_status_label.config(text="Ready", foreground="green")
        else:
            self.sync_button.config(state="disabled")
            self.sync_status_label.config(text="Not Connected", foreground="gray")

        # Schedule next update in 30 seconds
        self.root.after(30000, self.update_mal_status)

    def quick_mal_connect(self):
        """Quick MAL connection from toolbar"""
        if self.mal_auth_manager.is_authenticated():
            # Already connected, offer to disconnect
            response = messagebox.askyesno(
                "MAL Connected",
                "You are already connected to MyAnimeList.\n\nWould you like to disconnect?",
            )
            if response:
                self.mal_auth_manager.oauth_client.logout()
                self.mal_connect_btn.config(text="🔗 Connect MAL", fg="black")
                self.sync_button.config(state="disabled")
                self.sync_status_label.config(text="Not Connected", foreground="gray")
                messagebox.showinfo("Disconnected", "Disconnected from MyAnimeList")
        else:
            # Not connected, start authentication
            self.notifications.show("Opening browser for MAL authentication...", level="info")

            # Start authentication in background thread
            import threading

            thread = threading.Thread(target=self._perform_mal_auth)
            thread.daemon = True
            thread.start()

    def _perform_mal_auth(self):
        """Perform MAL authentication in background"""
        try:
            success = self.mal_auth_manager.oauth_client.authorize()

            if success:
                # Update UI on main thread
                self.root.after(0, self._mal_auth_success)
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Authentication Failed",
                        "Failed to authenticate with MyAnimeList.\n\n"
                        "Please make sure:\n"
                        "1. You're logged in to MyAnimeList\n"
                        "2. You authorized the application\n"
                        "3. Port 8888 is not blocked",
                    ),
                )
        except Exception as e:
            self.root.after(
                0,
                lambda msg=str(e): messagebox.showerror(
                    "Authentication Error", f"An error occurred during authentication:\n{msg}"
                ),
            )

    def _mal_auth_success(self):
        """Handle successful MAL authentication"""
        # Reinitialize services
        from services.mal_api_v2_service import MALAPIv2Service

        self.mal_api_v2_service = MALAPIv2Service(self.mal_auth_manager.oauth_client)

        # Update sync service
        self.sync_service.oauth_client = self.mal_auth_manager.oauth_client
        self.sync_service.mal_api_service = self.mal_api_v2_service
        self.sync_service.refresh_authentication()
        self.sync_service.enable_sync()

        # Update UI
        self.mal_connect_btn.config(text="✓ MAL Connected", fg="green")
        self.sync_button.config(state="normal")
        self.sync_status_label.config(text="Ready", foreground="green")

        # Update MAL status
        self.update_mal_status()

        self.notifications.show("Successfully connected to MyAnimeList!", level="success")

        # Get user info
        try:
            user_info = self.mal_auth_manager.oauth_client.make_api_request("/users/@me")
            if user_info:
                username = user_info.get("name", "Unknown")
                messagebox.showinfo(
                    "Connected!",
                    f"Successfully connected to MyAnimeList!\n\nLogged in as: {username}",
                )
        except:
            pass

    def show_mal_auth(self):
        """Show MAL authentication dialog"""
        authenticated = self.mal_auth_manager.show_auth_dialog(self.root)

        if authenticated:
            # Reinitialize services with OAuth2 client
            from services.mal_api_v2_service import MALAPIv2Service

            self.mal_api_v2_service = MALAPIv2Service(self.mal_auth_manager.oauth_client)

            # Update sync service
            self.sync_service.oauth_client = self.mal_auth_manager.oauth_client
            self.sync_service.mal_api_service = self.mal_api_v2_service
            self.sync_service.refresh_authentication()
            self.sync_service.enable_sync()

            # Update buttons
            self.mal_connect_btn.config(text="✓ MAL Connected", fg="green")
            self.sync_button.config(state="normal")
            self.sync_status_label.config(text="Sync: Ready", foreground="green")

            # Update MAL status
            self.update_mal_status()

    def sync_with_mal_v2(self):
        """Sync with MAL using OAuth2 (Phase 3)"""
        if not self.mal_auth_manager.is_authenticated():
            response = messagebox.askyesno(
                "Authentication Required",
                "You need to authenticate with MyAnimeList to sync.\n\n"
                "Would you like to authenticate now?",
            )

            if response:
                self.show_mal_auth()
            return

        # Show sync options dialog
        from ui.sync_dialog import SyncDialog

        dialog = SyncDialog(self.root, self.sync_service)
        self.root.wait_window(dialog.dialog)

        if dialog.result:
            sync_type = dialog.result.get("type")
            self.notifications.show(f"Starting {sync_type} sync...", level="info")

            # Perform sync in background
            import threading

            thread = threading.Thread(target=self._perform_sync, args=(sync_type,))
            thread.daemon = True
            thread.start()

    def _perform_sync(self, sync_type: str):
        """Perform sync operation in background

        Args:
            sync_type: Type of sync (push, pull, full)
        """
        try:
            # Create new database connection for this thread
            from models.database import Database

            thread_db = Database(str(self.config.db_path))

            # Create new sync service with thread-safe database
            from services.sync_service import SyncService

            thread_sync = SyncService(
                thread_db, self.mal_api_v2_service, self.mal_auth_manager.oauth_client
            )
            thread_sync.refresh_authentication()

            all_errors = []

            if sync_type == "push":
                # Push local changes to MAL
                success, failed, errors = thread_sync.process_sync_queue()

                self.root.after(
                    0,
                    lambda: self.notifications.show(
                        f"Push complete: {success} succeeded, {failed} failed",
                        level="success" if failed == 0 else "warning",
                    ),
                )
                all_errors.extend(errors)

            elif sync_type == "pull":
                # Pull from MAL
                added, updated, errors = thread_sync.full_sync_from_mal()

                self.root.after(
                    0,
                    lambda: self.notifications.show(
                        f"Pull complete: {added} added, {updated} updated", level="success"
                    ),
                )
                all_errors.extend(errors)

                # Refresh list
                self.root.after(0, self.refresh_list)

            elif sync_type == "full":
                # Full bidirectional sync
                # First push local changes
                push_success, push_failed, push_errors = thread_sync.process_sync_queue()

                # Then pull from MAL
                added, updated, pull_errors = thread_sync.full_sync_from_mal()

                self.root.after(
                    0,
                    lambda: self.notifications.show(
                        f"Full sync complete: {push_success} pushed, {added} added, {updated} updated",
                        level="success",
                    ),
                )

                all_errors.extend(push_errors)
                all_errors.extend(pull_errors)

                # Refresh list
                self.root.after(0, self.refresh_list)

            # Show errors if any
            if all_errors:
                error_msg = "\n".join(all_errors[:5])  # Show first 5 errors
                if len(all_errors) > 5:
                    error_msg += f"\n... and {len(all_errors) - 5} more"

                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Sync Warnings", f"Some items could not be synced:\n\n{error_msg}"
                    ),
                )

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror("Sync Failed", f"Sync operation failed:\n{error_msg}"),
            )

    def show_settings(self):
        """Show settings dialog"""
        from ui.settings_dialog import SettingsDialog

        # Create settings dialog with update check option and scrobbling manager
        dialog = SettingsDialog(
            self.root,
            config=self.config,
            scrobbling_manager=getattr(self, 'scrobbling_manager', None)
        )
        self.root.wait_window(dialog.dialog)

        if dialog.result:
            # Apply settings
            self.check_for_updates_enabled = self.config.get("check_for_updates", False)

            # Show success notification
            self.notifications.show("Settings saved successfully", NotificationLevel.SUCCESS)

    def show_about(self):
        """Show about/diagnostics dialog"""
        from ui.about_dialog import AboutDialog

        AboutDialog(self.root, self.config, self.db)

    def set_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)

    def update_status_bar(self, count: int):
        """Update status bar counts"""
        anime_text = "anime" if count == 1 else "anime"
        self.count_label.config(text=f"{count} {anime_text}")

        # Get status breakdown
        stats = self.service.get_statistics()
        watching = stats.get("currently_watching", 0)
        completed = stats.get("by_status", {}).get("Completed", 0)

        if watching > 0 or completed > 0:
            status_text = f"Total: {count}"
            if watching > 0:
                status_text += f" | Watching: {watching}"
            if completed > 0:
                status_text += f" | Completed: {completed}"
            self.set_status(status_text)

    def check_for_updates_on_startup(self):
        """Check for updates on startup (background)"""
        try:
            from datetime import datetime

            from utils.version_checker import VersionChecker

            # Check if enough time has passed since last check
            if self.last_update_check:
                try:
                    last_check = datetime.fromisoformat(self.last_update_check)
                    checker = VersionChecker(__version__)
                    if not checker.should_check(last_check, check_interval_days=7):
                        return
                except:
                    pass  # Invalid date, continue with check

            # Check for updates in background
            from utils.version_checker import check_for_updates_async

            check_for_updates_async(__version__, self._handle_update_check_result)

            # Update last check time
            self.last_update_check = datetime.now().isoformat()
            self.config.set("last_update_check", self.last_update_check)

        except Exception as e:
            logger.debug(f"Update check failed: {e}")

    def check_for_updates_manual(self):
        """Manual check for updates from menu"""
        try:
            from datetime import datetime

            from utils.version_checker import VersionChecker

            # Show checking message
            self.notifications.show("Checking for updates...", NotificationLevel.INFO)

            # Initialize checker
            if not self.version_checker:
                self.version_checker = VersionChecker(__version__)

            # Check for updates in background
            from utils.version_checker import check_for_updates_async

            check_for_updates_async(
                __version__, lambda result: self._handle_update_check_result(result, manual=True)
            )

            # Update last check time
            self.last_update_check = datetime.now().isoformat()
            self.config.set("last_update_check", self.last_update_check)

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            self.notifications.show(
                "Could not check for updates. Please check your internet connection.",
                NotificationLevel.WARNING,
            )

    def _handle_update_check_result(self, update_info, manual=False):
        """Handle update check result

        Args:
            update_info: Update information or None
            manual: Whether this was a manual check
        """
        if update_info:
            # New version available
            version = update_info.get("version", "Unknown")
            name = update_info.get("name", "")
            url = update_info.get("url", "")

            message = f"Mirenku {version} is available!"
            if name and name != f"Version {version}":
                message += f"\n{name}"

            # Show notification
            self.notifications.show(
                message,
                NotificationLevel.INFO,
                duration=10000,  # Show for 10 seconds
            )

            # Optionally show dialog for more info
            if manual or self.config.get("show_update_dialog", True):
                self.root.after(0, lambda: self._show_update_dialog(update_info))

        elif manual:
            # No updates, but user manually checked
            self.notifications.show(
                f"You're running the latest version (v{__version__})", NotificationLevel.SUCCESS
            )

    def _show_update_dialog(self, update_info):
        """Show update available dialog

        Args:
            update_info: Update information dict
        """
        version = update_info.get("version", "Unknown")
        name = update_info.get("name", "")
        notes = update_info.get("notes", "")
        url = update_info.get("url", "")

        message = "A new version of Mirenku is available!\n\n"
        message += f"Current version: v{__version__}\n"
        message += f"New version: v{version}\n"

        if name and name != f"Version {version}":
            message += f"\n{name}\n"

        if notes:
            message += f"\nRelease notes:\n{notes[:300]}"
            if len(notes) > 300:
                message += "..."

        message += "\n\nWould you like to visit the download page?"

        result = messagebox.askyesno("Update Available", message, icon="info")

        if result and url:
            # Open download page in browser
            import webbrowser

            webbrowser.open(url)

    def _on_database_change(self):
        """Callback when database changes externally"""
        if not self.auto_refresh_enabled or self.manual_operation:
            return

        try:
            # Schedule refresh on main thread
            self.root.after(0, self._do_auto_refresh)
        except Exception as e:
            logger.error(f"Error scheduling auto-refresh: {e}")

    def _do_auto_refresh(self):
        """Perform auto-refresh on main thread"""
        try:
            # Save current selection
            selected = self.tree.selection()
            selected_id = None
            if selected:
                selected_id = self.tree.item(selected[0])["text"]

            # Refresh the list
            self.refresh_list()

            # Restore selection if possible
            if selected_id:
                for item in self.tree.get_children():
                    if self.tree.item(item)["text"] == selected_id:
                        self.tree.selection_set(item)
                        self.tree.see(item)
                        break

            # Show subtle notification
            logger.debug("Auto-refresh completed")

        except Exception as e:
            logger.error(f"Error during auto-refresh: {e}")

    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        self.auto_refresh_var.set(self.auto_refresh_enabled)
        status = "enabled" if self.auto_refresh_enabled else "disabled"
        self.notifications.show(f"Auto-refresh {status}", NotificationLevel.INFO)
        logger.info(f"Auto-refresh {status}")

    def on_closing(self):
        """Handle window closing"""
        # Save window state
        self.persistence.save_window_state(
            geometry=self.root.geometry(), filter_status=self.current_filter.get()
        )

        # Stop scrobbling server if running
        if hasattr(self, 'scrobbling_manager') and self.scrobbling_manager:
            try:
                self.scrobbling_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping scrobbling server: {e}")

        # Stop database watcher
        self.db_watcher.stop()

        # Stop auto-save
        self.persistence.stop_auto_save_thread()

        # Final backup
        self.persistence.create_backup()

        # Save version check settings
        if hasattr(self, "last_update_check"):
            self.config.set("last_update_check", self.last_update_check)

        # Disconnect database
        self.db.disconnect()
        self.root.destroy()
