"""
Test suite for token refresh buffer implementation
Ensures tokens are refreshed 5 minutes before expiry to prevent auth failures
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestTokenRefreshBuffer:
    """Test token refresh buffer functionality"""

    # Constants
    REFRESH_BUFFER_MINUTES = 5

    @pytest.fixture
    def mock_token_storage(self):
        """Mock token storage"""
        with patch('services.mal_oauth2_protocol.TokenStorage') as mock_storage:
            mock_storage.return_value.load_tokens.return_value = {
                'access_token': 'test_access_token',
                'refresh_token': 'test_refresh_token',
                'token_expiry': (datetime.now() + timedelta(hours=1)).isoformat()
            }
            yield mock_storage

    @pytest.fixture
    def oauth_client(self, mock_token_storage):
        """Create OAuth2 client with mocked storage"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=Path("test_tokens.json")
        )
        return client

    def test_token_needs_refresh_when_near_expiry(self, oauth_client):
        """Test that tokens are identified as needing refresh when near expiry"""
        # Set token expiry to 4 minutes from now (within buffer)
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=4)

        assert oauth_client.needs_token_refresh() is True

        # Set token expiry to 6 minutes from now (outside buffer)
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=6)

        assert oauth_client.needs_token_refresh() is False

    def test_token_needs_refresh_when_expired(self, oauth_client):
        """Test that expired tokens are identified as needing refresh"""
        # Set token as already expired
        oauth_client.token_expiry = datetime.now() - timedelta(minutes=1)

        assert oauth_client.needs_token_refresh() is True

    def test_token_needs_refresh_with_no_expiry(self, oauth_client):
        """Test behavior when token has no expiry set"""
        oauth_client.token_expiry = None

        # Should return False when no expiry is set (token doesn't expire)
        assert oauth_client.needs_token_refresh() is False

    def test_is_authenticated_refreshes_within_buffer(self, oauth_client):
        """Test that is_authenticated triggers refresh within buffer window"""
        # Set token expiry to 4 minutes from now (within buffer)
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=4)
        oauth_client.access_token = "valid_token"
        oauth_client.refresh_token = "valid_refresh"

        with patch.object(oauth_client, 'refresh_access_token', return_value=True) as mock_refresh:
            result = oauth_client.is_authenticated()

            # Should trigger refresh
            mock_refresh.assert_called_once()
            assert result is True

    def test_is_authenticated_no_refresh_outside_buffer(self, oauth_client):
        """Test that is_authenticated doesn't refresh outside buffer window"""
        # Set token expiry to 10 minutes from now (outside buffer)
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=10)
        oauth_client.access_token = "valid_token"

        with patch.object(oauth_client, 'refresh_access_token') as mock_refresh:
            result = oauth_client.is_authenticated()

            # Should NOT trigger refresh
            mock_refresh.assert_not_called()
            assert result is True

    @patch('services.mal_oauth2_protocol.urllib.request.urlopen')
    def test_refresh_updates_expiry_correctly(self, mock_urlopen, oauth_client):
        """Test that refresh correctly updates token expiry with buffer considered"""
        # Mock successful refresh response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600  # 1 hour
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        oauth_client.refresh_token = "valid_refresh"

        # Capture time before refresh
        time_before = datetime.now()

        result = oauth_client.refresh_access_token()

        # Check refresh was successful
        assert result is True
        assert oauth_client.access_token == 'new_access_token'

        # Check expiry is set correctly (should be ~1 hour from now)
        expected_expiry = time_before + timedelta(seconds=3600)
        actual_expiry = oauth_client.token_expiry

        # Allow 1 second tolerance for test execution time
        time_diff = abs((expected_expiry - actual_expiry).total_seconds())
        assert time_diff < 1.0

    def test_get_access_token_triggers_refresh(self, oauth_client):
        """Test that get_access_token triggers refresh when needed"""
        # Set token to expire in 3 minutes (within buffer)
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=3)
        oauth_client.access_token = "old_token"
        oauth_client.refresh_token = "valid_refresh"

        def mock_refresh_side_effect():
            oauth_client.access_token = "new_token"
            oauth_client.token_expiry = datetime.now() + timedelta(hours=1)
            return True

        with patch.object(oauth_client, 'refresh_access_token', side_effect=mock_refresh_side_effect) as mock_refresh:
            token = oauth_client.get_access_token()

            mock_refresh.assert_called_once()
            assert token == "new_token"

    def test_token_refresh_logging(self, oauth_client):
        """Test that token refresh events are properly logged"""
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=2)
        oauth_client.access_token = "valid_token"
        oauth_client.refresh_token = "valid_refresh"

        with patch('services.mal_oauth2_protocol.logger') as mock_logger:
            with patch.object(oauth_client, 'refresh_access_token', return_value=True):
                oauth_client.is_authenticated()

                # Check for buffer refresh log message
                mock_logger.info.assert_any_call(
                    "Token expiring soon (within 5-minute buffer), refreshing proactively"
                )

    def test_token_refresh_failure_handling(self, oauth_client):
        """Test handling of token refresh failures within buffer"""
        # Set token to expire in 3 minutes
        oauth_client.token_expiry = datetime.now() + timedelta(minutes=3)
        oauth_client.access_token = "valid_token"
        oauth_client.refresh_token = "valid_refresh"

        with patch.object(oauth_client, 'refresh_access_token', return_value=False) as mock_refresh:
            result = oauth_client.is_authenticated()

            # Should attempt refresh but return False on failure
            mock_refresh.assert_called_once()
            assert result is False

    def test_token_expiry_warning_threshold(self, oauth_client):
        """Test that appropriate warnings are issued as token approaches expiry"""
        # Test various time thresholds
        test_cases = [
            (1, "critical"),   # 1 minute - critical
            (3, "warning"),    # 3 minutes - warning
            (5, "info"),       # 5 minutes - info (buffer threshold)
            (10, None),        # 10 minutes - no warning
        ]

        for minutes_until_expiry, expected_level in test_cases:
            oauth_client.token_expiry = datetime.now() + timedelta(minutes=minutes_until_expiry)

            with patch('services.mal_oauth2_protocol.logger') as mock_logger:
                oauth_client.check_token_expiry_status()

                if expected_level == "critical":
                    mock_logger.critical.assert_called()
                elif expected_level == "warning":
                    mock_logger.warning.assert_called()
                elif expected_level == "info":
                    mock_logger.info.assert_called()
                else:
                    mock_logger.info.assert_not_called()
                    mock_logger.warning.assert_not_called()
                    mock_logger.critical.assert_not_called()

    def test_concurrent_refresh_prevention(self, oauth_client):
        """Test that multiple concurrent refresh attempts are prevented"""
        import threading

        oauth_client.token_expiry = datetime.now() + timedelta(minutes=2)
        oauth_client.refresh_token = "valid_refresh"

        refresh_count = 0

        def mock_refresh():
            nonlocal refresh_count
            refresh_count += 1
            # Simulate refresh taking time
            import time
            time.sleep(0.1)
            return True

        with patch.object(oauth_client, '_do_refresh_access_token', side_effect=mock_refresh):
            # Simulate multiple threads trying to refresh
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=oauth_client.refresh_access_token)
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # Only one refresh should have occurred
            assert refresh_count == 1

    def test_token_refresh_with_network_retry(self, oauth_client):
        """Test that token refresh retries on network errors"""
        import urllib.error

        oauth_client.refresh_token = "valid_refresh"

        # Create a proper mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            'access_token': 'new_token',
            'refresh_token': 'new_refresh',
            'expires_in': 3600
        }).encode()
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None

        # Simulate network error then success
        effects = [
            urllib.error.URLError("Network error"),
            mock_response
        ]

        with patch('services.mal_oauth2_protocol.urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = effects

            result = oauth_client.refresh_access_token_with_retry(max_retries=2)

            assert result is True
            assert oauth_client.access_token == 'new_token'
            assert mock_urlopen.call_count == 2

    def test_token_refresh_buffer_configuration(self):
        """Test that refresh buffer can be configured"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient

        # Test with custom buffer
        with patch('services.mal_oauth2_protocol.TokenStorage'):
            client = MALOAuth2ProtocolClient(
                client_id="test",
                token_storage_path=Path("test.json"),
                refresh_buffer_minutes=10  # Custom 10-minute buffer
            )

            client.token_expiry = datetime.now() + timedelta(minutes=8)
            assert client.needs_token_refresh() is True

            client.token_expiry = datetime.now() + timedelta(minutes=12)
            assert client.needs_token_refresh() is False