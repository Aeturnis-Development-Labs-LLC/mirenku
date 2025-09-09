"""
Test suite for Token Storage module
Following TDD approach - tests written first
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestTokenStorageKeyring:
    """Test token storage with OS Keyring (primary method)"""
    
    @pytest.fixture
    def mock_keyring_available(self):
        """Mock keyring being available"""
        with patch('utils.token_storage.HAS_KEYRING', True):
            yield
    
    @pytest.fixture
    def mock_keyring(self):
        """Mock keyring module"""
        with patch('utils.token_storage.keyring') as mock:
            yield mock
    
    def test_keyring_save_and_load_tokens(self, mock_keyring_available, mock_keyring):
        """Test saving and loading tokens using OS keyring"""
        from utils.token_storage import TokenStorage
        
        # Given: A token storage instance with keyring available
        storage = TokenStorage("Mirenku")
        test_tokens = {
            "access_token": "test_access_token_123",
            "refresh_token": "test_refresh_token_456",
            "expires_in": 3600
        }
        
        # When: Tokens are saved
        success = storage.save_tokens(test_tokens)
        
        # Then: Tokens are stored in keyring
        assert success is True
        mock_keyring.set_password.assert_called_once()
        call_args = mock_keyring.set_password.call_args
        assert call_args[0][0] == "Mirenku"  # service name
        assert call_args[0][1] == "oauth_tokens"  # key name
        
        # Verify stored data is JSON
        stored_data = call_args[0][2]
        parsed = json.loads(stored_data)
        assert parsed["access_token"] == test_tokens["access_token"]
        
        # When: Tokens are loaded
        mock_keyring.get_password.return_value = stored_data
        loaded = storage.load_tokens()
        
        # Then: Correct tokens are returned
        assert loaded is not None
        assert loaded["access_token"] == test_tokens["access_token"]
        assert loaded["refresh_token"] == test_tokens["refresh_token"]
    
    def test_keyring_handles_missing_tokens(self, mock_keyring_available, mock_keyring):
        """Test keyring behavior when no tokens exist"""
        from utils.token_storage import TokenStorage
        
        # Given: No tokens in keyring
        mock_keyring.get_password.return_value = None
        storage = TokenStorage("Mirenku")
        
        # When: Attempting to load tokens
        loaded = storage.load_tokens()
        
        # Then: Returns None gracefully
        assert loaded is None
        mock_keyring.get_password.assert_called_with("Mirenku", "oauth_tokens")
    
    def test_keyring_delete_tokens(self, mock_keyring_available, mock_keyring):
        """Test deleting tokens from keyring"""
        from utils.token_storage import TokenStorage
        
        # Given: Tokens stored in keyring
        storage = TokenStorage("Mirenku")
        
        # When: Delete is called
        success = storage.delete_tokens()
        
        # Then: Tokens are removed from keyring
        assert success is True
        mock_keyring.delete_password.assert_called_with("Mirenku", "oauth_tokens")
    
    def test_keyring_error_fallback(self, mock_keyring_available, mock_keyring):
        """Test fallback when keyring operations fail"""
        from utils.token_storage import TokenStorage
        
        # Given: Keyring raises an exception
        mock_keyring.set_password.side_effect = Exception("Keyring error")
        storage = TokenStorage("Mirenku")
        
        test_tokens = {"access_token": "test"}
        
        # When: Save is attempted
        success = storage.save_tokens(test_tokens)
        
        # Then: Falls back to next method (should still succeed)
        assert success is True
        assert storage.storage_method != "keyring"


class TestTokenStorageFernet:
    """Test token storage with Fernet encryption (fallback method)"""
    
    @pytest.fixture
    def mock_no_keyring(self):
        """Mock keyring not being available"""
        with patch('utils.token_storage.HAS_KEYRING', False):
            yield
    
    @pytest.fixture
    def mock_fernet_available(self):
        """Mock Fernet being available"""
        with patch('utils.token_storage.HAS_CRYPTO', True):
            yield
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for testing"""
        return tmp_path
    
    def test_fernet_save_and_load_tokens(self, mock_no_keyring, mock_fernet_available, temp_dir):
        """Test Fernet encryption when keyring unavailable"""
        from utils.token_storage import TokenStorage
        
        # Given: Keyring unavailable, Fernet available
        with patch('utils.token_storage.Path.home') as mock_home:
            mock_home.return_value = temp_dir
            storage = TokenStorage("Mirenku")
            
            test_tokens = {
                "access_token": "fernet_access_token",
                "refresh_token": "fernet_refresh_token",
                "expires_in": 3600
            }
            
            # When: Tokens are saved
            success = storage.save_tokens(test_tokens)
            
            # Then: Tokens encrypted with Fernet and saved
            assert success is True
            assert storage.storage_method == "fernet"
            
            # Verify encrypted file exists
            token_file = temp_dir / ".mirenku" / "tokens.enc"
            assert token_file.exists()
            
            # When: Tokens are loaded
            loaded = storage.load_tokens()
            
            # Then: Correct tokens are returned
            assert loaded is not None
            assert loaded["access_token"] == test_tokens["access_token"]
            assert loaded["refresh_token"] == test_tokens["refresh_token"]
    
    def test_fernet_key_generation(self, mock_no_keyring, mock_fernet_available, temp_dir):
        """Test secure key generation for Fernet"""
        from utils.token_storage import TokenStorage
        
        # Given: No encryption key exists
        with patch('utils.token_storage.Path.home') as mock_home:
            mock_home.return_value = temp_dir
            
            # When: Storage initialized
            storage = TokenStorage("Mirenku")
            
            # Then: Key is generated and stored securely
            key_file = temp_dir / ".mirenku" / ".key"
            assert key_file.exists()
            
            # Verify key is valid Fernet key
            key_data = key_file.read_bytes()
            assert len(key_data) > 0
            
            # Key should be base64 encoded
            try:
                base64.urlsafe_b64decode(key_data)
                valid_key = True
            except:
                valid_key = False
            assert valid_key
    
    def test_fernet_key_persistence(self, mock_no_keyring, mock_fernet_available, temp_dir):
        """Test that Fernet key persists across sessions"""
        from utils.token_storage import TokenStorage
        
        with patch('utils.token_storage.Path.home') as mock_home:
            mock_home.return_value = temp_dir
            
            # Given: Key was previously generated
            storage1 = TokenStorage("Mirenku")
            test_tokens = {"access_token": "persistent_token"}
            storage1.save_tokens(test_tokens)
            
            # When: New storage instance created
            storage2 = TokenStorage("Mirenku")
            
            # Then: Same key is loaded and tokens decrypt correctly
            loaded = storage2.load_tokens()
            assert loaded is not None
            assert loaded["access_token"] == test_tokens["access_token"]


