# First-Run Protocol Registration Design

## Overview
Automatically handle protocol registration on first run with user consent, eliminating the need for separate PowerShell scripts.

## User Experience Flow

### First Launch
```
┌─────────────────────────────────────┐
│       Welcome to Mirenku!           │
│                                     │
│  To connect with MyAnimeList, we   │
│  need to register a protocol       │
│  handler (mirenku://)              │
│                                     │
│  This allows secure authentication │
│  without using localhost ports.    │
│                                     │
│  [✓] Register protocol handler     │
│      (Recommended)                  │
│                                     │
│  [Continue]  [Learn More]          │
└─────────────────────────────────────┘
```

### Subsequent Launches
- Check if protocol is registered
- If app moved/path changed, re-register silently
- Settings menu allows manual register/unregister

## Implementation Design

### 1. First Run Detection
```python
# src/utils/first_run.py
import json
from pathlib import Path
from typing import Dict, Optional

class FirstRunManager:
    """Manages first-run experience and app configuration"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "app_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load app configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "first_run": True,
            "version": "0.4.0",
            "protocol_registered": False,
            "last_exe_path": None,
            "settings": {}
        }
    
    def is_first_run(self) -> bool:
        """Check if this is the first run"""
        return self.config.get("first_run", True)
    
    def has_moved(self) -> bool:
        """Check if executable has moved"""
        import sys
        current_path = sys.executable if getattr(sys, 'frozen', False) else None
        last_path = self.config.get("last_exe_path")
        return current_path and current_path != last_path
    
    def mark_completed(self, register_protocol: bool = True):
        """Mark first run as completed"""
        import sys
        self.config["first_run"] = False
        self.config["protocol_registered"] = register_protocol
        if getattr(sys, 'frozen', False):
            self.config["last_exe_path"] = sys.executable
        self._save_config()
    
    def _save_config(self):
        """Save configuration"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
```

### 2. Protocol Registration Manager
```python
# src/utils/protocol_manager.py
import sys
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class ProtocolManager:
    """Manages mirenku:// protocol registration"""
    
    PROTOCOL = "mirenku"
    
    def __init__(self):
        self.exe_path = self._get_exe_path()
    
    def _get_exe_path(self) -> str:
        """Get current executable path"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            # Development mode - use Python with main.py
            return f'"{sys.executable}" "{Path(__file__).parent.parent / "main.py"}"'
    
    def is_registered(self) -> bool:
        """Check if protocol is registered and points to current exe"""
        if sys.platform != 'win32':
            return False
            
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{self.PROTOCOL}\\shell\\open\\command"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "")
                # Check if registered path matches current exe
                return self.exe_path in value or value in self.exe_path
        except:
            return False
    
    def register(self, silent: bool = False) -> Tuple[bool, Optional[str]]:
        """Register protocol handler
        
        Returns:
            (success, error_message)
        """
        if sys.platform != 'win32':
            return False, "Protocol registration only supported on Windows"
        
        try:
            import winreg
            
            base = f"Software\\Classes\\{self.PROTOCOL}"
            
            # Create main key
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, base) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Mirenku Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            # Set icon
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f"{base}\\DefaultIcon") as key:
                icon_path = f"{self.exe_path},0" if getattr(sys, 'frozen', False) else ""
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon_path)
            
            # Set command
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f"{base}\\shell\\open\\command") as key:
                cmd = f'"{self.exe_path}" "%1"'
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd)
            
            if not silent:
                logger.info(f"Registered {self.PROTOCOL}:// protocol handler")
            return True, None
            
        except Exception as e:
            error = f"Failed to register protocol: {str(e)}"
            logger.error(error)
            return False, error
    
    def unregister(self) -> Tuple[bool, Optional[str]]:
        """Unregister protocol handler"""
        if sys.platform != 'win32':
            return False, "Protocol registration only supported on Windows"
        
        try:
            import winreg
            
            def delete_key_recursive(key, subkey_path):
                """Recursively delete registry key"""
                try:
                    with winreg.OpenKey(key, subkey_path, 0, winreg.KEY_ALL_ACCESS) as subkey:
                        # Get all subkeys
                        i = 0
                        while True:
                            try:
                                child = winreg.EnumKey(subkey, i)
                                delete_key_recursive(key, f"{subkey_path}\\{child}")
                            except OSError:
                                break
                    winreg.DeleteKey(key, subkey_path)
                except FileNotFoundError:
                    pass
            
            delete_key_recursive(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{self.PROTOCOL}"
            )
            
            logger.info(f"Unregistered {self.PROTOCOL}:// protocol handler")
            return True, None
            
        except Exception as e:
            error = f"Failed to unregister protocol: {str(e)}"
            logger.error(error)
            return False, error
```

