"""
Test suite for MAL OAuth2 Client with Protocol Handler
Tests OAuth2 flow using mirenku:// protocol instead of HTTP server
"""

import pytest
import sys
import os
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestMALOAuth2Protocol:
    """Test OAuth2 client with protocol handler"""
    
    @pytest.fixture
    def temp_token_path(self, tmp_path):
        """Create temporary path for token storage"""
        return tmp_path / "mal_tokens.json"
    
    @pytest.fixture
    def mock_token_storage(self):
        """Mock TokenStorage"""
        with patch('services.mal_oauth2_protocol.TokenStorage') as mock:
            storage = mock.return_value
            storage.save_tokens.return_value = True
            storage.load_tokens.return_value = None
            yield storage
    
    @pytest.fixture
    def oauth_client(self, temp_token_path, mock_token_storage):
        """Create OAuth2 client instance"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        return MALOAuth2ProtocolClient(
            client_id="test_client_id",
            token_storage_path=temp_token_path
        )
    
    def test_client_initialization(self, oauth_client):
        """Test client initialization"""
        assert oauth_client.client_id == "test_client_id"
        assert oauth_client.access_token is None
        assert oauth_client.refresh_token is None
        assert oauth_client.redirect_uri == "mirenku://auth"
    
    def test_generate_pkce_pair(self, oauth_client):
        """Test PKCE generation"""
        verifier, challenge = oauth_client._generate_pkce_pair()
        
        # Verify lengths
        assert len(verifier) >= 43
        assert len(verifier) <= 128
        assert len(challenge) >= 43
        
        # Verify uniqueness
        verifier2, challenge2 = oauth_client._generate_pkce_pair()
        assert verifier != verifier2
        assert challenge != challenge2
    
    def test_generate_state(self, oauth_client):
        """Test state generation for CSRF protection"""
        state1 = oauth_client._generate_state()
        state2 = oauth_client._generate_state()
        
        assert len(state1) > 20
        assert state1 != state2
    
    def test_get_authorization_url(self, oauth_client):
        """Test authorization URL generation"""
        url = oauth_client.get_authorization_url()
        
        assert "https://myanimelist.net/v1/oauth2/authorize" in url
        assert "client_id=test_client_id" in url
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url
        assert "redirect_uri=mirenku%3A%2F%2Fauth" in url  # URL encoded
        assert "state=" in url
        
        # Verify PKCE and state are stored
        assert oauth_client.code_verifier is not None
        assert oauth_client.state is not None
    
    @patch('services.mal_oauth2_protocol.webbrowser.open')
    @patch('services.mal_oauth2_protocol.ProtocolHandler')
    def test_authorize_with_protocol_handler(self, mock_protocol_class, mock_browser, oauth_client):
        """Test authorization flow with protocol handler"""
        # Setup mocks
        mock_browser.return_value = True
        mock_protocol = mock_protocol_class.return_value
        
        # Simulate successful OAuth callback
        def simulate_callback(callback):
            time.sleep(0.1)  # Small delay
            callback(
                code="test_auth_code",
                state=oauth_client.state,
                error=None
            )
        
        mock_protocol.register_oauth_handler.side_effect = lambda cb: simulate_callback(cb)
        
        # Mock token exchange
        with patch.object(oauth_client, '_exchange_code_for_tokens', return_value=True) as mock_exchange:
            result = oauth_client.authorize(timeout=1)
            
            assert result is True
            mock_browser.assert_called_once()
            mock_exchange.assert_called_once_with("test_auth_code")
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_exchange_code_for_tokens(self, mock_urlopen, oauth_client):
        """Test exchanging auth code for tokens"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 2678400
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        oauth_client.code_verifier = "test_verifier"
        result = oauth_client._exchange_code_for_tokens("test_auth_code")
        
        assert result is True
        assert oauth_client.access_token == "test_access_token"
        assert oauth_client.refresh_token == "test_refresh_token"
        assert oauth_client.token_expiry is not None
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_refresh_access_token(self, mock_urlopen, oauth_client):
        """Test refreshing access token"""
        # Setup initial tokens
        oauth_client.refresh_token = "old_refresh_token"
        oauth_client.token_expiry = datetime.now() - timedelta(hours=1)  # Expired
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 2678400
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        result = oauth_client.refresh_access_token()
        
        assert result is True
        assert oauth_client.access_token == "new_access_token"
        assert oauth_client.refresh_token == "new_refresh_token"
    
    def test_is_authenticated_no_token(self, oauth_client):
        """Test authentication check with no token"""
        assert oauth_client.is_authenticated() is False
    
    def test_is_authenticated_valid_token(self, oauth_client):
        """Test authentication check with valid token"""
        oauth_client.access_token = "valid_token"
        oauth_client.token_expiry = datetime.now() + timedelta(hours=1)
        
        assert oauth_client.is_authenticated() is True
    
    def test_is_authenticated_expired_token(self, oauth_client):
        """Test authentication check with expired token"""
        oauth_client.access_token = "expired_token"
        oauth_client.refresh_token = "refresh_token"
        oauth_client.token_expiry = datetime.now() - timedelta(hours=1)
        
        with patch.object(oauth_client, 'refresh_access_token', return_value=True):
            assert oauth_client.is_authenticated() is True
    
    def test_save_tokens_with_encryption(self, oauth_client, mock_token_storage):
        """Test saving tokens with encryption"""
        oauth_client.access_token = "test_access"
        oauth_client.refresh_token = "test_refresh"
        oauth_client.token_expiry = datetime.now() + timedelta(days=30)
        
        oauth_client._save_tokens()
        
        # Should use TokenStorage for encryption
        mock_token_storage.save_tokens.assert_called_once()
        saved_data = mock_token_storage.save_tokens.call_args[0][0]
        assert saved_data['access_token'] == "test_access"
        assert saved_data['refresh_token'] == "test_refresh"
    
    def test_load_tokens_with_decryption(self, oauth_client, mock_token_storage):
        """Test loading tokens with decryption"""
        mock_token_storage.load_tokens.return_value = {
            'access_token': 'loaded_access',
            'refresh_token': 'loaded_refresh',
            'token_expiry': datetime.now().isoformat(),
            'client_id': 'test_client_id'  # Must match oauth_client.client_id
        }
        
        oauth_client._load_tokens()
        
        assert oauth_client.access_token == "loaded_access"
        assert oauth_client.refresh_token == "loaded_refresh"
    
    @patch('services.mal_oauth2_protocol.SingleInstanceManager')
    def test_protocol_handler_with_single_instance(self, mock_single_instance, oauth_client):
        """Test integration with single instance manager"""
        mock_instance = mock_single_instance.return_value
        mock_instance.is_primary = False
        
        # Should check if primary instance
        from services.mal_oauth2_protocol import handle_protocol_url
        handle_protocol_url("mirenku://auth?code=123&state=abc")
        
        # Should forward to primary if not primary
        mock_instance.send_message_to_primary.assert_called_once()
    
    def test_logout_clears_tokens(self, oauth_client, mock_token_storage):
        """Test logout clears tokens"""
        oauth_client.access_token = "token_to_clear"
        oauth_client.refresh_token = "refresh_to_clear"
        oauth_client.logout()
        
        assert oauth_client.access_token is None
        assert oauth_client.refresh_token is None
        
        # Should clear from storage
        mock_token_storage.save_tokens.assert_called_with(None)


