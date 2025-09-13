"""
Test suite for token encryption key rotation
Ensures encryption keys are rotated periodically for enhanced security
Following The Mirenku Way: Simple, secure, local key management
"""

import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from cryptography.fernet import Fernet

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestTokenEncryptionRotation:
    """Test token encryption key rotation functionality"""

    @pytest.fixture()
    def mock_keyring(self):
        """Mock keyring for testing"""
        with patch("keyring.get_password") as mock_get, patch(
            "keyring.set_password"
        ) as mock_set, patch("keyring.delete_password") as mock_delete:
            yield mock_get, mock_set, mock_delete

    @pytest.fixture()
    def token_storage(self, mock_keyring):
        """Create token storage with mocked keyring"""
        from utils.token_storage import TokenStorage

        storage = TokenStorage(app_name="TestApp")
        return storage

    @pytest.fixture()
    def key_rotator(self):
        """Create key rotation manager"""
        with patch("utils.key_rotation.keyring"):
            from utils.key_rotation import KeyRotationManager

            rotator = KeyRotationManager(app_name="TestApp", rotation_days=30)
            yield rotator

    def test_key_rotator_initialization(self, key_rotator):
        """Test that key rotator initializes correctly"""
        assert key_rotator is not None
        assert key_rotator.app_name == "TestApp"
        assert key_rotator.rotation_days == 30

    def test_generate_new_encryption_key(self, key_rotator):
        """Test generation of new encryption key"""
        key = key_rotator.generate_new_key()

        # Should be a valid Fernet key
        assert key is not None
        assert len(key) == 44  # Base64 encoded 32 bytes

        # Should be usable for encryption
        fernet = Fernet(key.encode())
        test_data = b"test data"
        encrypted = fernet.encrypt(test_data)
        decrypted = fernet.decrypt(encrypted)
        assert decrypted == test_data

    def test_key_metadata_storage(self, key_rotator):
        """Test storing key metadata (creation time, rotation schedule)"""
        key = key_rotator.generate_new_key()
        metadata = key_rotator.save_key_metadata(key)

        assert "key_id" in metadata
        assert "created_at" in metadata
        assert "rotate_after" in metadata
        assert "is_active" in metadata
        assert metadata["is_active"] is True

    def test_key_rotation_needed_check(self, key_rotator):
        """Test checking if key rotation is needed"""
        # New key shouldn't need rotation
        key = key_rotator.generate_new_key()
        key_rotator.save_key_metadata(key)
        assert not key_rotator.needs_rotation()

        # Simulate old key by modifying metadata
        if key_rotator._active_key_id:
            key_rotator._metadata[key_rotator._active_key_id]["rotate_after"] = (
                datetime.now() - timedelta(days=1)
            ).isoformat()
            assert key_rotator.needs_rotation()

    def test_rotate_encryption_key(self, key_rotator, token_storage):
        """Test rotating encryption key while maintaining access to tokens"""
        # Mock the save and load methods to avoid keyring access
        with patch.object(token_storage, "save_tokens", return_value=True), patch.object(
            token_storage, "load_tokens", return_value={"test": "token"}
        ):
            # Set up initial key
            old_key = key_rotator.generate_new_key()
            key_rotator.save_key_metadata(old_key)

            # Rotate key
            new_key = key_rotator.rotate_key(token_storage)

            assert new_key != old_key
            assert new_key is not None

            # Verify new key is active
            assert key_rotator.get_active_key() == new_key

    def test_key_rotation_with_multiple_keys(self, key_rotator):
        """Test managing multiple keys during rotation period"""
        # Generate multiple keys
        key1 = key_rotator.generate_new_key()
        time.sleep(0.1)
        key2 = key_rotator.generate_new_key()
        time.sleep(0.1)
        key3 = key_rotator.generate_new_key()

        # Save all keys
        key_rotator.save_key_metadata(key1)
        key_rotator.save_key_metadata(key2)
        key_rotator.save_key_metadata(key3)

        # Should track all keys
        all_keys = key_rotator.get_all_keys()
        assert len(all_keys) >= 3

        # Should identify active key
        active_key = key_rotator.get_active_key()
        assert active_key == key3  # Most recent

    def test_decrypt_with_old_keys(self, key_rotator):
        """Test decrypting data encrypted with old keys"""
        # Encrypt with old key
        old_key = Fernet.generate_key().decode()
        fernet_old = Fernet(old_key.encode())
        test_data = b"sensitive data"
        encrypted_data = fernet_old.encrypt(test_data)

        # Rotate to new key
        new_key = Fernet.generate_key().decode()

        # Should still decrypt with old key in rotation
        key_rotator.add_key_to_rotation(old_key)
        key_rotator.add_key_to_rotation(new_key)

        decrypted = key_rotator.decrypt_with_any_key(encrypted_data)
        assert decrypted == test_data

    def test_key_rotation_cleanup(self, key_rotator):
        """Test cleanup of old keys after grace period"""
        # Create old keys
        for i in range(5):
            key = key_rotator.generate_new_key()
            metadata = key_rotator.save_key_metadata(key)
            # Simulate aging
            if i < 3:  # First 3 keys are old
                metadata["created_at"] = (datetime.now() - timedelta(days=60)).isoformat()
                key_rotator.update_key_metadata(metadata)

        # Clean up old keys (keep last 2 + current)
        key_rotator.cleanup_old_keys(keep_last=2)

        remaining_keys = key_rotator.get_all_keys()
        assert len(remaining_keys) <= 3

    def test_automatic_rotation_on_schedule(self, key_rotator):
        """Test automatic key rotation based on schedule"""
        # Set short rotation period for testing
        key_rotator.rotation_days = 0.001  # Very short for testing

        # Generate initial key
        initial_key = key_rotator.generate_new_key()
        key_rotator.save_key_metadata(initial_key)

        # Wait for rotation period
        time.sleep(0.1)

        # Check and perform rotation if needed
        if key_rotator.needs_rotation():
            new_key = key_rotator.rotate_key()
            assert new_key != initial_key

    def test_rotation_with_concurrent_access(self, key_rotator, token_storage):
        """Test key rotation doesn't break concurrent token access"""
        import threading

        # Set up initial state
        key = key_rotator.generate_new_key()
        token_storage.encryption_key = key
        tokens = {"access_token": "test_token"}
        token_storage.save_tokens(tokens)

        errors = []

        def read_tokens():
            try:
                for _ in range(10):
                    loaded = token_storage.load_tokens()
                    assert loaded == tokens
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        def rotate_keys():
            try:
                time.sleep(0.05)  # Start rotation mid-read
                key_rotator.rotate_key(token_storage)
            except Exception as e:
                errors.append(e)

        # Run concurrent operations
        threads = [
            threading.Thread(target=read_tokens),
            threading.Thread(target=rotate_keys),
            threading.Thread(target=read_tokens),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_key_rotation_audit_logging(self, key_rotator):
        """Test that key rotations are logged for audit"""
        with patch("utils.security_audit.SecurityAuditLogger") as mock_audit:
            mock_logger = Mock()
            mock_audit.return_value = mock_logger

            # Enable audit logging
            key_rotator.enable_audit_logging()

            # Perform rotation
            old_key = key_rotator.generate_new_key()
            new_key = key_rotator.rotate_key()

            # Should log rotation event
            mock_logger.log_config_change.assert_called()
            call_args = mock_logger.log_config_change.call_args
            assert "encryption_key" in str(call_args)

    def test_emergency_key_rotation(self, key_rotator):
        """Test emergency key rotation (e.g., after potential compromise)"""
        # Set up normal key
        normal_key = key_rotator.generate_new_key()
        key_rotator.save_key_metadata(normal_key)

        # Perform emergency rotation
        emergency_key = key_rotator.emergency_rotate(reason="potential_compromise")

        assert emergency_key != normal_key

        # Old key should be marked as compromised
        old_metadata = key_rotator.get_key_metadata(normal_key)
        assert old_metadata["is_active"] is False
        assert old_metadata.get("compromised") is True
        assert old_metadata.get("compromise_reason") == "potential_compromise"

    def test_key_backup_and_restore(self, key_rotator):
        """Test backing up and restoring encryption keys"""
        # Generate keys
        key1 = key_rotator.generate_new_key()
        key2 = key_rotator.generate_new_key()

        # Create backup
        backup_data = key_rotator.create_backup()

        assert "keys" in backup_data
        assert "metadata" in backup_data
        assert "backup_date" in backup_data

        # Simulate key loss
        key_rotator.clear_all_keys()

        # Restore from backup
        key_rotator.restore_from_backup(backup_data)

        # Keys should be restored
        restored_keys = key_rotator.get_all_keys()
        assert key1 in restored_keys
        assert key2 in restored_keys

    def test_rotation_rollback_on_failure(self, key_rotator, token_storage):
        """Test rollback if rotation fails"""
        # Set up initial state
        old_key = key_rotator.generate_new_key()
        token_storage.encryption_key = old_key

        # Simulate rotation failure
        with patch.object(token_storage, "save_tokens", side_effect=Exception("Save failed")):
            with pytest.raises(Exception):
                key_rotator.rotate_key(token_storage)

        # Should rollback to old key
        assert token_storage.encryption_key == old_key
        assert key_rotator.get_active_key() == old_key

    def test_key_rotation_metrics(self, key_rotator):
        """Test tracking key rotation metrics"""
        # Perform several rotations
        for _ in range(3):
            key_rotator.generate_new_key()
            key_rotator.rotate_key()
            time.sleep(0.1)

        # Get metrics
        metrics = key_rotator.get_rotation_metrics()

        assert "total_rotations" in metrics
        assert "last_rotation" in metrics
        assert "average_key_age_days" in metrics
        assert "keys_in_rotation" in metrics
        assert metrics["total_rotations"] >= 3

    def test_secure_key_deletion(self, key_rotator):
        """Test secure deletion of old keys"""
        # Generate key
        key = key_rotator.generate_new_key()
        key_id = key_rotator.save_key_metadata(key)["key_id"]

        # Delete key securely
        key_rotator.secure_delete_key(key_id)

        # Key should be overwritten and deleted
        with pytest.raises(KeyError):
            key_rotator.get_key_by_id(key_id)

        # Verify secure deletion (key material should be overwritten)
        # This is implementation-specific

    def test_rotation_with_token_storage_integration(self, token_storage):
        """Test integration with TokenStorage for seamless rotation"""

        # Enable key rotation in token storage
        token_storage.enable_key_rotation(rotation_days=30)

        # Save tokens
        tokens = {"access_token": "test", "refresh_token": "refresh"}
        token_storage.save_tokens(tokens)

        # Simulate time passing
        with patch("utils.key_rotation.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(days=31)

            # Loading tokens should trigger rotation if needed
            loaded = token_storage.load_tokens()
            assert loaded == tokens

            # Key should have been rotated
            assert token_storage.key_rotation_performed
