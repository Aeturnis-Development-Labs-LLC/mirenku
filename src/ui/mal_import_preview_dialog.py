"""MAL Import Preview Dialog with checkbox selection"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk

logger = logging.getLogger(__name__)


class MALImportPreviewDialog:
    """Dialog for previewing and selecting anime to import from MAL"""

    def __init__(self, parent, anime_list, anime_service, mal_service, image_service):
        """Initialize import preview dialog

        Args:
            parent: Parent window
            anime_list: List of anime dictionaries from MAL
            anime_service: Local anime service instance
            mal_service: MAL service instance
            image_service: Image service instance
        """
        self.parent = parent
        self.anime_list = anime_list
        self.anime_service = anime_service
        self.mal_service = mal_service
        self.image_service = image_service
        self.selected_items = set()
        self.checkboxes = {}
        self.import_thread = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Import from MyAnimeList - Preview")
        self.dialog.geometry("900x600")
        self.dialog.resizable(True, True)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 450
        y = (self.dialog.winfo_screenheight() // 2) - 300
        self.dialog.geometry(f"900x600+{x}+{y}")

        self.create_widgets()
        self.populate_list()

        # Bind keyboard shortcuts
        self.dialog.bind("<Escape>", lambda e: self.cancel())
        self.dialog.bind("<Return>", lambda e: self.import_selected())

    def create_widgets(self):
        """Create dialog widgets"""
        # Top frame with controls
        control_frame = ttk.Frame(self.dialog, padding="10")
        control_frame.pack(fill="x")

        ttk.Label(
            control_frame,
            text=f"Found {len(self.anime_list)} anime in MAL list. Select which ones to import:",
            font=("TkDefaultFont", 10),
        ).pack(side="left")

        # Select all/none buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side="right")

        ttk.Button(button_frame, text="Select All", command=self.select_all).pack(
            side="left", padx=2
        )

        ttk.Button(button_frame, text="Select None", command=self.select_none).pack(
            side="left", padx=2
        )

        ttk.Button(button_frame, text="Select New Only", command=self.select_new_only).pack(
            side="left", padx=2
        )

        # Main frame with scrollable list
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Create treeview with checkboxes
        columns = ("Title", "Episodes", "Score", "Status", "Exists")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="tree headings", height=15)

        # Configure columns
        self.tree.column("#0", width=50, stretch=False)  # Checkbox column
        self.tree.column("Title", width=350)
        self.tree.column("Episodes", width=100, anchor="center")
        self.tree.column("Score", width=80, anchor="center")
        self.tree.column("Status", width=120, anchor="center")
        self.tree.column("Exists", width=80, anchor="center")

        # Set headings
        self.tree.heading("#0", text="✓")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Episodes", text="Episodes")
        self.tree.heading("Score", text="Score")
        self.tree.heading("Status", text="MAL Status")
        self.tree.heading("Exists", text="In Library")

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind click event for checkbox toggle
        self.tree.bind("<Button-1>", self.on_click)

        # Progress frame (hidden initially)
        self.progress_frame = ttk.Frame(self.dialog, padding="10")

        self.progress_label = ttk.Label(self.progress_frame, text="Importing...")
        self.progress_label.pack()

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate", length=400)
        self.progress_bar.pack(pady=5)

        self.progress_detail = ttk.Label(self.progress_frame, text="")
        self.progress_detail.pack()

        # Bottom frame with buttons and status
        bottom_frame = ttk.Frame(self.dialog, padding="10")
        bottom_frame.pack(fill="x")

        # Status label
        self.status_label = ttk.Label(bottom_frame, text="0 selected for import")
        self.status_label.pack(side="left")

        # Buttons
        button_container = ttk.Frame(bottom_frame)
        button_container.pack(side="right")

        self.import_button = ttk.Button(
            button_container, text="Import Selected", command=self.import_selected, state="disabled"
        )
        self.import_button.pack(side="left", padx=5)

        ttk.Button(button_container, text="Cancel", command=self.cancel).pack(side="left", padx=5)

    def populate_list(self):
        """Populate the tree with anime data"""
        for anime in self.anime_list:
            # Extract data
            title = anime.get("title", "Unknown")
            mal_id = anime.get("mal_id")

            # Check if already exists
            existing = self.anime_service.search_anime(title)
            exists = "Yes" if existing else "No"

            # Get episode info
            episodes = anime.get("episodes", "?")
            if anime.get("watching_status"):
                watched = anime.get("num_episodes_watched", 0)
                episodes = f"{watched}/{episodes}"

            # Get score
            score = anime.get("score", "N/A")
            if score and score != "N/A":
                score = f"{score}/10"

            # Get status
            status = anime.get("watching_status", anime.get("status", "Unknown"))

            # Insert into tree
            item = self.tree.insert(
                "",
                "end",
                text="☐",
                values=(title, episodes, score, status, exists),
                tags=("unchecked",),
            )

            # Store anime data with item
            self.tree.set(item, "#0", mal_id)

            # Auto-select if new
            if exists == "No":
                self.toggle_item(item, True)

    def on_click(self, event):
        """Handle click events on the tree"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":
            item = self.tree.identify_row(event.y)
            if item:
                self.toggle_item(item)

    def toggle_item(self, item, checked=None):
        """Toggle checkbox for an item"""
        current_text = self.tree.item(item, "text")
        mal_id = self.tree.set(item, "#0")

        if checked is None:
            # Toggle
            if current_text == "☐":
                self.tree.item(item, text="☑", tags=("checked",))
                self.selected_items.add(mal_id)
            else:
                self.tree.item(item, text="☐", tags=("unchecked",))
                self.selected_items.discard(mal_id)
        # Set specific state
        elif checked:
            self.tree.item(item, text="☑", tags=("checked",))
            self.selected_items.add(mal_id)
        else:
            self.tree.item(item, text="☐", tags=("unchecked",))
            self.selected_items.discard(mal_id)

        self.update_status()

    def select_all(self):
        """Select all items"""
        for item in self.tree.get_children():
            self.toggle_item(item, True)

    def select_none(self):
        """Deselect all items"""
        for item in self.tree.get_children():
            self.toggle_item(item, False)

    def select_new_only(self):
        """Select only anime not in library"""
        for item in self.tree.get_children():
            exists = self.tree.item(item, "values")[4]
            self.toggle_item(item, exists == "No")

    def update_status(self):
        """Update status label and button state"""
        count = len(self.selected_items)
        self.status_label.config(text=f"{count} selected for import")
        self.import_button.config(state="normal" if count > 0 else "disabled")

    def import_selected(self):
        """Import selected anime"""
        if not self.selected_items:
            return

        # Get selected anime
        selected_anime = [
            anime
            for anime in self.anime_list
            if str(anime.get("mal_id")) in [str(id) for id in self.selected_items]
        ]

        if not selected_anime:
            return

        # Confirm import
        response = messagebox.askyesno(
            "Confirm Import", f"Import {len(selected_anime)} anime from MyAnimeList?"
        )

        if not response:
            return

        # Hide list and show progress
        for widget in self.dialog.winfo_children():
            if widget != self.progress_frame:
                widget.pack_forget()

        self.progress_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Start import in background thread
        self.import_thread = threading.Thread(target=self._import_thread, args=(selected_anime,))
        self.import_thread.daemon = True
        self.import_thread.start()

    def _import_thread(self, anime_list):
        """Background thread for importing anime"""
        total = len(anime_list)
        imported = 0
        failed = 0
        errors = []

        for i, anime in enumerate(anime_list):
            try:
                # Update progress
                self.dialog.after(0, self._update_progress, i, total, anime.get("title", "Unknown"))

                # Extract all data
                mal_id = anime.get("mal_id")
                title = anime.get("title", "Unknown")
                title_english = anime.get("title_english")
                title_japanese = anime.get("title_japanese")
                total_episodes = anime.get("episodes")
                synopsis = anime.get("synopsis", "")

                # Get genres
                genres = []
                if "genres" in anime:
                    genres = [g["name"] for g in anime.get("genres", [])]

                # Get studios
                studio = None
                if anime.get("studios"):
                    studio = anime["studios"][0].get("name")

                # Get image URL
                images = anime.get("images", {})
                jpg_images = images.get("jpg", {})
                image_url = jpg_images.get("image_url", "")

                # Handle missing data gracefully
                if not title or title == "Unknown":
                    title = title_english or title_japanese or f"MAL ID {mal_id}"

                # Map MAL status to local status
                mal_status = anime.get("watching_status", anime.get("status", ""))
                status_map = {
                    "watching": "Watching",
                    "completed": "Completed",
                    "on_hold": "On Hold",
                    "dropped": "Dropped",
                    "plan_to_watch": "Plan to Watch",
                    "ptw": "Plan to Watch",
                }
                status = status_map.get(mal_status.lower(), "Plan to Watch")

                # Get episodes watched
                episodes_watched = anime.get("num_episodes_watched", 0)

                # Add to database
                success, message, anime_id = self.anime_service.add_anime(
                    title=title,
                    status=status,
                    episodes_watched=episodes_watched,
                    total_episodes=total_episodes if total_episodes else None,
                    mal_id=mal_id,
                    title_english=title_english,
                    title_japanese=title_japanese,
                    synopsis=synopsis if synopsis else None,
                    genres=genres,
                    studio=studio,
                    image_url=image_url,
                )

                if success:
                    imported += 1

                    # Queue image download
                    if image_url:
                        self.image_service.queue_download(
                            image_url, self.image_service.cache_dir / f"mal_{mal_id}.jpg"
                        )
                else:
                    failed += 1
                    errors.append(f"{title}: {message}")

            except Exception as e:
                failed += 1
                errors.append(f"Error importing {anime.get('title', 'Unknown')}: {e!s}")
                logger.error(f"Import error: {e}")

        # Show completion
        self.dialog.after(0, self._import_complete, imported, failed, errors)

    def _update_progress(self, current, total, title):
        """Update progress display"""
        progress = (current / total) * 100
        self.progress_bar["value"] = progress
        self.progress_label.config(text=f"Importing {current + 1} of {total}")
        self.progress_detail.config(text=f"Processing: {title[:50]}...")

    def _import_complete(self, imported, failed, errors):
        """Handle import completion"""
        # Show results
        if imported > 0:
            message = f"Successfully imported {imported} anime"
            if failed > 0:
                message += f"\n{failed} failed to import"
                if errors and len(errors) <= 5:
                    message += "\n\nErrors:\n" + "\n".join(errors)
                elif errors:
                    message += "\n\nFirst 5 errors:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Import Complete", message)
        else:
            message = f"No anime imported. {failed} failed."
            if errors and len(errors) <= 5:
                message += "\n\nErrors:\n" + "\n".join(errors)
            elif errors:
                message += "\n\nFirst 5 errors:\n" + "\n".join(errors[:5])
            messagebox.showerror("Import Failed", message)

        self.dialog.destroy()

    def cancel(self):
        """Cancel import and close dialog"""
        if self.import_thread and self.import_thread.is_alive():
            response = messagebox.askyesno(
                "Cancel Import", "Import is in progress. Are you sure you want to cancel?"
            )
            if not response:
                return

        self.dialog.destroy()