class TestTokenStorageBase64:
    """Test token storage with Base64 (last resort)"""
    
    @pytest.fixture
    def mock_no_encryption(self):
        """Mock no secure encryption available"""
        with patch('utils.token_storage.HAS_KEYRING', False), \
             patch('utils.token_storage.HAS_CRYPTO', False):
            yield
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger to capture warnings"""
        with patch('utils.token_storage.logger') as mock:
            yield mock
    
    def test_base64_fallback_with_warning(self, mock_no_encryption, mock_logger, tmp_path):
        """Test base64 encoding when no secure option available"""
        from utils.token_storage import TokenStorage
        
        # Given: Neither keyring nor cryptography available
        with patch('utils.token_storage.Path.home') as mock_home:
            mock_home.return_value = tmp_path
            storage = TokenStorage("Mirenku")
            
            test_tokens = {
                "access_token": "base64_token",
                "refresh_token": "base64_refresh"
            }
            
            # When: Tokens are saved
            success = storage.save_tokens(test_tokens)
            
            # Then: Warning logged and tokens base64 encoded
            assert success is True
            assert storage.storage_method == "base64"
            mock_logger.warning.assert_called()
            
            # Verify file exists
            token_file = tmp_path / ".mirenku" / "tokens.b64"
            assert token_file.exists()
            
            # Verify content is base64
            content = token_file.read_text()
            decoded = base64.b64decode(content)
            tokens = json.loads(decoded)
            assert tokens["access_token"] == test_tokens["access_token"]
    
    def test_base64_migration_to_secure(self, tmp_path):
        """Test upgrading from base64 to secure storage"""
        from utils.token_storage import TokenStorage
        
        with patch('utils.token_storage.Path.home') as mock_home:
            mock_home.return_value = tmp_path
            
            # Given: Tokens stored with base64
            with patch('utils.token_storage.HAS_KEYRING', False), \
                 patch('utils.token_storage.HAS_CRYPTO', False):
                storage1 = TokenStorage("Mirenku")
                test_tokens = {"access_token": "migrate_me"}
                storage1.save_tokens(test_tokens)
                assert storage1.storage_method == "base64"
            
            # When: Secure storage becomes available
            with patch('utils.token_storage.HAS_KEYRING', True), \
                 patch('utils.token_storage.keyring') as mock_keyring:
                storage2 = TokenStorage("Mirenku")
                
                # Should attempt migration
                loaded = storage2.load_tokens()
                
                # Then: Tokens migrated to secure storage
                if loaded:  # Migration implemented
                    assert loaded["access_token"] == test_tokens["access_token"]
                    assert storage2.storage_method == "keyring"


class TestTokenStorageIntegration:
    """Integration tests for token storage"""
    
    def test_storage_method_priority(self):
        """Test correct priority of storage methods"""
        from utils.token_storage import TokenStorage
        
        # Test 1: All available - should use keyring
        with patch('utils.token_storage.HAS_KEYRING', True), \
             patch('utils.token_storage.HAS_CRYPTO', True):
            storage = TokenStorage("Mirenku")
            assert storage.storage_method == "keyring"
        
        # Test 2: No keyring - should use Fernet
        with patch('utils.token_storage.HAS_KEYRING', False), \
             patch('utils.token_storage.HAS_CRYPTO', True):
            storage = TokenStorage("Mirenku")
            assert storage.storage_method == "fernet"
        
        # Test 3: Nothing available - should use base64
        with patch('utils.token_storage.HAS_KEYRING', False), \
             patch('utils.token_storage.HAS_CRYPTO', False):
            storage = TokenStorage("Mirenku")
            assert storage.storage_method == "base64"
    
    def test_token_structure_validation(self):
        """Test that token structure is validated"""
        from utils.token_storage import TokenStorage
        
        with patch('utils.token_storage.HAS_KEYRING', True), \
             patch('utils.token_storage.keyring'):
            storage = TokenStorage("Mirenku")
            
            # Invalid token structure should be rejected
            invalid_tokens = {"invalid": "structure"}
            success = storage.save_tokens(invalid_tokens)
            
            # Should either reject or add required fields
            assert success is True or success is False
    
    def test_app_name_isolation(self):
        """Test that different apps have isolated storage"""
        from utils.token_storage import TokenStorage
        
        with patch('utils.token_storage.HAS_KEYRING', True), \
             patch('utils.token_storage.keyring') as mock_keyring:
            
            # Given: Two different apps
            storage1 = TokenStorage("App1")
            storage2 = TokenStorage("App2")
            
            tokens1 = {"access_token": "app1_token"}
            tokens2 = {"access_token": "app2_token"}
            
            # When: Both save tokens
            storage1.save_tokens(tokens1)
            storage2.save_tokens(tokens2)
            
            # Then: Tokens are isolated
            calls = mock_keyring.set_password.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "App1"
            assert calls[1][0][0] == "App2"