"""MAL Authentication Dialog for OAuth2 login"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MALAuthDialog:
    """Dialog for MAL OAuth2 authentication"""
    
    def __init__(self, parent, oauth_client):
        """Initialize MAL auth dialog
        
        Args:
            parent: Parent window
            oauth_client: MAL OAuth2 client instance
        """
        self.parent = parent
        self.oauth_client = oauth_client
        self.authenticated = False
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Connect to MyAnimeList")
        self.dialog.geometry("500x420")
        self.dialog.resizable(False, False)
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 210
        self.dialog.geometry(f"500x420+{x}+{y}")
        
        self.create_widgets()
        self.check_auth_status()
        
        # Bind escape key
        self.dialog.bind('<Escape>', lambda e: self.close())
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="MyAnimeList Authentication",
            font=('TkDefaultFont', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Status frame
        self.status_frame = ttk.LabelFrame(main_frame, text="Status", padding="15")
        self.status_frame.pack(fill='x', pady=(0, 20))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="Checking authentication status...",
            font=('TkDefaultFont', 10)
        )
        self.status_label.pack()
        
        self.user_label = ttk.Label(
            self.status_frame,
            text="",
            font=('TkDefaultFont', 9)
        )
        self.user_label.pack(pady=(5, 0))
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding="15")
        info_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        info_text = """Connecting to MyAnimeList allows you to:
• Sync your anime list
• Push local changes to MAL
• Pull updates from MAL

