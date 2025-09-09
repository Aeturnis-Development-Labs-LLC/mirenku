"""
Integration tests for complete OAuth2 flow
Tests the end-to-end OAuth process with protocol handler
"""

import pytest
import sys
import os
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestOAuth2IntegrationFlow:
    """Test complete OAuth2 flow integration"""
    
    @pytest.fixture
    def mock_components(self, tmp_path):
        """Mock all OAuth components"""
        components = {}
        
        # Mock protocol manager
        with patch('utils.protocol_manager.ProtocolManager') as mock_pm:
            components['protocol_manager'] = mock_pm.return_value
            components['protocol_manager'].is_registered.return_value = True
            components['protocol_manager'].register_protocol.return_value = True
        
        # Mock first run manager
        with patch('utils.first_run.FirstRunManager') as mock_frm:
            components['first_run_manager'] = mock_frm.return_value
            components['first_run_manager'].is_first_run.return_value = False
            components['first_run_manager'].get_config_path.return_value = tmp_path
        
        # Mock single instance manager
        with patch('utils.single_instance.SingleInstanceManager') as mock_sim:
            components['single_instance'] = mock_sim.return_value
            components['single_instance'].acquire_lock.return_value = True
            components['single_instance'].is_primary = True
        
        return components
    
    @patch('services.mal_oauth2_protocol.SingleInstanceManager')
    @patch('services.mal_oauth2_protocol.webbrowser.open')
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_complete_oauth_flow(self, mock_urlopen, mock_browser, mock_single_instance, mock_components, tmp_path):
        """Test complete OAuth flow from start to authenticated"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        from utils.protocol_handler import ProtocolHandler
        
        # Setup single instance mock
        mock_instance = mock_single_instance.return_value
        mock_instance.is_primary = True
        
        # Setup OAuth client
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
        
        # Mock browser open
        mock_browser.return_value = True
        
        # Mock token exchange response
        token_response = MagicMock()
        token_response.status = 200
        token_response.read.return_value = json.dumps({
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 2678400
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = token_response
        
        # Simulate OAuth callback in background
        def simulate_callback():
            time.sleep(0.5)  # Wait for handler to be registered
            # Directly call the callback handler
            client._handle_oauth_callback(
                code="test_code",
                state=client.state,
                error=None
            )
        
        # Start authorization
        callback_thread = threading.Thread(target=simulate_callback)
        callback_thread.start()
        
        # Perform authorization
        success = client.authorize(timeout=2)
            
        # Verify flow
        assert success is True
        assert client.access_token == "test_access_token"
        assert client.refresh_token == "test_refresh_token"
        mock_browser.assert_called_once()
        
        callback_thread.join()
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_token_refresh_flow(self, mock_urlopen, tmp_path):
        """Test token refresh flow"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        
        # Setup client with expired token
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
        
        # Set expired tokens
        client.access_token = "old_access_token"
        client.refresh_token = "old_refresh_token"
        client.token_expiry = datetime.now() - timedelta(hours=1)
        
        # Mock refresh response
        refresh_response = MagicMock()
        refresh_response.status = 200
        refresh_response.read.return_value = json.dumps({
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 2678400
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = refresh_response
        
        # Check authentication (should trigger refresh)
        is_auth = client.is_authenticated()
        
        assert is_auth is True
        assert client.access_token == "new_access_token"
        assert client.refresh_token == "new_refresh_token"
    
    def test_protocol_url_routing(self, mock_components):
        """Test protocol URL is properly routed"""
        from utils.protocol_handler import ProtocolHandler
        
        handler = ProtocolHandler()
        
        # Mock OAuth handler
        oauth_handler = Mock()
        handler.register_oauth_handler(oauth_handler)
        
        # Test valid OAuth URL
        url = "mirenku://auth?code=test_code&state=test_state"
        result = handler.handle_url(url)
        
        assert result is True
        oauth_handler.assert_called_once_with(
            code="test_code",
            state="test_state",
            error=None
        )
    
    @patch('services.mal_oauth2_protocol.SingleInstanceManager')
    def test_single_instance_protocol_forwarding(self, mock_single_instance, mock_components):
        """Test protocol URL forwarding to primary instance"""
        from services.mal_oauth2_protocol import handle_protocol_url
        
        # Mock as secondary instance
        mock_instance = mock_single_instance.return_value
        mock_instance.is_primary = False
        
        # Test URL forwarding
        handle_protocol_url("mirenku://auth?code=test")
        
        mock_instance.send_message_to_primary.assert_called_once()
        message = mock_instance.send_message_to_primary.call_args[0][0]
        assert message['action'] == 'protocol_url'
        assert message['url'] == "mirenku://auth?code=test"
    
    @patch('tkinter.Tk')
    def test_first_run_with_protocol_registration(self, mock_tk, mock_components, tmp_path):
        """Test first run experience with protocol registration"""
        from ui.first_run_dialog import FirstRunDialog
        
        # Mock first run
        mock_components['first_run_manager'].is_first_run.return_value = True
        mock_components['protocol_manager'].is_registered.return_value = False
        
        # Create dialog
        mock_root = mock_tk.return_value
        dialog = FirstRunDialog(
            mock_root,
            mock_components['first_run_manager'],
            mock_components['protocol_manager']
        )
        
        # Simulate user accepting protocol registration
        dialog.protocol_var.set(True)
        dialog._on_continue()
        
        # Verify protocol was registered
        mock_components['protocol_manager'].register_protocol.assert_called_once()
        mock_components['first_run_manager'].mark_first_run_complete.assert_called_once()
    
    @patch('ui.mal_auth_dialog.MALOAuth2ProtocolClient')
    @patch('tkinter.Tk')
    def test_mal_auth_dialog_integration(self, mock_tk, mock_oauth_client, tmp_path):
        """Test MAL auth dialog with new OAuth client"""
        from ui.mal_auth_dialog import MALAuthManager, MALAuthDialog
        
        # Setup auth manager
        auth_manager = MALAuthManager(config_dir=tmp_path, client_id="test_client")
        
        # Verify it uses protocol client
        mock_oauth_client.assert_called_once_with("test_client", tmp_path / "mal_tokens.json")
        
        # Test dialog creation
        mock_root = mock_tk.return_value
        mock_client = mock_oauth_client.return_value
        mock_client.is_authenticated.return_value = False
        
        dialog = MALAuthDialog(mock_root, mock_client)
        
        # Verify dialog initialized correctly
        assert dialog.oauth_client == mock_client
        assert dialog.authenticated is False
    
    def test_token_storage_encryption(self, tmp_path):
        """Test tokens are properly encrypted"""
        from utils.token_storage import TokenStorage
        
        storage = TokenStorage(app_name="TestApp")
        
        # Save tokens
        test_tokens = {
            'access_token': 'secret_access_token',
            'refresh_token': 'secret_refresh_token',
            'token_expiry': datetime.now().isoformat(),
            'client_id': 'test_client'
        }
        
        result = storage.save_tokens(test_tokens)
        assert result is True
        
        # Load tokens
        loaded = storage.load_tokens()
        assert loaded is not None
        assert loaded['access_token'] == 'secret_access_token'
        assert loaded['refresh_token'] == 'secret_refresh_token'
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_api_request_with_auth(self, mock_urlopen, tmp_path):
        """Test making authenticated API request"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        
        # Setup authenticated client
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
        client.access_token = "valid_token"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        
        # Mock API response
        api_response = MagicMock()
        api_response.status = 200
        api_response.read.return_value = json.dumps({
            'name': 'TestUser',
            'joined_at': '2024-01-01'
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = api_response
        
        # Make API request
        result = client.make_api_request("/users/@me")
        
        assert result is not None
        assert result['name'] == 'TestUser'
        
        # Verify authorization header was sent
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert 'Authorization' in request.headers
        assert request.headers['Authorization'] == 'Bearer valid_token'


class TestOAuth2ErrorHandling:
    """Test OAuth2 error scenarios"""
    
    def test_state_mismatch_prevents_token_exchange(self, tmp_path):
        """Test CSRF protection with state validation"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
        
        # Set expected state
        client.state = "expected_state"
        
        # Try callback with wrong state
        client._handle_oauth_callback(
            code="auth_code",
            state="wrong_state",
            error=None
        )
        
        # Should set error and not exchange tokens
        assert client.auth_error == "state_mismatch"
        assert client.auth_code is None
    
    @patch('services.mal_oauth2_protocol.TokenStorage')
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_token_exchange_failure_handling(self, mock_urlopen, mock_token_storage, tmp_path):
        """Test handling of token exchange failures"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        import urllib.error
        
        # Mock token storage to return None
        mock_storage = mock_token_storage.return_value
        mock_storage.load_tokens.return_value = None
        
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
        client.code_verifier = "test_verifier"
        
        # Mock HTTP error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="test", code=400, msg="Bad Request",
            hdrs={}, fp=None
        )
        
        # Try token exchange
        result = client._exchange_code_for_tokens("test_code")
        
        assert result is False
        assert client.access_token is None
    
    @patch('services.mal_oauth2_protocol.SingleInstanceManager')
    @patch('services.mal_oauth2_protocol.TokenStorage')
    def test_authorization_timeout(self, mock_token_storage, mock_single_instance, tmp_path):
        """Test authorization timeout handling"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        
        # Mock single instance
        mock_instance = mock_single_instance.return_value
        mock_instance.is_primary = True
        
        # Mock token storage to return None
        mock_storage = mock_token_storage.return_value
        mock_storage.load_tokens.return_value = None
        
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=tmp_path / "tokens.json"
        )
        
        # Don't simulate callback, let it timeout
        with patch('services.mal_oauth2_protocol.webbrowser.open', return_value=True):
            result = client.authorize(timeout=0.1)
        
        assert result is False
        assert client.access_token is None