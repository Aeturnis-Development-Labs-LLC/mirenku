"""About/Diagnostics dialog for Mirenku"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
import os
from pathlib import Path
import platform


class AboutDialog:
    """About and diagnostics dialog"""
    
    def __init__(self, parent, config, db):
        """Initialize about dialog
        
        Args:
            parent: Parent window
            config: Config instance
            db: Database instance
        """
        self.parent = parent
        self.config = config
        self.db = db
        
        # Get version from __init__.py
        try:
            from __init__ import __version__
        except ImportError:
            __version__ = "Unknown"
        self.version = __version__
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("About Mirenku")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self.create_widgets()
        
        # Focus and bind escape
        self.dialog.focus_set()
        self.dialog.bind('<Escape>', lambda e: self.close())
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # About tab
        about_frame = ttk.Frame(notebook)
        notebook.add(about_frame, text="About")
        self.create_about_tab(about_frame)
        
        # Diagnostics tab
        diag_frame = ttk.Frame(notebook)
        notebook.add(diag_frame, text="Diagnostics")
        self.create_diagnostics_tab(diag_frame)
        
        # Paths tab
        paths_frame = ttk.Frame(notebook)
        notebook.add(paths_frame, text="Paths")
        self.create_paths_tab(paths_frame)
        
        # Close button
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Close",
            command=self.close
        ).pack(side='right')
    
    def create_about_tab(self, parent):
        """Create about tab content"""
        # Logo/Title
        title_label = ttk.Label(
            parent,
            text="Mirenku",
            font=('Helvetica', 18, 'bold')
        )
        title_label.pack(pady=(20, 5))
        
        version_label = ttk.Label(
            parent,
            text=f"Version {self.version}",
            font=('Helvetica', 12)
        )
        version_label.pack(pady=(0, 20))
        
        # Description
        desc_text = """A simple, offline-first desktop application
for tracking your anime viewing progress.

Track episodes, manage your watchlist,
and keep notes on your favorite shows."""
        
        desc_label = ttk.Label(
            parent,
            text=desc_text,
            justify='center'
        )
        desc_label.pack(pady=10)
        
        # Credits
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=50, pady=20)
        
        credits_label = ttk.Label(
            parent,
            text="Developed by",
            font=('Helvetica', 10)
        )
        credits_label.pack()
        
        company_label = ttk.Label(
            parent,
            text="Aeturnis Development Labs LLC",
            font=('Helvetica', 12, 'bold')
        )
        company_label.pack(pady=5)
        
        email_label = ttk.Label(
            parent,
            text="projects@aeturnis.dev",
            font=('Helvetica', 10),
            foreground='blue',
            cursor='hand2'
        )
        email_label.pack()
        
        # License
        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=50, pady=20)
        
        license_label = ttk.Label(
            parent,
            text="Licensed under Prosperity Public License 3.0.0",
            font=('Helvetica', 10)
        )
        license_label.pack()
        
        github_label = ttk.Label(
            parent,
            text="github.com/Aeturnis-Development-Labs-LLC/mirenku",
            font=('Helvetica', 9),
            foreground='blue',
            cursor='hand2'
        )
        github_label.pack(pady=5)
    
    def create_diagnostics_tab(self, parent):
        """Create diagnostics tab content"""
        # Create scrolled text widget
        text_widget = scrolledtext.ScrolledText(
            parent,
            wrap='word',
            width=70,
            height=20,
            font=('Consolas', 9)
        )
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Gather diagnostic info
        diag_info = []
        
        # System Information
        diag_info.append("=== SYSTEM INFORMATION ===")
        diag_info.append(f"Platform: {platform.system()} {platform.release()}")
        diag_info.append(f"Architecture: {platform.machine()}")
        diag_info.append(f"Python Version: {sys.version}")
        diag_info.append(f"Python Executable: {sys.executable}")
        diag_info.append("")
        
        # Application Information
        diag_info.append("=== APPLICATION ===")
        diag_info.append(f"Version: {self.version}")
        diag_info.append(f"Running as: {'Executable' if getattr(sys, 'frozen', False) else 'Script'}")
        diag_info.append("")
        
        # Database Information
        diag_info.append("=== DATABASE ===")
        db_path = self.config.get_db_path()
        diag_info.append(f"Path: {db_path}")
        diag_info.append(f"Exists: {db_path.exists()}")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            diag_info.append(f"Size: {size_mb:.2f} MB")
        
        # Get anime count
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM anime")
                count = cursor.fetchone()['count']
                diag_info.append(f"Anime Count: {count}")
        except:
            diag_info.append("Anime Count: Error reading database")
        diag_info.append("")
        
        # Configuration
        diag_info.append("=== CONFIGURATION ===")
        diag_info.append(f"Auto-save: {self.config.get('auto_save', True)}")
        diag_info.append(f"Theme: {self.config.get('theme', 'light')}")
        diag_info.append(f"Last Filter: {self.config.get('last_filter', 'All')}")
        diag_info.append(f"Sort Column: {self.config.get('sort_column', 'title')}")
        diag_info.append("")
        
        # Memory Usage
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            diag_info.append("=== MEMORY ===")
            diag_info.append(f"Current Usage: {memory_mb:.1f} MB")
            diag_info.append("")
        except ImportError:
            pass
        
        # Insert diagnostic info
        text_widget.insert('1.0', '\n'.join(diag_info))
        text_widget.config(state='disabled')
    
    def create_paths_tab(self, parent):
        """Create paths tab content"""
        # Create frame with grid
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        paths = [
            ("Data Directory", self.config.get_data_directory()),
            ("Database", self.config.get_db_path()),
            ("Config File", self.config.config_file),
            ("Backup Directory", self.config.get_backup_dir()),
            ("Log Directory", self.config.get_data_directory() / "logs"),
        ]
        
        # Add export directory if it exists
        export_dir = self.config.get_data_directory() / "exports"
        if export_dir.exists():
            paths.append(("Export Directory", export_dir))
        
        # Create labels for each path
        for i, (label, path) in enumerate(paths):
            ttk.Label(
                frame,
                text=f"{label}:",
                font=('Helvetica', 10, 'bold')
            ).grid(row=i*2, column=0, sticky='w', pady=(10, 2))
            
            # Create entry with path
            entry = ttk.Entry(frame, width=60)
            entry.insert(0, str(path))
            entry.config(state='readonly')
            entry.grid(row=i*2+1, column=0, sticky='ew', padx=(20, 0))
            
            # Add "exists" indicator
            exists = path.exists() if isinstance(path, Path) else False
            status = "✓" if exists else "✗"
            color = 'green' if exists else 'red'
            
            status_label = ttk.Label(
                frame,
                text=status,
                foreground=color,
                font=('Helvetica', 12, 'bold')
            )
            status_label.grid(row=i*2+1, column=1, padx=5)
        
        # Configure grid weights
        frame.columnconfigure(0, weight=1)
    
    def close(self):
        """Close dialog"""
        self.dialog.destroy()