### 3. First Run Dialog
```python
# src/ui/first_run_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

class FirstRunDialog:
    """First run setup dialog"""
    
    def __init__(self, parent):
        self.parent = parent
        self.register_protocol = tk.BooleanVar(value=True)
        self.result = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Welcome to Mirenku!")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 200
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        self.create_widgets()
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def create_widgets(self):
        """Create dialog widgets"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Welcome icon and title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame,
            text="Welcome to Mirenku!",
            font=('Arial', 16, 'bold')
        )
        title_label.pack()
        
        version_label = ttk.Label(
            title_frame,
            text="Anime Tracking Made Simple",
            font=('Arial', 10),
            foreground='gray'
        )
        version_label.pack()
        
        # Info text
        info_text = """To provide the best experience, Mirenku needs to set up a few things:

• Protocol Handler (mirenku://)
  Enables secure MyAnimeList authentication without
  using localhost ports or firewall issues.

• This is a one-time setup that allows:
  - Seamless OAuth2 authentication
  - Quick-add anime from your browser
  - Future streaming service integrations

The protocol handler is registered for your user account only
and doesn't require administrator privileges."""
        
        info_label = ttk.Label(
            main_frame,
            text=info_text,
            justify='left',
            wraplength=440
        )
        info_label.pack(pady=(0, 20))
        
        # Checkbox
        checkbox = ttk.Checkbutton(
            main_frame,
            text="Register mirenku:// protocol handler (Recommended)",
            variable=self.register_protocol,
            onvalue=True,
            offvalue=False
        )
        checkbox.pack(pady=(0, 20))
        
        # Note about moving
        note_frame = ttk.LabelFrame(main_frame, text="Note", padding="10")
        note_frame.pack(fill='x', pady=(0, 20))
        
        note_label = ttk.Label(
            note_frame,
            text="If you move Mirenku to a different folder later, "
                 "it will automatically update the registration.",
            wraplength=420,
            font=('Arial', 9),
            foreground='gray'
        )
        note_label.pack()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x')
        
        continue_btn = ttk.Button(
            button_frame,
            text="Continue",
            command=self.on_continue,
            width=15
        )
        continue_btn.pack(side='right', padx=(5, 0))
        
        learn_btn = ttk.Button(
            button_frame,
            text="Learn More",
            command=self.on_learn_more,
            width=15
        )
        learn_btn.pack(side='right')
        
        skip_btn = ttk.Button(
            button_frame,
            text="Skip",
            command=self.on_skip,
            width=10
        )
        skip_btn.pack(side='left')
    
    def on_continue(self):
        """Handle continue button"""
        self.result = self.register_protocol.get()
        self.dialog.destroy()
    
    def on_skip(self):
        """Handle skip button"""
        response = messagebox.askyesno(
            "Skip Setup?",
            "Without the protocol handler, you'll need to use "
            "the localhost method for MAL authentication, which "
            "may have firewall issues.\n\n"
            "You can enable it later in Settings.\n\n"
            "Skip setup?",
            parent=self.dialog
        )
        if response:
            self.result = False
            self.dialog.destroy()
    
    def on_cancel(self):
        """Handle window close"""
        self.on_skip()
    
    def on_learn_more(self):
        """Open documentation"""
        webbrowser.open("https://github.com/yourusername/mirenku/wiki/Protocol-Handler")
```

