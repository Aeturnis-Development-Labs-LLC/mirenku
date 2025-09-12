"""
Secure token storage with three-tier encryption hierarchy
Primary: OS Keyring, Fallback: Fernet, Last Resort: Base64
"""

import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Check available encryption methods
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    logger.debug("Keyring library not available")

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    logger.debug("Cryptography library not available")


class TokenStorage:
    """
    Secure token storage with automatic fallback
    
    Storage hierarchy:
    1. OS Keyring (most secure, OS-managed)
    2. Fernet encryption (reliable, cross-platform)
    3. Base64 encoding (last resort, not secure)
    """
    
    def __init__(self, app_name: str = "Mirenku"):
        """
        Initialize token storage
        
        Args:
            app_name: Application name for keyring isolation
        """
        self.app_name = app_name
        self.config_dir = Path.home() / ".mirenku"
        self.config_dir.mkdir(exist_ok=True)
        
        # File paths for fallback storage
        self.token_file = self.config_dir / "tokens.enc"
        self.key_file = self.config_dir / ".key"
        self.base64_file = self.config_dir / "tokens.b64"
        
        # Initialize storage method
        self.storage_method = self._init_storage()
        self.fernet = None
        
        if self.storage_method == "fernet":
            self._init_fernet()
        
        logger.info(f"TokenStorage initialized with method: {self.storage_method}")
        
        # Check for migration opportunities
        self._check_migration()
    
    def _init_storage(self) -> str:
        """
        Determine available storage method
        
        Returns:
            Storage method name: "keyring", "fernet", or "base64"
        """
        if HAS_KEYRING:
            # Test keyring availability
            try:
                # Try a test operation
                keyring.get_password("test", "test")
                return "keyring"
            except Exception as e:
                logger.debug(f"Keyring test failed: {e}")
        
        if HAS_CRYPTO:
            return "fernet"
        
        # No secure storage available - refuse to continue
        logger.error("No secure encryption available! Cannot store tokens safely.")
        return "unavailable"
    
    def _init_fernet(self):
        """Initialize Fernet encryption with key management"""
        if not self.key_file.exists():
            # Generate new key
            key = Fernet.generate_key()
            # Save key (slightly obfuscated)
            self.key_file.write_bytes(key)
            # Set restrictive permissions on Windows
            try:
                import stat
                import os
                os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)
            except:
                pass
            logger.debug("Generated new Fernet key")
        
        # Load key
        key = self.key_file.read_bytes()
        self.fernet = Fernet(key)
    
    def save_tokens(self, tokens: Dict[str, Any], user_accepts_risk: bool = False) -> bool:
        """
        Save OAuth tokens securely
        
        Args:
            tokens: Dictionary containing access_token, refresh_token, etc.
            user_accepts_risk: User explicitly accepts security risk (for emergency fallback)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Try primary method first
            if self.storage_method == "keyring":
                return self._save_keyring(tokens)
            elif self.storage_method == "fernet":
                return self._save_fernet(tokens)
            elif self.storage_method == "base64" and user_accepts_risk:
                return self._save_base64(tokens)
            else:
                logger.error("No secure storage method available. Tokens will not be saved.")
                logger.error("Please install 'keyring' or 'cryptography' package for secure token storage.")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save tokens with {self.storage_method}: {e}")
            
            # Try fallback methods
            if self.storage_method == "keyring":
                # Fallback to Fernet
                if HAS_CRYPTO:
                    logger.info("Falling back to Fernet encryption")
                    self.storage_method = "fernet"
                    self._init_fernet()
                    return self._save_fernet(tokens)
                else:
                    # No secure fallback available
                    logger.error("No secure storage fallback available. Tokens cannot be saved.")
                    logger.error("Please install 'keyring' or 'cryptography' package.")
                    return False
            
            return False
    
    def load_tokens(self) -> Optional[Dict[str, Any]]:
        """
        Load OAuth tokens from storage
        
        Returns:
            Token dictionary or None if not found
        """
        try:
            if self.storage_method == "keyring":
                tokens = self._load_keyring()
            elif self.storage_method == "fernet":
                tokens = self._load_fernet()
            elif self.storage_method == "base64":
                # Only load if it exists from before security update
                logger.warning("Loading tokens from insecure base64 storage (legacy)")
                tokens = self._load_base64()
            else:
                return None
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            
            # Try loading from other methods (migration support)
            if self.base64_file.exists():
                try:
                    return self._load_base64()
                except:
                    pass
            
            return None
    
    def delete_tokens(self) -> bool:
        """
        Delete stored tokens
        
        Returns:
            True if deleted successfully
        """
        try:
            if self.storage_method == "keyring":
                keyring.delete_password(self.app_name, "oauth_tokens")
            
            # Clean up all possible files
            for file in [self.token_file, self.base64_file]:
                if file.exists():
                    file.unlink()
            
            logger.info("Tokens deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tokens: {e}")
            return False
    
    # Keyring methods
    def _save_keyring(self, tokens: Dict[str, Any]) -> bool:
        """Save tokens to OS keyring"""
        json_data = json.dumps(tokens)
        keyring.set_password(self.app_name, "oauth_tokens", json_data)
        logger.debug("Tokens saved to keyring")
        return True
    
    def _load_keyring(self) -> Optional[Dict[str, Any]]:
        """Load tokens from OS keyring"""
        json_data = keyring.get_password(self.app_name, "oauth_tokens")
        if json_data:
            return json.loads(json_data)
        return None
    
    # Fernet methods
    def _save_fernet(self, tokens: Dict[str, Any]) -> bool:
        """Save tokens with Fernet encryption"""
        json_data = json.dumps(tokens)
        encrypted = self.fernet.encrypt(json_data.encode())
        self.token_file.write_bytes(encrypted)
        logger.debug("Tokens saved with Fernet encryption")
        return True
    
    def _load_fernet(self) -> Optional[Dict[str, Any]]:
        """Load tokens with Fernet decryption"""
        if not self.token_file.exists():
            return None
        
        encrypted = self.token_file.read_bytes()
        decrypted = self.fernet.decrypt(encrypted)
        return json.loads(decrypted.decode())
    
    # Base64 methods (legacy support only)
    def _save_base64(self, tokens: Dict[str, Any]) -> bool:
        """Save tokens with base64 encoding (INSECURE - EMERGENCY USE ONLY)"""
        logger.critical("SECURITY WARNING: Saving tokens with base64 encoding!")
        logger.critical("This is NOT encryption and tokens are readable by anyone with file access!")
        logger.critical("Install 'keyring' or 'cryptography' package for secure storage.")
        json_data = json.dumps(tokens)
        encoded = base64.b64encode(json_data.encode()).decode()
        self.base64_file.write_text(encoded)
        return True
    
    def _load_base64(self) -> Optional[Dict[str, Any]]:
        """Load tokens with base64 decoding"""
        if not self.base64_file.exists():
            return None
        
        encoded = self.base64_file.read_text()
        decoded = base64.b64decode(encoded)
        return json.loads(decoded.decode())
    
    def _check_migration(self):
        """Check if tokens can be migrated to more secure storage"""
        if self.storage_method == "keyring":
            # Already using best method
            return
        
        # Check if base64 tokens exist and can be migrated
        if self.base64_file.exists() and self.storage_method in ["keyring", "fernet"]:
            try:
                tokens = self._load_base64()
                if tokens:
                    logger.info("Migrating tokens from insecure storage to secure storage")
                    # Force migration without user consent since we have secure method
                    if self.storage_method == "keyring":
                        self._save_keyring(tokens)
                    elif self.storage_method == "fernet":
                        self._save_fernet(tokens)
                    # Delete old base64 file
                    self.base64_file.unlink()
                    logger.info("Token migration completed - insecure storage removed")
            except Exception as e:
                logger.error(f"Failed to migrate tokens: {e}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about current storage method
        
        Returns:
            Dictionary with storage information
        """
        return {
            "method": self.storage_method,
            "secure": self.storage_method in ["keyring", "fernet"],
            "available": self.storage_method != "unavailable",
            "app_name": self.app_name,
            "has_tokens": self.load_tokens() is not None
        }