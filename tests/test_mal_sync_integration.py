"""
Integration tests for MAL sync with OAuth2
Tests that the new OAuth2 protocol client works with sync operations
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestMALSyncIntegration:
    """Test MAL sync operations with OAuth2"""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database"""
        db = Mock()
        cursor = Mock()
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=None)
        db.get_cursor.return_value = cursor
        return db
    
    @pytest.fixture
    def mock_oauth_client(self):
        """Mock OAuth2 protocol client"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        with patch('services.mal_oauth2_protocol.TokenStorage'):
            client = MALOAuth2ProtocolClient(
                client_id="test_client",
                token_storage_path=Path("test_tokens.json")
            )
            client.access_token = "valid_token"
            client.refresh_token = "refresh_token"
            client.token_expiry = datetime.now() + timedelta(days=30)
            return client
    
    @pytest.fixture
    def mal_api_service(self, mock_oauth_client):
        """Create MAL API v2 service"""
        from services.mal_api_v2_service import MALAPIv2Service
        return MALAPIv2Service(mock_oauth_client)
    
    @pytest.fixture
    def sync_service(self, mock_database, mal_api_service, mock_oauth_client):
        """Create sync service"""
        from services.sync_service import SyncService
        return SyncService(
            database=mock_database,
            mal_api_v2_service=mal_api_service,
            oauth_client=mock_oauth_client
        )
    
    def test_sync_service_authentication_check(self, sync_service, mock_oauth_client):
        """Test sync service checks OAuth authentication"""
        assert sync_service.is_authenticated is True
        assert sync_service.oauth_client == mock_oauth_client
        
        # Test refresh authentication
        result = sync_service.refresh_authentication()
        assert result is True
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_pull_user_list_with_oauth(self, mock_urlopen, mal_api_service):
        """Test pulling user anime list with OAuth"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            'data': [
                {
                    'node': {
                        'id': 1,
                        'title': 'Test Anime',
                        'main_picture': {'medium': 'https://example.com/image.jpg'}
                    },
                    'list_status': {
                        'status': 'watching',
                        'score': 8,
                        'num_episodes_watched': 5
                    }
                }
            ],
            'paging': {}
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Get user anime list
        result = mal_api_service.get_user_animelist()
        
        assert result is not None
        assert 'data' in result
        assert len(result['data']) == 1
        assert result['data'][0]['node']['title'] == 'Test Anime'
        
        # Verify OAuth token was used
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert 'Authorization' in request.headers
        assert request.headers['Authorization'] == 'Bearer valid_token'
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_push_anime_update_with_oauth(self, mock_urlopen, mal_api_service):
        """Test pushing anime updates with OAuth"""
        from services.mal_api_v2_service import MALStatus
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            'status': 'watching',
            'score': 9,
            'num_watched_episodes': 10
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Update anime status
        result = mal_api_service.update_anime_status(
            anime_id=1,
            status=MALStatus.WATCHING
        )
        
        assert result is True
        
        # Verify OAuth token and method
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.headers['Authorization'] == 'Bearer valid_token'
        assert request.get_method() == 'PATCH'
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_token_refresh_during_sync(self, mock_urlopen, mal_api_service, mock_oauth_client):
        """Test automatic token refresh during sync operations"""
        import urllib.error
        
        # Set token as expired
        mock_oauth_client.token_expiry = datetime.now() - timedelta(hours=1)
        
        # First call returns 401, triggering refresh
        error = urllib.error.HTTPError(
            url="test", code=401, msg="Unauthorized",
            hdrs={}, fp=None
        )
        
        # Mock refresh token response
        refresh_response = MagicMock()
        refresh_response.status = 200
        refresh_response.read.return_value = json.dumps({
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 2678400
        }).encode()
        
        # Mock successful API response after refresh
        api_response = MagicMock()
        api_response.status = 200
        api_response.read.return_value = json.dumps({
            'name': 'TestUser',
            'joined_at': '2024-01-01'
        }).encode()
        
        # First API call fails with 401, refresh succeeds, retry succeeds
        mock_urlopen.side_effect = [
            error,  # Initial API call fails
            MagicMock(__enter__=MagicMock(return_value=refresh_response)),  # Refresh
            MagicMock(__enter__=MagicMock(return_value=api_response))  # Retry
        ]
        
        # Make API request
        result = mal_api_service.get_user_info()
        
        assert result is not None
        assert result['name'] == 'TestUser'
        assert mock_oauth_client.access_token == 'new_access_token'
        assert mock_urlopen.call_count == 3
    
    def test_sync_queue_operations(self, sync_service, mock_database):
        """Test sync queue for offline operations"""
        from services.sync_service import SyncOperation
        
        # Queue an operation
        sync_service.queue_sync_operation(
            anime_id=1,
            operation=SyncOperation.UPDATE,
            data={'status': 'watching', 'score': 8}
        )
        
        # Verify database insert was called
        mock_database.get_cursor().execute.assert_called()
        call_args = mock_database.get_cursor().execute.call_args
        assert 'INSERT INTO sync_queue' in call_args[0][0]
    
    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_full_sync_flow(self, mock_urlopen, sync_service, mal_api_service):
        """Test full sync flow: auth -> pull -> update -> push"""
        # 1. Verify authentication
        assert sync_service.is_authenticated is True
        
        # 2. Mock pull response
        pull_response = MagicMock()
        pull_response.status = 200
        pull_response.read.return_value = json.dumps({
            'data': [
                {
                    'node': {'id': 1, 'title': 'Anime 1'},
                    'list_status': {'status': 'watching', 'score': 7}
                }
            ]
        }).encode()
        
        # 3. Mock update response
        update_response = MagicMock()
        update_response.status = 200
        update_response.read.return_value = json.dumps({
            'status': 'completed',
            'score': 9
        }).encode()
        
        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=pull_response)),
            MagicMock(__enter__=MagicMock(return_value=update_response))
        ]
        
        # Pull list
        anime_list = mal_api_service.get_user_animelist()
        assert anime_list is not None
        assert len(anime_list['data']) == 1
        
        # Update anime
        from services.mal_api_v2_service import MALStatus
        result = mal_api_service.update_anime_status(1, MALStatus.COMPLETED)
        assert result is True
        
        # Verify both calls used OAuth
        assert mock_urlopen.call_count == 2
        for call in mock_urlopen.call_args_list:
            request = call[0][0]
            assert 'Authorization' in request.headers
            assert 'Bearer' in request.headers['Authorization']


