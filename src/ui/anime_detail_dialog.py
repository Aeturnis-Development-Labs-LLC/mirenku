"""Detailed anime view dialog with cover image display"""

import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

logger = logging.getLogger(__name__)


class AnimeDetailDialog:
    """Dialog for displaying detailed anime information"""

    def __init__(self, parent, anime, anime_service, image_service, mal_service=None):
        """Initialize anime detail dialog

        Args:
            parent: Parent window
            anime: Anime instance to display
            anime_service: Anime service instance
            image_service: Image service instance
            mal_service: Optional MAL service instance
        """
        self.parent = parent
        self.anime = anime
        self.anime_service = anime_service
        self.image_service = image_service
        self.mal_service = mal_service
        self.photo = None  # Keep reference to prevent garbage collection

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Anime Details - {anime.display_title}")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 400
        y = (self.dialog.winfo_screenheight() // 2) - 300
        self.dialog.geometry(f"800x600+{x}+{y}")

        self.create_widgets()
        self.load_data()

        # Bind keyboard shortcuts
        self.dialog.bind("<Escape>", lambda e: self.close())

    def create_widgets(self):
        """Create dialog widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Top section with image and basic info
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 10))

        # Image frame (left side)
        image_frame = ttk.Frame(top_frame)
        image_frame.pack(side="left", padx=(0, 10))

        # Cover image label
        self.image_label = ttk.Label(image_frame)
        self.image_label.pack()

        # Refresh image button
        if self.anime.image_url:
            ttk.Button(image_frame, text="Refresh Image", command=self.refresh_image).pack(
                pady=(5, 0)
            )

        # Info frame (right side)
        info_frame = ttk.Frame(top_frame)
        info_frame.pack(side="left", fill="both", expand=True)

        # Title
        title_label = ttk.Label(
            info_frame, text=self.anime.display_title, font=("TkDefaultFont", 14, "bold")
        )
        title_label.pack(anchor="w")

        if self.anime.title_japanese:
            ttk.Label(info_frame, text=self.anime.title_japanese, font=("TkDefaultFont", 10)).pack(
                anchor="w"
            )

        # Separator
        ttk.Separator(info_frame, orient="horizontal").pack(fill="x", pady=10)

        # Basic info grid
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill="x")

        # Status
        ttk.Label(info_grid, text="Status:", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        status_label = ttk.Label(info_grid, text=self.anime.status)
        status_label.grid(row=0, column=1, sticky="w")

        # Progress
        ttk.Label(info_grid, text="Progress:", font=("TkDefaultFont", 9, "bold")).grid(
            row=1, column=0, sticky="w", padx=(0, 5)
        )
        progress_frame = ttk.Frame(info_grid)
        progress_frame.grid(row=1, column=1, sticky="w")

        self.progress_label = ttk.Label(progress_frame, text=self.anime.display_progress)
        self.progress_label.pack(side="left")

        # Progress buttons
        ttk.Button(progress_frame, text="-", width=3, command=self.decrement_episode).pack(
            side="left", padx=(10, 2)
        )

        ttk.Button(progress_frame, text="+", width=3, command=self.increment_episode).pack(
            side="left", padx=(2, 0)
        )

        # Score
        ttk.Label(info_grid, text="Score:", font=("TkDefaultFont", 9, "bold")).grid(
            row=2, column=0, sticky="w", padx=(0, 5)
        )

        score_frame = ttk.Frame(info_grid)
        score_frame.grid(row=2, column=1, sticky="w")

        self.score_var = tk.IntVar(value=self.anime.score or 0)
        self.score_spinbox = ttk.Spinbox(
            score_frame,
            from_=0,
            to=10,
            textvariable=self.score_var,
            width=5,
            command=self.update_score,
        )
        self.score_spinbox.pack(side="left")

        ttk.Label(score_frame, text="/ 10").pack(side="left", padx=(5, 0))

        # Type and Episodes
        if self.anime.year or self.anime.season:
            ttk.Label(info_grid, text="Season:", font=("TkDefaultFont", 9, "bold")).grid(
                row=3, column=0, sticky="w", padx=(0, 5)
            )
            season_text = f"{self.anime.season or ''} {self.anime.year or ''}".strip()
            ttk.Label(info_grid, text=season_text).grid(row=3, column=1, sticky="w")

        # Studio
        if self.anime.studio:
            ttk.Label(info_grid, text="Studio:", font=("TkDefaultFont", 9, "bold")).grid(
                row=4, column=0, sticky="w", padx=(0, 5)
            )
            ttk.Label(info_grid, text=self.anime.studio).grid(row=4, column=1, sticky="w")

        # Genres
        if self.anime.genres:
            ttk.Label(info_grid, text="Genres:", font=("TkDefaultFont", 9, "bold")).grid(
                row=5, column=0, sticky="w", padx=(0, 5)
            )
            genres_text = ", ".join(self.anime.genres)
            ttk.Label(info_grid, text=genres_text, wraplength=300).grid(row=5, column=1, sticky="w")

        # Synopsis section - moved up and improved layout
        if self.anime.synopsis:
            synopsis_frame = ttk.LabelFrame(main_frame, text="Synopsis", padding="10")
            synopsis_frame.pack(fill="both", expand=True, pady=(10, 0))

            # Create a frame for the text widget and scrollbar
            text_frame = ttk.Frame(synopsis_frame)
            text_frame.pack(fill="both", expand=True)

            # Create scrollbar first
            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side="right", fill="y")

            synopsis_text = tk.Text(
                text_frame,
                height=10,  # Increased height for better readability
                wrap="word",
                relief="flat",
                bg=self.dialog.cget("bg"),
                padx=5,
                pady=5,
                yscrollcommand=scrollbar.set,
            )
            synopsis_text.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=synopsis_text.yview)

            synopsis_text.insert("1.0", self.anime.synopsis)
            synopsis_text.config(state="disabled")

        # MAL Link - moved below synopsis
        if self.anime.mal_id:
            mal_frame = ttk.Frame(main_frame)
            mal_frame.pack(fill="x", pady=(10, 0))

            ttk.Button(mal_frame, text="View on MyAnimeList", command=self.open_mal_page).pack(
                side="left"
            )

            if self.mal_service:
                ttk.Button(mal_frame, text="Refresh from MAL", command=self.refresh_from_mal).pack(
                    side="left", padx=(5, 0)
                )

        # Notes section
        notes_frame = ttk.LabelFrame(main_frame, text="Personal Notes", padding="10")
        notes_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.notes_text = tk.Text(notes_frame, height=4, wrap="word")
        self.notes_text.pack(fill="both", expand=True)

        if self.anime.notes:
            self.notes_text.insert("1.0", self.anime.notes)

        # Button frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Save Changes", command=self.save_changes).pack(
            side="left", padx=5
        )

        ttk.Button(button_frame, text="Close", command=self.close).pack(side="right", padx=5)

        # Status label
        self.status_label = ttk.Label(self.dialog, text="", relief="sunken", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(0, 10))

    def load_data(self):
        """Load anime data including image"""
        # Load cover image
        self.load_image()

    def load_image(self):
        """Load and display cover image"""
        try:
            # Define callback for when image downloads
            def on_image_downloaded(path):
                # Schedule UI update in main thread
                self.dialog.after(0, lambda: self._display_image(path))

            # Get image path (downloads if needed with callback)
            image_path = self.image_service.get_image_path(
                self.anime.image_url, self.anime.mal_id, callback=on_image_downloaded
            )

            # Display the image (placeholder or actual)
            self._display_image(image_path)

        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            self.image_label.config(text="Failed to load image")

    def _display_image(self, image_path):
        """Display an image from path"""
        try:
            if image_path and image_path.exists():
                # Load and resize image
                img = Image.open(image_path)

                # Resize to fit (max 225x320)
                img.thumbnail((225, 320), Image.Resampling.LANCZOS)

                # Convert to PhotoImage
                self.photo = ImageTk.PhotoImage(img)

                # Update label
                self.image_label.config(image=self.photo)
            else:
                # Show placeholder text
                self.image_label.config(text="No Image Available")
        except Exception as e:
            logger.error(f"Failed to display image: {e}")

    def refresh_image(self):
        """Refresh cover image from MAL"""
        if not self.anime.image_url:
            return

        self.status_label.config(text="Refreshing image...")

        try:
            # Force refresh
            new_path = self.image_service.refresh_image(self.anime.image_url, self.anime.mal_id)

            if new_path:
                self.load_image()
                self.status_label.config(text="Image refreshed")
            else:
                self.status_label.config(text="Failed to refresh image")

        except Exception as e:
            logger.error(f"Failed to refresh image: {e}")
            self.status_label.config(text="Error refreshing image")

    def increment_episode(self):
        """Increment episode count"""
        success, message = self.anime_service.increment_episode(self.anime.id)
        if success:
            # Reload anime data
            self.anime = self.anime_service.get_anime(self.anime.id)
            self.progress_label.config(text=self.anime.display_progress)
            self.status_label.config(text=message)

    def decrement_episode(self):
        """Decrement episode count"""
        success, message = self.anime_service.decrement_episode(self.anime.id)
        if success:
            # Reload anime data
            self.anime = self.anime_service.get_anime(self.anime.id)
            self.progress_label.config(text=self.anime.display_progress)
            self.status_label.config(text=message)

    def update_score(self):
        """Update anime score"""
        new_score = self.score_var.get()
        if new_score != (self.anime.score or 0):
            success, message = self.anime_service.update_anime(
                self.anime.id, score=new_score if new_score > 0 else None
            )
            if success:
                self.anime.score = new_score if new_score > 0 else None
                self.status_label.config(text="Score updated")

    def open_mal_page(self):
        """Open anime page on MAL website"""
        if self.anime.mal_id:
            import webbrowser

            url = f"https://myanimelist.net/anime/{self.anime.mal_id}"
            webbrowser.open(url)

    def refresh_from_mal(self):
        """Refresh anime data from MAL"""
        if not self.mal_service or not self.anime.mal_id:
            return

        self.status_label.config(text="Fetching data from MAL...")

        try:
            # Get updated data from MAL
            mal_data = self.mal_service.get_anime_details(self.anime.mal_id)

            if mal_data:
                # Update anime with new data
                updates = {}

                if mal_data.get("synopsis"):
                    updates["synopsis"] = mal_data["synopsis"]

                if mal_data.get("genres"):
                    updates["genres"] = [g["name"] for g in mal_data["genres"]]

                if mal_data.get("studios"):
                    studios = [s["name"] for s in mal_data["studios"]]
                    if studios:
                        updates["studio"] = studios[0]

                if updates:
                    success, message = self.anime_service.update_anime(self.anime.id, **updates)

                    if success:
                        # Reload anime
                        self.anime = self.anime_service.get_anime(self.anime.id)
                        self.status_label.config(text="Updated from MAL")

                        # Refresh display
                        self.dialog.destroy()
                        self.__init__(
                            self.parent,
                            self.anime,
                            self.anime_service,
                            self.image_service,
                            self.mal_service,
                        )
                    else:
                        self.status_label.config(text=f"Update failed: {message}")
                else:
                    self.status_label.config(text="No updates available")
            else:
                self.status_label.config(text="Failed to fetch MAL data")

        except Exception as e:
            logger.error(f"Failed to refresh from MAL: {e}")
            self.status_label.config(text="Error fetching MAL data")

    def save_changes(self):
        """Save any changes made"""
        # Save notes
        new_notes = self.notes_text.get("1.0", tk.END).strip()
        if new_notes != (self.anime.notes or ""):
            success, message = self.anime_service.update_anime(
                self.anime.id, notes=new_notes if new_notes else None
            )
            if success:
                self.status_label.config(text="Notes saved")
            else:
                self.status_label.config(text=f"Failed to save: {message}")

    def close(self):
        """Close dialog"""
        self.save_changes()
        self.dialog.destroy()
