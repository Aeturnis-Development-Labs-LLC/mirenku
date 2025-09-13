"""
Token encryption key rotation manager
Following The Mirenku Way: Local key management, user controls their security
"""

import json
import logging
import secrets
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import keyring
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class KeyRotationManager:
    """Manages encryption key rotation for token storage"""

    def __init__(
        self, app_name: str, rotation_days: int = 30, key_storage_path: Optional[Path] = None
    ):
        """
        Initialize key rotation manager

        Args:
            app_name: Application name for keyring
            rotation_days: Days before key rotation (default 30)
            key_storage_path: Path to store key metadata
        """
        self.app_name = app_name
        self.rotation_days = rotation_days
        self.key_storage_path = (
            key_storage_path or Path.home() / f".{app_name.lower()}" / "keys.json"
        )

        # Thread safety
        self._lock = threading.Lock()

        # Key storage
        self._keys = {}  # key_id -> key
        self._metadata = {}  # key_id -> metadata
        self._active_key_id = None

        # Audit logging
        self.audit_logger = None

        # Load existing keys
        self._load_keys()

    def generate_new_key(self) -> str:
        """Generate a new Fernet encryption key"""
        return Fernet.generate_key().decode("utf-8")

    def save_key_metadata(self, key: str) -> Dict[str, Any]:
        """
        Save key with metadata

        Args:
            key: The encryption key

        Returns:
            Key metadata dictionary
        """
        with self._lock:
            # Generate key ID
            key_id = secrets.token_urlsafe(16)

            # Create metadata
            metadata = {
                "key_id": key_id,
                "created_at": datetime.now().isoformat(),
                "rotate_after": (datetime.now() + timedelta(days=self.rotation_days)).isoformat(),
                "is_active": True,
                "compromised": False,
            }

            # Deactivate previous active key
            if self._active_key_id:
                self._metadata[self._active_key_id]["is_active"] = False

            # Store key and metadata
            self._keys[key_id] = key
            self._metadata[key_id] = metadata
            self._active_key_id = key_id

            # Save to secure storage
            self._save_key_to_keyring(key_id, key)
            self._save_metadata()

            return metadata

    def needs_rotation(self) -> bool:
        """Check if key rotation is needed"""
        if not self._active_key_id:
            return True

        active_metadata = self._metadata.get(self._active_key_id)
        if not active_metadata:
            return True

        rotate_after = datetime.fromisoformat(active_metadata["rotate_after"])
        return datetime.now() > rotate_after

    def get_key_age_days(self) -> float:
        """Get age of active key in days"""
        if not self._active_key_id:
            return float("inf")

        metadata = self._metadata.get(self._active_key_id)
        if not metadata:
            return float("inf")

        created_at = datetime.fromisoformat(metadata["created_at"])
        age = datetime.now() - created_at
        return age.total_seconds() / 86400

    def rotate_key(self, token_storage=None) -> str:
        """
        Rotate encryption key

        Args:
            token_storage: Optional TokenStorage instance to update

        Returns:
            New encryption key
        """
        with self._lock:
            try:
                # Get current tokens if token_storage provided
                current_tokens = None
                old_key = self.get_active_key()

                if token_storage and old_key:
                    token_storage.encryption_key = old_key
                    current_tokens = token_storage.load_tokens()

                # Generate new key
                new_key = self.generate_new_key()
                metadata = self.save_key_metadata(new_key)

                # Re-encrypt tokens with new key if needed
                if token_storage and current_tokens:
                    token_storage.encryption_key = new_key
                    token_storage.save_tokens(current_tokens)

                # Log rotation
                if self.audit_logger:
                    self.audit_logger.log_config_change(
                        setting="encryption_key",
                        old_value="[REDACTED]",
                        new_value="[REDACTED]",
                        changed_by="automatic_rotation",
                    )

                logger.info(
                    f"Successfully rotated encryption key (ID: {metadata['key_id'][:8]}...)"
                )
                return new_key

            except Exception as e:
                logger.error(f"Key rotation failed: {e}")
                # Rollback on failure
                if token_storage and old_key:
                    token_storage.encryption_key = old_key
                raise

    def get_active_key(self) -> Optional[str]:
        """Get the currently active encryption key"""
        if not self._active_key_id:
            return None
        return self._keys.get(self._active_key_id)

    def get_all_keys(self) -> List[str]:
        """Get all keys in rotation"""
        return list(self._keys.values())

    def add_key_to_rotation(self, key: str) -> None:
        """Add a key to the rotation pool"""
        key_id = secrets.token_urlsafe(16)
        self._keys[key_id] = key
        self._metadata[key_id] = {
            "key_id": key_id,
            "created_at": datetime.now().isoformat(),
            "is_active": False,
        }

    def decrypt_with_any_key(self, encrypted_data: bytes) -> bytes:
        """
        Try to decrypt data with any available key

        Args:
            encrypted_data: Data to decrypt

        Returns:
            Decrypted data

        Raises:
            InvalidToken: If no key can decrypt the data
        """
        # Try active key first
        if self._active_key_id:
            try:
                fernet = Fernet(self._keys[self._active_key_id].encode())
                return fernet.decrypt(encrypted_data)
            except InvalidToken:
                pass

        # Try other keys
        for key_id, key in self._keys.items():
            if key_id != self._active_key_id:
                try:
                    fernet = Fernet(key.encode())
                    return fernet.decrypt(encrypted_data)
                except InvalidToken:
                    continue

        raise InvalidToken("No valid key found to decrypt data")

    def cleanup_old_keys(self, keep_last: int = 2) -> None:
        """
        Clean up old keys, keeping only recent ones

        Args:
            keep_last: Number of recent keys to keep
        """
        with self._lock:
            # Sort keys by creation time
            sorted_keys = sorted(
                self._metadata.items(), key=lambda x: x[1]["created_at"], reverse=True
            )

            # Keep active + keep_last keys
            keys_to_keep = set()
            if self._active_key_id:
                keys_to_keep.add(self._active_key_id)

            for key_id, _ in sorted_keys[:keep_last]:
                keys_to_keep.add(key_id)

            # Delete old keys
            keys_to_delete = set(self._keys.keys()) - keys_to_keep
            for key_id in keys_to_delete:
                self.secure_delete_key(key_id)

    def update_key_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update metadata for a key"""
        key_id = metadata["key_id"]
        self._metadata[key_id] = metadata
        self._save_metadata()

    def emergency_rotate(self, reason: str) -> str:
        """
        Perform emergency key rotation

        Args:
            reason: Reason for emergency rotation

        Returns:
            New encryption key
        """
        with self._lock:
            # Mark current key as compromised
            if self._active_key_id:
                self._metadata[self._active_key_id]["compromised"] = True
                self._metadata[self._active_key_id]["compromise_reason"] = reason
                self._metadata[self._active_key_id]["compromised_at"] = datetime.now().isoformat()
                self._metadata[self._active_key_id]["is_active"] = False

            # Generate new key immediately
            new_key = self.generate_new_key()
            metadata = self.save_key_metadata(new_key)

            # Log emergency rotation
            if self.audit_logger:
                self.audit_logger.log_suspicious_activity(
                    activity_type="emergency_key_rotation",
                    details=f"Reason: {reason}",
                    ip_address="local",
                    severity="critical",
                )

            logger.warning(f"Emergency key rotation performed: {reason}")
            return new_key

    def get_key_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific key"""
        # Find key ID by value
        for key_id, stored_key in self._keys.items():
            if stored_key == key:
                return self._metadata.get(key_id)
        return None

    def create_backup(self) -> Dict[str, Any]:
        """Create backup of all keys and metadata"""
        with self._lock:
            backup = {
                "keys": dict(self._keys),
                "metadata": dict(self._metadata),
                "active_key_id": self._active_key_id,
                "backup_date": datetime.now().isoformat(),
                "app_name": self.app_name,
            }
            return backup

    def restore_from_backup(self, backup_data: Dict[str, Any]) -> None:
        """Restore keys from backup"""
        with self._lock:
            self._keys = backup_data["keys"]
            self._metadata = backup_data["metadata"]
            self._active_key_id = backup_data.get("active_key_id")

            # Save restored keys to keyring
            for key_id, key in self._keys.items():
                self._save_key_to_keyring(key_id, key)

            self._save_metadata()
            logger.info(f"Restored {len(self._keys)} keys from backup")

    def clear_all_keys(self) -> None:
        """Clear all keys (use with caution)"""
        with self._lock:
            # Securely delete all keys
            for key_id in list(self._keys.keys()):
                self.secure_delete_key(key_id)

            self._keys.clear()
            self._metadata.clear()
            self._active_key_id = None

    def secure_delete_key(self, key_id: str) -> None:
        """Securely delete a key"""
        if key_id in self._keys:
            # Overwrite key in memory
            key = self._keys[key_id]
            overwrite = "X" * len(key)
            self._keys[key_id] = overwrite

            # Delete from keyring
            try:
                keyring.delete_password(self.app_name, f"key_{key_id}")
            except Exception:
                pass

            # Remove from dictionaries
            del self._keys[key_id]
            if key_id in self._metadata:
                del self._metadata[key_id]

            logger.info(f"Securely deleted key {key_id[:8]}...")

    def get_key_by_id(self, key_id: str) -> str:
        """Get key by ID"""
        if key_id not in self._keys:
            raise KeyError(f"Key {key_id} not found")
        return self._keys[key_id]

    def get_rotation_metrics(self) -> Dict[str, Any]:
        """Get key rotation metrics"""
        with self._lock:
            total_rotations = len(self._metadata)

            # Find last rotation time
            last_rotation = None
            if self._active_key_id and self._active_key_id in self._metadata:
                last_rotation = self._metadata[self._active_key_id]["created_at"]

            # Calculate average key age
            total_age = 0
            key_count = 0
            for metadata in self._metadata.values():
                created_at = datetime.fromisoformat(metadata["created_at"])
                age = (datetime.now() - created_at).total_seconds() / 86400
                total_age += age
                key_count += 1

            avg_age = total_age / key_count if key_count > 0 else 0

            return {
                "total_rotations": total_rotations,
                "last_rotation": last_rotation,
                "average_key_age_days": avg_age,
                "keys_in_rotation": len(self._keys),
                "active_key_id": self._active_key_id[:8] + "..." if self._active_key_id else None,
            }

    def enable_audit_logging(self) -> None:
        """Enable audit logging for key operations"""
        from utils.security_audit import SecurityAuditLogger

        self.audit_logger = SecurityAuditLogger()

    def _save_key_to_keyring(self, key_id: str, key: str) -> None:
        """Save key to system keyring"""
        try:
            keyring.set_password(self.app_name, f"key_{key_id}", key)
        except Exception as e:
            logger.warning(f"Failed to save key to keyring: {e}")

    def _save_metadata(self) -> None:
        """Save metadata to file"""
        try:
            # Ensure directory exists
            self.key_storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Save metadata (not keys!)
            metadata_only = {"metadata": self._metadata, "active_key_id": self._active_key_id}

            with open(self.key_storage_path, "w") as f:
                json.dump(metadata_only, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save key metadata: {e}")

    def _load_keys(self) -> None:
        """Load keys from storage"""
        # Load metadata from file
        if self.key_storage_path.exists():
            try:
                with open(self.key_storage_path) as f:
                    data = json.load(f)
                    self._metadata = data.get("metadata", {})
                    self._active_key_id = data.get("active_key_id")
            except Exception as e:
                logger.error(f"Failed to load key metadata: {e}")

        # Load actual keys from keyring
        for key_id in self._metadata.keys():
            try:
                key = keyring.get_password(self.app_name, f"key_{key_id}")
                if key:
                    self._keys[key_id] = key
            except Exception as e:
                logger.warning(f"Failed to load key {key_id[:8]}... from keyring: {e}")