class TestMALAuthManager:
    """Test MAL Auth Manager with new OAuth client"""
    
    @patch('ui.mal_auth_dialog.MALOAuth2ProtocolClient')
    def test_auth_manager_uses_protocol_client(self, mock_oauth_class, tmp_path):
        """Test MALAuthManager uses new protocol client"""
        from ui.mal_auth_dialog import MALAuthManager
        
        # Create auth manager
        auth_manager = MALAuthManager(
            config_dir=tmp_path,
            client_id="test_client"
        )
        
        # Verify it created the protocol client
        mock_oauth_class.assert_called_once_with(
            "test_client",
            tmp_path / "mal_tokens.json"
        )
        
        assert auth_manager.oauth_client is not None
    
    @patch('tkinter.Tk')
    def test_auth_dialog_with_protocol_client(self, mock_tk):
        """Test MAL auth dialog works with protocol client"""
        from ui.mal_auth_dialog import MALAuthDialog
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        
        # Create mock OAuth client
        with patch('services.mal_oauth2_protocol.TokenStorage'):
            oauth_client = MALOAuth2ProtocolClient(
                client_id="test",
                token_storage_path=Path("test.json")
            )
            oauth_client.access_token = "token"
            oauth_client.token_expiry = datetime.now() + timedelta(days=1)
        
        # Create dialog
        mock_root = mock_tk.return_value
        dialog = MALAuthDialog(mock_root, oauth_client)
        
        # Check authentication status
        dialog.check_auth_status()
        
        assert dialog.authenticated is True