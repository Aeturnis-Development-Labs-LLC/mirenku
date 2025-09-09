"""
Protocol Manager for registering custom URI schemes
Handles Windows Registry operations for mirenku:// protocol
"""

import platform
import logging
from typing import Optional
from pathlib import Path

# Windows-specific imports
if platform.system() == 'Windows':
    import winreg

logger = logging.getLogger(__name__)


class ProtocolManager:
    """Manages custom protocol registration for OAuth callbacks"""
    
    def __init__(self, development_mode: bool = False):
        """
        Initialize Protocol Manager
        
        Args:
            development_mode: If True, simulates registration without modifying system
        """
        self.development_mode = development_mode
        self.platform = platform.system()
        self.default_protocol = "mirenku"
        
    def register_protocol(self, exe_path: str, protocol: str = None) -> bool:
        """
        Register custom protocol handler
        
        Args:
            exe_path: Path to the executable to handle the protocol
            protocol: Protocol scheme (default: mirenku)
            
        Returns:
            True if registration successful, False otherwise
        """
        protocol = protocol or self.default_protocol
        
        if self.development_mode:
            logger.info(f"[DEV MODE] Would register {protocol}:// -> {exe_path}")
            return True
            
        if self.platform == 'Windows':
            return self._register_windows(exe_path, protocol)
        else:
            logger.warning(f"Protocol registration not implemented for {self.platform}")
            return False
    
    def _register_windows(self, exe_path: str, protocol: str) -> bool:
        """
        Register protocol on Windows via Registry
        
        Args:
            exe_path: Path to executable
            protocol: Protocol scheme
            
        Returns:
            True if successful
        """
        try:
            # Create main protocol key
            protocol_key_path = f"Software\\Classes\\{protocol}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, protocol_key_path) as protocol_key:
                winreg.SetValueEx(protocol_key, "", 0, winreg.REG_SZ, f"URL:{protocol} Protocol")
                winreg.SetValueEx(protocol_key, "URL Protocol", 0, winreg.REG_SZ, "")
                
            # Create shell command key
            command_key_path = f"Software\\Classes\\{protocol}\\shell\\open\\command"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, command_key_path) as command_key:
                # Command format: "path\to\exe" "%1"
                command = f'"{exe_path}" "%1"'
                winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)
                
            logger.info(f"Successfully registered {protocol}:// protocol")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied registering protocol: {e}")
            return False
        except Exception as e:
            logger.error(f"Error registering protocol: {e}")
            return False
    
    def unregister_protocol(self, protocol: str = None) -> bool:
        """
        Unregister custom protocol handler
        
        Args:
            protocol: Protocol scheme to unregister (default: mirenku)
            
        Returns:
            True if unregistration successful
        """
        protocol = protocol or self.default_protocol
        
        if self.development_mode:
            logger.info(f"[DEV MODE] Would unregister {protocol}://")
            return True
            
        if self.platform == 'Windows':
            return self._unregister_windows(protocol)
        else:
            logger.warning(f"Protocol unregistration not implemented for {self.platform}")
            return False
    
    def _unregister_windows(self, protocol: str) -> bool:
        """
        Unregister protocol on Windows
        
        Args:
            protocol: Protocol scheme
            
        Returns:
            True if successful
        """
        try:
            # Delete the entire protocol key tree
            self._delete_registry_tree(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{protocol}")
            logger.info(f"Successfully unregistered {protocol}:// protocol")
            return True
            
        except FileNotFoundError:
            logger.info(f"Protocol {protocol}:// was not registered")
            return True
        except Exception as e:
            logger.error(f"Error unregistering protocol: {e}")
            return False
    
    def _delete_registry_tree(self, key, subkey_path):
        """
        Recursively delete a registry key and all subkeys
        
        Args:
            key: Registry hive (e.g., HKEY_CURRENT_USER)
            subkey_path: Path to the key to delete
        """
        if platform.system() != 'Windows':
            return
            
        try:
            with winreg.OpenKey(key, subkey_path, 0, winreg.KEY_ALL_ACCESS) as open_key:
                # Get number of subkeys
                info = winreg.QueryInfoKey(open_key)
                num_subkeys = info[0]
                
                # Delete all subkeys first (in reverse to avoid index issues)
                for i in range(num_subkeys - 1, -1, -1):
                    subkey_name = winreg.EnumKey(open_key, i)
                    self._delete_registry_tree(key, f"{subkey_path}\\{subkey_name}")
                    
            # Now delete the key itself
            winreg.DeleteKey(key, subkey_path)
        except FileNotFoundError:
            pass  # Key doesn't exist, that's fine
        except AttributeError:
            # winreg not available (mocked in tests)
            pass
    
    def is_registered(self, protocol: str = None) -> bool:
        """
        Check if protocol is registered
        
        Args:
            protocol: Protocol scheme to check (default: mirenku)
            
        Returns:
            True if protocol is registered
        """
        protocol = protocol or self.default_protocol
        
        if self.development_mode:
            logger.info(f"[DEV MODE] Checking registration for {protocol}://")
            return True
            
        if self.platform == 'Windows':
            return self._is_registered_windows(protocol)
        else:
            return False
    
    def _is_registered_windows(self, protocol: str) -> bool:
        """
        Check if protocol is registered on Windows
        
        Args:
            protocol: Protocol scheme
            
        Returns:
            True if registered
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{protocol}"):
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking protocol registration: {e}")
            return False
    
    def get_registered_path(self, protocol: str = None) -> Optional[str]:
        """
        Get the registered executable path for a protocol
        
        Args:
            protocol: Protocol scheme (default: mirenku)
            
        Returns:
            Path to registered executable, or None if not registered
        """
        protocol = protocol or self.default_protocol
        
        if self.development_mode:
            logger.info(f"[DEV MODE] Getting registered path for {protocol}://")
            return None
            
        if self.platform == 'Windows':
            return self._get_registered_path_windows(protocol)
        else:
            return None
    
    def _get_registered_path_windows(self, protocol: str) -> Optional[str]:
        """
        Get registered executable path on Windows
        
        Args:
            protocol: Protocol scheme
            
        Returns:
            Path to executable or None
        """
        try:
            command_key_path = f"Software\\Classes\\{protocol}\\shell\\open\\command"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, command_key_path) as key:
                command, _ = winreg.QueryValueEx(key, "")
                # Extract path from command string (format: "path" "%1")
                if command.startswith('"'):
                    end_quote = command.index('"', 1)
                    return command[1:end_quote]
                else:
                    # No quotes, take everything before first space
                    parts = command.split(' ')
                    return parts[0] if parts else None
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting registered path: {e}")
            return None
    
    def needs_reregistration(self, current_exe_path: str, protocol: str = None) -> bool:
        """
        Check if protocol needs reregistration (app moved)
        
        Args:
            current_exe_path: Current executable path
            protocol: Protocol scheme (default: mirenku)
            
        Returns:
            True if reregistration needed
        """
        protocol = protocol or self.default_protocol
        
        if self.development_mode:
            return False
            
        if not self.is_registered(protocol):
            return True
            
        registered_path = self.get_registered_path(protocol)
        if not registered_path:
            return True
            
        # Normalize paths for comparison
        current_path = Path(current_exe_path).resolve()
        reg_path = Path(registered_path).resolve()
        
        return current_path != reg_path
    
    def auto_reregister(self, current_exe_path: str, protocol: str = None) -> bool:
        """
        Automatically reregister protocol if app has moved
        
        Args:
            current_exe_path: Current executable path
            protocol: Protocol scheme (default: mirenku)
            
        Returns:
            True if reregistration successful or not needed
        """
        protocol = protocol or self.default_protocol
        
        if not self.needs_reregistration(current_exe_path, protocol):
            logger.info(f"Protocol {protocol}:// registration is up to date")
            return True
            
        logger.info(f"App has moved, reregistering {protocol}:// protocol")
        
        # Unregister old path
        self.unregister_protocol(protocol)
        
        # Register new path
        return self.register_protocol(current_exe_path, protocol)