class TestOAuth2ProtocolSecurity:
    """Test OAuth2 security features"""
    
    @pytest.fixture
    def oauth_client(self, tmp_path):
        """Create OAuth2 client"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        return MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
    
    def test_state_validation_prevents_csrf(self, oauth_client):
        """Test state validation prevents CSRF attacks"""
        oauth_client.state = "expected_state"
        
        # Wrong state should fail
        with patch.object(oauth_client, '_exchange_code_for_tokens') as mock_exchange:
            oauth_client._handle_oauth_callback(
                code="auth_code",
                state="wrong_state",
                error=None
            )
            mock_exchange.assert_not_called()
    
    def test_pkce_prevents_code_interception(self, oauth_client):
        """Test PKCE prevents authorization code interception"""
        # Generate PKCE
        verifier1, challenge1 = oauth_client._generate_pkce_pair()
        
        # Verify challenge can't be reversed to get verifier
        import hashlib
        import base64
        
        # Try to reverse (should be impossible with SHA256)
        # This just verifies the challenge is properly hashed
        reconstructed = hashlib.sha256(verifier1.encode()).digest()
        reconstructed_b64 = base64.urlsafe_b64encode(reconstructed).decode().rstrip('=')
        
        assert reconstructed_b64 == challenge1
    
    def test_token_expiry_enforced(self, oauth_client):
        """Test token expiry is enforced"""
        oauth_client.access_token = "expired_token"
        oauth_client.token_expiry = datetime.now() - timedelta(seconds=1)
        
        # Should detect expired token
        assert oauth_client._is_token_expired() is True
    
    def test_no_token_leakage_in_logs(self, oauth_client, caplog):
        """Test tokens are not leaked in logs"""
        import logging
        caplog.set_level(logging.DEBUG)
        
        oauth_client.access_token = "secret_access_token"
        oauth_client.refresh_token = "secret_refresh_token"
        
        # Perform operations that might log
        oauth_client._save_tokens()
        
        # Check logs don't contain full tokens
        log_text = caplog.text
        assert "secret_access_token" not in log_text
        assert "secret_refresh_token" not in log_text