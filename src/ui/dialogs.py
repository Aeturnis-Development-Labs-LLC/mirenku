"""Dialog windows for Anime Tracker"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
from models.anime import Anime
from services.anime_service import AnimeService


class AddAnimeDialog:
    """Dialog for adding new anime"""
    
    def __init__(self, parent, service: AnimeService):
        """Initialize add anime dialog
        
        Args:
            parent: Parent window
            service: Anime service instance
        """
        self.service = service
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Anime")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Variables
        self.title_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Plan to Watch")
        self.episodes_var = tk.StringVar(value="0")
        self.total_var = tk.StringVar()
        self.score_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        
        # Create form
        self._create_form()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Focus on title field
        self.title_entry.focus()
    
    def _create_form(self):
        """Create form fields"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Title:*").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.title_entry = ttk.Entry(main_frame, textvariable=self.title_var, width=50)
        self.title_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Status
        ttk.Label(main_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.status_combo = ttk.Combobox(
            main_frame,
            textvariable=self.status_var,
            values=Anime.STATUS_OPTIONS,
            state="readonly",
            width=20
        )
        self.status_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Episodes
        ttk.Label(main_frame, text="Episodes:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        episode_frame = ttk.Frame(main_frame)
        episode_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.episodes_spin = ttk.Spinbox(
            episode_frame,
            textvariable=self.episodes_var,
            from_=0,
            to=9999,
            width=10
        )
        self.episodes_spin.pack(side=tk.LEFT)
        
        ttk.Label(episode_frame, text=" / ").pack(side=tk.LEFT, padx=5)
        
        self.total_entry = ttk.Entry(
            episode_frame,
            textvariable=self.total_var,
            width=10
        )
        self.total_entry.pack(side=tk.LEFT)
        
        ttk.Label(episode_frame, text="(leave blank if unknown)").pack(side=tk.LEFT, padx=10)
        
        # Score
        ttk.Label(main_frame, text="Score:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        score_frame = ttk.Frame(main_frame)
        score_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        self.score_spin = ttk.Spinbox(
            score_frame,
            textvariable=self.score_var,
            from_=0,
            to=10,
            width=10
        )
        self.score_spin.pack(side=tk.LEFT)
        
        ttk.Label(score_frame, text=" / 10").pack(side=tk.LEFT, padx=5)
        
        # Notes
        ttk.Label(main_frame, text="Notes:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        
        self.notes_text = tk.Text(main_frame, width=50, height=8)
        self.notes_text.grid(row=4, column=1, columnspan=2, pady=5)
        
        # Scrollbar for notes
        notes_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.notes_text.yview)
        notes_scroll.grid(row=4, column=3, sticky=tk.NS, pady=5)
        self.notes_text.config(yscrollcommand=notes_scroll.set)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, pady=10)
        
        ttk.Button(
            button_frame,
            text="Add",
            command=self.add_anime,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to add
        self.dialog.bind("<Return>", lambda e: self.add_anime())
    
    def add_anime(self):
        """Add anime with validation"""
        # Get values
        title = self.title_var.get().strip()
        status = self.status_var.get()
        
        # Validate title
        if not title:
            messagebox.showerror("Error", "Title is required", parent=self.dialog)
            self.title_entry.focus()
            return
        
        # Parse episodes
        try:
            episodes = int(self.episodes_var.get() or 0)
        except ValueError:
            episodes = 0
        
        # Parse total episodes
        total_episodes = None
        if self.total_var.get():
            try:
                total_episodes = int(self.total_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid total episodes", parent=self.dialog)
                return
        
        # Parse score
        score = None
        if self.score_var.get():
            try:
                score = int(self.score_var.get())
                if score < 0 or score > 10:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Error", "Score must be between 0 and 10", parent=self.dialog)
                return
        
        # Get notes
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        # Add anime
        success, message, anime_id = self.service.add_anime(
            title=title,
            status=status,
            episodes_watched=episodes,
            total_episodes=total_episodes,
            score=score,
            notes=notes if notes else None
        )
        
        if success:
            self.result = title
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", message, parent=self.dialog)


class EditAnimeDialog:
    """Dialog for editing anime"""
    
    def __init__(self, parent, service: AnimeService, anime: Anime):
        """Initialize edit anime dialog
        
        Args:
            parent: Parent window
            service: Anime service instance
            anime: Anime to edit
        """
        self.service = service
        self.anime = anime
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit: {anime.title}")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Variables
        self.title_var = tk.StringVar(value=anime.title)
        self.status_var = tk.StringVar(value=anime.status)
        self.episodes_var = tk.StringVar(value=str(anime.episodes_watched))
        self.total_var = tk.StringVar(value=str(anime.total_episodes) if anime.total_episodes else "")
        self.score_var = tk.StringVar(value=str(anime.score) if anime.score else "")
        self.notes_var = tk.StringVar(value=anime.notes or "")
        
        # Create form
        self._create_form()
        
        # Load notes
        if anime.notes:
            self.notes_text.insert("1.0", anime.notes)
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Focus on title field
        self.title_entry.focus()
        self.title_entry.select_range(0, tk.END)
    
    def _create_form(self):
        """Create form fields"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Title:*").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.title_entry = ttk.Entry(main_frame, textvariable=self.title_var, width=50)
        self.title_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Status
        ttk.Label(main_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.status_combo = ttk.Combobox(
            main_frame,
            textvariable=self.status_var,
            values=Anime.STATUS_OPTIONS,
            state="readonly",
            width=20
        )
        self.status_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Episodes
        ttk.Label(main_frame, text="Episodes:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        episode_frame = ttk.Frame(main_frame)
        episode_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.episodes_spin = ttk.Spinbox(
            episode_frame,
            textvariable=self.episodes_var,
            from_=0,
            to=9999,
            width=10
        )
        self.episodes_spin.pack(side=tk.LEFT)
        
        ttk.Label(episode_frame, text=" / ").pack(side=tk.LEFT, padx=5)
        
        self.total_entry = ttk.Entry(
            episode_frame,
            textvariable=self.total_var,
            width=10
        )
        self.total_entry.pack(side=tk.LEFT)
        
        ttk.Label(episode_frame, text="(leave blank if unknown)").pack(side=tk.LEFT, padx=10)
        
        # Score
        ttk.Label(main_frame, text="Score:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        score_frame = ttk.Frame(main_frame)
        score_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        self.score_spin = ttk.Spinbox(
            score_frame,
            textvariable=self.score_var,
            from_=0,
            to=10,
            width=10
        )
        self.score_spin.pack(side=tk.LEFT)
        
        ttk.Label(score_frame, text=" / 10").pack(side=tk.LEFT, padx=5)
        
        # Notes
        ttk.Label(main_frame, text="Notes:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        
        self.notes_text = tk.Text(main_frame, width=50, height=8)
        self.notes_text.grid(row=4, column=1, columnspan=2, pady=5)
        
        # Scrollbar for notes
        notes_scroll = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.notes_text.yview)
        notes_scroll.grid(row=4, column=3, sticky=tk.NS, pady=5)
        self.notes_text.config(yscrollcommand=notes_scroll.set)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(side=tk.BOTTOM, pady=10)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self.save_anime,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to save
        self.dialog.bind("<Return>", lambda e: self.save_anime())
    
    def save_anime(self):
        """Save anime changes"""
        # Get values
        title = self.title_var.get().strip()
        status = self.status_var.get()
        
        # Validate title
        if not title:
            messagebox.showerror("Error", "Title is required", parent=self.dialog)
            self.title_entry.focus()
            return
        
        # Parse episodes
        try:
            episodes = int(self.episodes_var.get() or 0)
        except ValueError:
            episodes = 0
        
        # Parse total episodes
        total_episodes = None
        if self.total_var.get():
            try:
                total_episodes = int(self.total_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid total episodes", parent=self.dialog)
                return
        
        # Parse score
        score = None
        if self.score_var.get():
            try:
                score = int(self.score_var.get())
                if score < 0 or score > 10:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Error", "Score must be between 0 and 10", parent=self.dialog)
                return
        
        # Get notes
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        # Update anime
        success, message = self.service.update_anime(
            self.anime.id,
            title=title,
            status=status,
            episodes_watched=episodes,
            total_episodes=total_episodes,
            score=score,
            notes=notes if notes else None
        )
        
        if success:
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", message, parent=self.dialog)