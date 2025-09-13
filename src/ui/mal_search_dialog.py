"""MAL Search Dialog for finding and importing anime from MyAnimeList"""

import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List

logger = logging.getLogger(__name__)


class MALSearchDialog:
    """Dialog for searching and importing anime from MyAnimeList"""

    def __init__(self, parent, mal_service, anime_service):
        """Initialize MAL search dialog

        Args:
            parent: Parent window
            mal_service: MAL API service instance
            anime_service: Local anime service instance
        """
        self.parent = parent
        self.mal_service = mal_service
        self.anime_service = anime_service
        self.selected_anime = None
        self.search_results = []

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Search MyAnimeList")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400)
        y = (self.dialog.winfo_screenheight() // 2) - (300)
        self.dialog.geometry(f"800x600+{x}+{y}")

        self.create_widgets()

        # Bind keyboard shortcuts
        self.dialog.bind("<Return>", lambda e: self.search())
        self.dialog.bind("<Escape>", lambda e: self.close())

        # Focus search entry
        self.search_entry.focus_set()

    def create_widgets(self):
        """Create dialog widgets"""
        # Search bar frame
        search_frame = ttk.Frame(self.dialog, padding="10")
        search_frame.pack(fill="x")

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.search_button = ttk.Button(search_frame, text="Search", command=self.search)
        self.search_button.pack(side="left", padx=5)

        # Progress bar (hidden initially)
        self.progress = ttk.Progressbar(self.dialog, mode="indeterminate")

        # Results frame
        results_frame = ttk.Frame(self.dialog, padding="10")
        results_frame.pack(fill="both", expand=True)

        # Results listbox with scrollbar
        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.results_listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set, height=15, selectmode="single"
        )
        self.results_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.results_listbox.yview)

        # Bind selection event
        self.results_listbox.bind("<<ListboxSelect>>", self.on_select)
        self.results_listbox.bind("<Double-Button-1>", lambda e: self.view_details())

        # Details frame
        details_frame = ttk.LabelFrame(results_frame, text="Details", padding="10")
        details_frame.pack(fill="x", pady=(10, 0))

        self.details_text = tk.Text(details_frame, height=6, wrap="word", state="disabled")
        self.details_text.pack(fill="both", expand=True)

        # Button frame
        button_frame = ttk.Frame(self.dialog, padding="10")
        button_frame.pack(fill="x")

        self.import_button = ttk.Button(
            button_frame, text="Import Selected", command=self.import_selected, state="disabled"
        )
        self.import_button.pack(side="left", padx=5)

        self.view_button = ttk.Button(
            button_frame, text="View on MAL", command=self.open_mal_page, state="disabled"
        )
        self.view_button.pack(side="left", padx=5)

        ttk.Button(button_frame, text="Close", command=self.close).pack(side="right", padx=5)

        # Status label
        self.status_label = ttk.Label(
            self.dialog, text="Enter a search term and press Search", relief="sunken", anchor="w"
        )
        self.status_label.pack(fill="x", padx=10, pady=(0, 10))

    def search(self):
        """Perform MAL search"""
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Search", "Please enter a search term")
            return

        # Clear previous results
        self.results_listbox.delete(0, tk.END)
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.config(state="disabled")
        self.search_results = []
        self.selected_anime = None
        self.import_button.config(state="disabled")
        self.view_button.config(state="disabled")

        # Show progress
        self.progress.pack(fill="x", padx=10, pady=5)
        self.progress.start()
        self.search_button.config(state="disabled")
        self.status_label.config(text="Searching...")

        # Perform search in background thread
        thread = threading.Thread(target=self._search_thread, args=(query,))
        thread.daemon = True
        thread.start()

    def _search_thread(self, query: str):
        """Background thread for searching"""
        try:
            results = self.mal_service.search_anime(query, limit=20)
            self.dialog.after(0, self._search_complete, results)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            self.dialog.after(0, self._search_error, str(e))

    def _search_complete(self, results: List[Dict]):
        """Handle search completion"""
        # Hide progress
        self.progress.stop()
        self.progress.pack_forget()
        self.search_button.config(state="normal")

        if not results:
            self.status_label.config(text="No results found")
            return

        # Populate results
        self.search_results = results
        for anime in results:
            title = anime.get("title", "Unknown")
            title_english = anime.get("title_english", "")
            episodes = anime.get("episodes", "?")
            score = anime.get("score", "N/A")

            # Format display string
            if title_english and title_english != title:
                display = f"{title} ({title_english}) - Episodes: {episodes}, Score: {score}"
            else:
                display = f"{title} - Episodes: {episodes}, Score: {score}"

            self.results_listbox.insert(tk.END, display)

        self.status_label.config(text=f"Found {len(results)} results")

    def _search_error(self, error_msg: str):
        """Handle search error"""
        # Hide progress
        self.progress.stop()
        self.progress.pack_forget()
        self.search_button.config(state="normal")

        # Parse error type for user-friendly message
        if "rate limit" in error_msg.lower():
            self.status_label.config(text="Rate limit reached. Please wait a minute.")
            messagebox.showwarning(
                "Rate Limit",
                "MAL API rate limit reached (60 requests/minute).\n\n"
                "Please wait a minute before searching again.",
            )
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            self.status_label.config(text="Network error. Check connection.")
            messagebox.showerror(
                "Network Error",
                "Could not connect to MyAnimeList.\n\n" "Please check your internet connection.",
            )
        elif "not found" in error_msg.lower():
            self.status_label.config(text="No results found")
        elif "server error" in error_msg.lower() or "500" in error_msg:
            self.status_label.config(text="MAL server error. Try again later.")
            messagebox.showerror(
                "Server Error",
                "MyAnimeList servers are experiencing issues.\n\n" "Please try again later.",
            )
        else:
            self.status_label.config(text=f"Search failed: {error_msg}")

    def on_select(self, event):
        """Handle selection change"""
        selection = self.results_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        self.selected_anime = self.search_results[index]

        # Enable buttons
        self.import_button.config(state="normal")
        self.view_button.config(state="normal")

        # Show details
        self.show_details(self.selected_anime)

    def show_details(self, anime: Dict):
        """Show anime details in text widget"""
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)

        # Format details
        details = []

        # Titles
        title = anime.get("title", "Unknown")
        title_english = anime.get("title_english")
        if title_english and title_english != title:
            details.append(f"Title: {title} ({title_english})")
        else:
            details.append(f"Title: {title}")

        # Basic info
        details.append(f"Type: {anime.get('type', 'Unknown')}")
        details.append(f"Episodes: {anime.get('episodes', 'Unknown')}")
        details.append(f"Status: {anime.get('status', 'Unknown')}")
        details.append(f"Score: {anime.get('score', 'N/A')}")

        # Dates
        aired = anime.get("aired", {})
        if aired.get("from"):
            details.append(f"Aired: {aired.get('from', 'Unknown')} to {aired.get('to', 'Ongoing')}")

        # Synopsis (truncated)
        synopsis = anime.get("synopsis", "No synopsis available")
        if len(synopsis) > 200:
            synopsis = synopsis[:200] + "..."
        details.append(f"\nSynopsis: {synopsis}")

        self.details_text.insert("1.0", "\n".join(details))
        self.details_text.config(state="disabled")

    def view_details(self):
        """View detailed anime information"""
        if not self.selected_anime:
            return

        # Could open a detailed view dialog here
        # For now, just show what we have

    def import_selected(self):
        """Import selected anime to local database"""
        if not self.selected_anime:
            return

        # Show progress
        self.import_button.config(state="disabled")
        self.status_label.config(text="Importing anime...")
        self.dialog.update()

        # Extract data
        mal_id = self.selected_anime.get("mal_id")
        title = self.selected_anime.get("title", "Unknown")
        title_english = self.selected_anime.get("title_english")
        title_japanese = self.selected_anime.get("title_japanese")
        total_episodes = self.selected_anime.get("episodes")
        synopsis = self.selected_anime.get("synopsis", "")
        score = self.selected_anime.get("score")

        # Get genres
        genres = []
        if "genres" in self.selected_anime:
            genres = [g["name"] for g in self.selected_anime.get("genres", [])]

        # Get studios
        studio = None
        if self.selected_anime.get("studios"):
            studio = self.selected_anime["studios"][0].get("name")

        # Get aired dates
        aired_from = None
        aired_to = None
        if "aired" in self.selected_anime:
            aired = self.selected_anime["aired"]
            aired_from = aired.get("from")
            aired_to = aired.get("to")

        # Get season and year
        season = self.selected_anime.get("season")
        year = self.selected_anime.get("year")

        # Get source and rating
        source = self.selected_anime.get("source")
        rating = self.selected_anime.get("rating")

        # Get image URL
        images = self.selected_anime.get("images", {})
        jpg_images = images.get("jpg", {})
        image_url = jpg_images.get("image_url", "")

        # Check if already exists
        existing = self.anime_service.search_anime(title)
        if existing:
            response = messagebox.askyesno(
                "Anime Exists",
                f"'{title}' already exists in your list.\nDo you want to update it with MAL data?",
            )
            if not response:
                self.import_button.config(state="normal")
                self.status_label.config(text="Import cancelled")
                return

            # Update existing with MAL data
            anime = existing[0]
            updates = {}

            # Only update fields that are missing or empty
            if mal_id and not anime.mal_id:
                updates["mal_id"] = mal_id
            if title_english and not anime.title_english:
                updates["title_english"] = title_english
            if title_japanese and not anime.title_japanese:
                updates["title_japanese"] = title_japanese
            if synopsis and not anime.synopsis:
                updates["synopsis"] = synopsis
            if genres and not anime.genres:
                updates["genres"] = genres
            if studio and not anime.studio:
                updates["studio"] = studio
            if image_url and not anime.image_url:
                updates["image_url"] = image_url
            if total_episodes and not anime.total_episodes:
                updates["total_episodes"] = total_episodes
            if season and not anime.season:
                updates["season"] = season
            if year and not anime.year:
                updates["year"] = year
            if source and not anime.source:
                updates["source"] = source
            if rating and not anime.rating:
                updates["rating"] = rating

            if updates:
                success, message = self.anime_service.update_anime(anime.id, **updates)
                if success:
                    # Download image if needed
                    if image_url:
                        from services.image_service import ImageService

                        image_cache_dir = Path.home() / ".animetracker" / "image_cache"
                        image_service = ImageService(image_cache_dir)
                        image_service.queue_download(
                            image_url, image_cache_dir / f"mal_{mal_id}.jpg"
                        )

                    messagebox.showinfo(
                        "Update Success", f"Successfully updated '{title}' with MAL data"
                    )
                    self.close()
                else:
                    messagebox.showerror("Update Failed", f"Failed to update: {message}")
                    self.import_button.config(state="normal")
                    self.status_label.config(text="Update failed")
            else:
                messagebox.showinfo("No Updates", "No new data to update")
                self.import_button.config(state="normal")
                self.status_label.config(text="No updates needed")
            return

        # Add to database with all MAL data
        success, message, anime_id = self.anime_service.add_anime(
            title=title,
            status="Plan to Watch",
            episodes_watched=0,
            total_episodes=total_episodes if total_episodes else None,
            mal_id=mal_id,
            title_english=title_english,
            title_japanese=title_japanese,
            synopsis=synopsis if synopsis else None,
            genres=genres,
            studio=studio,
            image_url=image_url,
            season=season,
            year=year,
            source=source,
            rating=rating,
        )

        if success:
            # Download cover image in background
            if image_url:
                try:
                    from services.image_service import ImageService

                    image_cache_dir = Path.home() / ".animetracker" / "image_cache"
                    image_service = ImageService(image_cache_dir)
                    image_service.queue_download(image_url, image_cache_dir / f"mal_{mal_id}.jpg")
                except Exception as e:
                    logger.warning(f"Failed to queue image download: {e}")

            messagebox.showinfo("Import Success", f"Successfully imported '{title}'")
            self.close()
        else:
            messagebox.showerror("Import Failed", f"Failed to import: {message}")
            self.import_button.config(state="normal")
            self.status_label.config(text="Import failed")

    def open_mal_page(self):
        """Open anime page on MAL website"""
        if not self.selected_anime:
            return

        mal_id = self.selected_anime.get("mal_id")
        if mal_id:
            import webbrowser

            url = f"https://myanimelist.net/anime/{mal_id}"
            webbrowser.open(url)

    def close(self):
        """Close dialog"""
        self.dialog.destroy()