### 4. Settings Integration
```python
# Addition to settings dialog
class ProtocolSettingsFrame(ttk.LabelFrame):
    """Protocol handler settings"""
    
    def __init__(self, parent, protocol_manager):
        super().__init__(parent, text="Protocol Handler", padding="10")
        self.protocol_manager = protocol_manager
        
        self.create_widgets()
        self.update_status()
    
    def create_widgets(self):
        """Create settings widgets"""
        # Status label
        self.status_label = ttk.Label(self, text="")
        self.status_label.pack(anchor='w')
        
        # Info
        info = ttk.Label(
            self,
            text="The protocol handler enables OAuth and browser integration.",
            font=('Arial', 9),
            foreground='gray'
        )
        info.pack(anchor='w', pady=(5, 10))
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(anchor='w')
        
        self.register_btn = ttk.Button(
            button_frame,
            text="Register",
            command=self.register_protocol,
            width=12
        )
        self.register_btn.pack(side='left', padx=(0, 5))
        
        self.unregister_btn = ttk.Button(
            button_frame,
            text="Unregister",
            command=self.unregister_protocol,
            width=12
        )
        self.unregister_btn.pack(side='left')
        
        # Test button
        test_btn = ttk.Button(
            button_frame,
            text="Test",
            command=self.test_protocol,
            width=8
        )
        test_btn.pack(side='left', padx=(10, 0))
    
    def update_status(self):
        """Update registration status"""
        if self.protocol_manager.is_registered():
            self.status_label.config(
                text="✓ Protocol handler is registered",
                foreground='green'
            )
            self.register_btn.config(state='disabled')
            self.unregister_btn.config(state='normal')
        else:
            self.status_label.config(
                text="✗ Protocol handler not registered",
                foreground='red'
            )
            self.register_btn.config(state='normal')
            self.unregister_btn.config(state='disabled')
    
    def register_protocol(self):
        """Register protocol handler"""
        success, error = self.protocol_manager.register()
        if success:
            messagebox.showinfo(
                "Success",
                "Protocol handler registered successfully!"
            )
        else:
            messagebox.showerror(
                "Error",
                f"Failed to register protocol:\n{error}"
            )
        self.update_status()
    
    def unregister_protocol(self):
        """Unregister protocol handler"""
        response = messagebox.askyesno(
            "Unregister Protocol?",
            "This will remove the mirenku:// protocol handler.\n"
            "OAuth authentication will fall back to localhost method.\n\n"
            "Continue?"
        )
        if response:
            success, error = self.protocol_manager.unregister()
            if success:
                messagebox.showinfo(
                    "Success",
                    "Protocol handler unregistered."
                )
            else:
                messagebox.showerror(
                    "Error",
                    f"Failed to unregister:\n{error}"
                )
            self.update_status()
    
    def test_protocol(self):
        """Test protocol handler"""
        import webbrowser
        test_url = "mirenku://test?message=Protocol%20handler%20is%20working!"
        webbrowser.open(test_url)
```

### 5. Main App Integration
```python
# In main.py
def main():
    # ... existing setup ...
    
    # Initialize managers
    from utils.first_run import FirstRunManager
    from utils.protocol_manager import ProtocolManager
    
    first_run_mgr = FirstRunManager(config.get_config_directory())
    protocol_mgr = ProtocolManager()
    
    # Check first run
    if first_run_mgr.is_first_run():
        # Create temporary root for dialog
        temp_root = tk.Tk()
        temp_root.withdraw()
        
        # Show first run dialog
        from ui.first_run_dialog import FirstRunDialog
        dialog = FirstRunDialog(temp_root)
        temp_root.wait_window(dialog.dialog)
        
        # Process result
        if dialog.result is not None:
            if dialog.result:
                success, error = protocol_mgr.register()
                if not success:
                    messagebox.showwarning(
                        "Protocol Registration",
                        f"Failed to register protocol handler:\n{error}\n\n"
                        "You can try again from Settings.",
                        parent=temp_root
                    )
            first_run_mgr.mark_completed(dialog.result)
        
        temp_root.destroy()
    
    # Check if app has moved
    elif first_run_mgr.has_moved():
        # Re-register protocol silently if it was registered before
        if first_run_mgr.config.get("protocol_registered"):
            protocol_mgr.register(silent=True)
            first_run_mgr.mark_completed(True)
    
    # Continue with normal app startup
    root = tk.Tk()
    app = MainWindow(root, db)
    
    # Pass protocol manager to settings
    app.protocol_manager = protocol_mgr
    
    # ... rest of initialization ...
```

## Benefits

1. **Zero Friction**: No PowerShell scripts needed
2. **Automatic Updates**: Re-registers if app moves
3. **User Control**: Can enable/disable from settings
4. **Graceful Fallback**: Works without protocol via localhost
5. **Professional UX**: Guided first-run experience
6. **Portable Friendly**: Detects and handles location changes

## Testing Scenarios

1. **First Run**
   - Fresh install shows dialog
   - Can skip or accept
   - Registration succeeds/fails gracefully

2. **App Moved**
   - Copy app to new location
   - Auto-updates registration
   - No user intervention needed

3. **Settings Management**
   - Can register/unregister anytime
   - Status clearly shown
   - Test button verifies functionality

4. **Error Handling**
   - Registry access denied
   - Antivirus interference
   - Windows version incompatibility

This approach provides the best of both worlds: simple first-run setup with the flexibility to manage the protocol handler as needed!