Click 'Connect to MAL' to:
1. Open your browser
2. Log in to MyAnimeList
3. Authorize the app"""
        
        info_label = ttk.Label(
            info_frame,
            text=info_text,
            justify='left',
            wraplength=430
        )
        info_label.pack()
        
        # Progress bar (hidden initially)
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate'
        )
        
        # Button frame with explicit height
        button_frame = tk.Frame(main_frame, height=60)
        button_frame.pack(fill='x', pady=(10, 0))
        button_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Create buttons with explicit height using place geometry
        self.auth_button = tk.Button(
            button_frame,
            text="Connect to MAL",
            command=self.start_authentication,
            state='disabled',
            bg='#4CAF50',
            fg='white',
            font=('Arial', 11, 'bold'),
            relief=tk.RAISED,
            bd=2
        )
        self.auth_button.place(x=10, y=10, width=140, height=40)
        
        self.disconnect_button = tk.Button(
            button_frame,
            text="Disconnect",
            command=self.disconnect,
            state='disabled',
            bg='#f44336',
            fg='white',
            font=('Arial', 11, 'bold'),
            relief=tk.RAISED,
            bd=2
        )
        self.disconnect_button.place(x=160, y=10, width=120, height=40)
        
        close_btn = tk.Button(
            button_frame,
            text="Close",
            command=self.close,
            font=('Arial', 11),
            relief=tk.RAISED,
            bd=2
        )
        close_btn.place(x=400, y=10, width=80, height=40)
    
    def check_auth_status(self):
        """Check current authentication status"""
        if self.oauth_client.is_authenticated():
            self.authenticated = True
            self.status_label.config(
                text="✓ Connected to MyAnimeList",
                foreground='green'
            )
            
            # Try to get user info
            self.user_label.config(text="Fetching user information...")
            
            # Enable/disable buttons
            self.auth_button.config(state='disabled')
            self.disconnect_button.config(state='normal', bg='#f44336')
            
            # Fetch user info in background
            threading.Thread(target=self._fetch_user_info, daemon=True).start()
        else:
            self.authenticated = False
            self.status_label.config(
                text="✗ Not connected to MyAnimeList",
                foreground='red'
            )
            self.user_label.config(text="")
            
            # Enable/disable buttons
            self.auth_button.config(state='normal', bg='#4CAF50')
            self.disconnect_button.config(state='disabled')
    
    def _fetch_user_info(self):
        """Fetch user information from MAL"""
        try:
            # Get user info
            user_data = self.oauth_client.make_api_request("/users/@me")
            
            if user_data:
                username = user_data.get('name', 'Unknown')
                joined = user_data.get('joined_at', 'Unknown')
                
                self.dialog.after(0, lambda: self.user_label.config(
                    text=f"Logged in as: {username}"
                ))
            else:
                self.dialog.after(0, lambda: self.user_label.config(
                    text="Unable to fetch user information"
                ))
        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            self.dialog.after(0, lambda: self.user_label.config(
                text="Error fetching user information"
            ))
    
    def start_authentication(self):
        """Start OAuth2 authentication flow"""
        logger.info("Starting authentication flow...")
        
        # Disable button and show progress
        self.auth_button.config(state='disabled')
        self.progress.pack(pady=10)
        self.progress.start()
        
        self.status_label.config(
            text="Opening browser for authentication...",
            foreground='blue'
        )
        
        # Start auth in background thread
        thread = threading.Thread(target=self._authenticate_thread)
        thread.daemon = True
        thread.start()
    
    def _authenticate_thread(self):
        """Background thread for authentication"""
        try:
            # Update status
            self.dialog.after(0, lambda: self.status_label.config(
                text="Please authorize in your browser...",
                foreground='blue'
            ))
            
            # Perform authentication
            success = self.oauth_client.authorize()
            
            # Update UI on main thread
            self.dialog.after(0, lambda: self._auth_complete(success))
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            self.dialog.after(0, lambda: self._auth_complete(False, str(e)))
    
    def _auth_complete(self, success: bool, error: Optional[str] = None):
        """Handle authentication completion
        
        Args:
            success: Whether authentication was successful
            error: Error message if failed
        """
        # Hide progress
        self.progress.stop()
        self.progress.pack_forget()
        
        if success:
            self.authenticated = True
            self.status_label.config(
                text="✓ Successfully connected to MyAnimeList!",
                foreground='green'
            )
            
            # Update buttons
            self.auth_button.config(state='disabled')
            self.disconnect_button.config(state='normal', bg='#f44336')
            
            # Fetch user info
            threading.Thread(target=self._fetch_user_info, daemon=True).start()
            
            messagebox.showinfo(
                "Success",
                "Successfully connected to MyAnimeList!\n\n"
                "You can now sync your anime list."
            )
        else:
            self.authenticated = False
            self.status_label.config(
                text="✗ Authentication failed",
                foreground='red'
            )
            
            # Re-enable auth button
            self.auth_button.config(state='normal', bg='#4CAF50')
            
            error_msg = error or "Unknown error"
            messagebox.showerror(
                "Authentication Failed",
                f"Failed to connect to MyAnimeList:\n\n{error_msg}"
            )
    
    def disconnect(self):
        """Disconnect from MAL"""
        response = messagebox.askyesno(
            "Disconnect",
            "Are you sure you want to disconnect from MyAnimeList?\n\n"
            "This will clear your authentication tokens and "
            "disable synchronization."
        )
        
        if response:
            self.oauth_client.logout()
            self.authenticated = False
            
            self.status_label.config(
                text="✗ Disconnected from MyAnimeList",
                foreground='red'
            )
            self.user_label.config(text="")
            
            # Update buttons
            self.auth_button.config(state='normal', bg='#4CAF50')
            self.disconnect_button.config(state='disabled')
            
            messagebox.showinfo(
                "Disconnected",
                "Successfully disconnected from MyAnimeList."
            )
    
    def close(self):
        """Close dialog"""
        self.dialog.destroy()


class MALAuthManager:
    """Manager for MAL authentication state"""
    
    def __init__(self, config_dir: Path, client_id: Optional[str] = None):
        """Initialize auth manager
        
        Args:
            config_dir: Configuration directory
            client_id: MAL client ID (if not provided, will use default)
        """
        self.config_dir = config_dir
        # Use provided client_id, or default app client ID, or get from config
        self.client_id = client_id or "77dcb3ef6a0b47401c5d76e5957bc425" or self._get_client_id()
        
        if self.client_id:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from services.mal_oauth2_client import MALOAuth2Client
            token_path = config_dir / "mal_tokens.json"
            self.oauth_client = MALOAuth2Client(self.client_id, token_path)
        else:
            self.oauth_client = None
    
    def _get_client_id(self) -> Optional[str]:
        """Get client ID from config or prompt user
        
        Returns:
            Client ID or None
        """
        # Check if client ID is saved in config
        config_file = self.config_dir / "mal_config.json"
        
        if config_file.exists():
            import json
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('client_id')
            except Exception as e:
                logger.error(f"Failed to load MAL config: {e}")
        
        # Prompt user for client ID
        return self._prompt_for_client_id()
    
    def _prompt_for_client_id(self) -> Optional[str]:
        """Prompt user to enter client ID
        
        Returns:
            Client ID or None
        """
        import tkinter.simpledialog as simpledialog
        
        client_id = simpledialog.askstring(
            "MAL Client ID",
            "Please enter your MyAnimeList Client ID:\n\n"
            "You can get this by registering your app at:\n"
            "https://myanimelist.net/apiconfig\n\n"
            "Client ID:"
        )
        
        if client_id:
            # Save client ID
            self._save_client_id(client_id)
            return client_id
        
        return None
    
    def _save_client_id(self, client_id: str):
        """Save client ID to config
        
        Args:
            client_id: MAL client ID
        """
        import json
        config_file = self.config_dir / "mal_config.json"
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config = {'client_id': client_id}
            with open(config_file, 'w') as f:
                json.dump(config, f)
                
            logger.info("Saved MAL client ID to config")
        except Exception as e:
            logger.error(f"Failed to save client ID: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if authenticated
        
        Returns:
            True if authenticated
        """
        return self.oauth_client and self.oauth_client.is_authenticated()
    
    def show_auth_dialog(self, parent) -> bool:
        """Show authentication dialog
        
        Args:
            parent: Parent window
            
        Returns:
            True if authenticated after dialog
        """
        if not self.oauth_client:
            messagebox.showerror(
                "Configuration Required",
                "MAL Client ID is required for authentication.\n\n"
                "Please register your app at:\n"
                "https://myanimelist.net/apiconfig"
            )
            return False
        
        dialog = MALAuthDialog(parent, self.oauth_client)
        parent.wait_window(dialog.dialog)
        
        return dialog.authenticated