"""
Test suite for OAuth operation rate limiting
Prevents brute force attacks on token refresh and authorization
Following The Mirenku Way: Local protection, simple implementation
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import time
import threading
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestOAuthRateLimiting:
    """Test OAuth rate limiting functionality"""

    @pytest.fixture
    def mock_token_storage(self):
        """Mock token storage"""
        with patch('services.mal_oauth2_protocol.TokenStorage') as mock_storage:
            mock_storage.return_value.load_tokens.return_value = None
            yield mock_storage

    @pytest.fixture
    def oauth_client(self, mock_token_storage):
        """Create OAuth2 client with mocked storage"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient
        client = MALOAuth2ProtocolClient(
            client_id="test_client",
            token_storage_path=Path("test_tokens.json")
        )
        # Set up valid tokens for testing
        client.access_token = "test_token"
        client.refresh_token = "refresh_token"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        return client

    def test_rate_limit_on_authorization_attempts(self, oauth_client):
        """Test rate limiting on authorization attempts"""
        # Simulate multiple rapid authorization attempts
        for i in range(3):
            oauth_client.track_auth_attempt()

        # Fourth attempt should be rate limited
        is_limited = oauth_client.is_rate_limited('authorize')
        assert is_limited is True

        # Check that appropriate error is set
        with patch('services.mal_oauth2_protocol.logger') as mock_logger:
            result = oauth_client.authorize(timeout=1)
            assert result is False
            mock_logger.warning.assert_any_call(
                "Rate limit exceeded for authorization. Please wait before trying again."
            )

    def test_rate_limit_on_token_refresh(self, oauth_client):
        """Test rate limiting on token refresh attempts"""
        # Mock failed refresh attempts
        with patch.object(oauth_client, '_do_refresh_access_token', return_value=False):
            # Simulate multiple failed refresh attempts
            for i in range(5):
                oauth_client.refresh_access_token()

            # Next attempt should be rate limited
            is_limited = oauth_client.is_rate_limited('refresh')
            assert is_limited is True

    def test_exponential_backoff(self, oauth_client):
        """Test exponential backoff timing"""
        # Track attempts
        oauth_client.track_auth_attempt()
        wait_time_1 = oauth_client.get_backoff_time()
        assert wait_time_1 == 1  # First failure: 1 second

        oauth_client.track_auth_attempt()
        wait_time_2 = oauth_client.get_backoff_time()
        assert wait_time_2 == 2  # Second failure: 2 seconds

        oauth_client.track_auth_attempt()
        wait_time_3 = oauth_client.get_backoff_time()
        assert wait_time_3 == 4  # Third failure: 4 seconds

        oauth_client.track_auth_attempt()
        wait_time_4 = oauth_client.get_backoff_time()
        assert wait_time_4 == 8  # Fourth failure: 8 seconds

    def test_rate_limit_reset_after_success(self, oauth_client):
        """Test that rate limit resets after successful operation"""
        # Track some failed attempts
        for i in range(2):
            oauth_client.track_auth_attempt()

        # Successful operation should reset counter
        oauth_client.reset_rate_limit('authorize')

        # Should not be rate limited anymore
        is_limited = oauth_client.is_rate_limited('authorize')
        assert is_limited is False

    def test_rate_limit_time_window(self, oauth_client):
        """Test that rate limit expires after time window"""
        # Track attempts
        for i in range(3):
            oauth_client.track_auth_attempt()

        # Should be rate limited
        assert oauth_client.is_rate_limited('authorize') is True

        # Clear attempts and simulate time passing
        # (simpler than mocking time.time() everywhere)
        oauth_client._auth_attempts = [time.time() - 62 for _ in range(3)]

        # Should no longer be rate limited (attempts are old)
        assert oauth_client.is_rate_limited('authorize') is False

    def test_separate_limits_for_different_operations(self, oauth_client):
        """Test that different operations have separate rate limits"""
        # Hit rate limit for authorization
        for i in range(3):
            oauth_client.track_auth_attempt()

        assert oauth_client.is_rate_limited('authorize') is True

        # Refresh should still work
        assert oauth_client.is_rate_limited('refresh') is False

    def test_rate_limit_with_concurrent_requests(self, oauth_client):
        """Test rate limiting with concurrent requests"""
        results = []

        def attempt_auth():
            # Small delay to ensure threads start at slightly different times
            time.sleep(0.01)
            limited = oauth_client.is_rate_limited('authorize')
            results.append(limited)
            if not limited:
                oauth_client.track_auth_attempt()

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=attempt_auth)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have rate limited some attempts
        rate_limited_count = sum(1 for r in results if r)
        assert rate_limited_count > 0

    def test_rate_limit_logging(self, oauth_client):
        """Test that rate limiting events are properly logged"""
        with patch('services.mal_oauth2_protocol.logger') as mock_logger:
            # Hit rate limit
            for i in range(3):
                oauth_client.track_auth_attempt()

            oauth_client.is_rate_limited('authorize')

            # Check for rate limit log
            mock_logger.warning.assert_any_call(
                "Rate limit active for authorize: 3 attempts in last 60 seconds"
            )

    def test_rate_limit_configuration(self):
        """Test that rate limits can be configured"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient

        with patch('services.mal_oauth2_protocol.TokenStorage'):
            # Custom rate limits
            client = MALOAuth2ProtocolClient(
                client_id="test",
                token_storage_path=Path("test.json"),
                max_auth_attempts=5,  # Allow 5 attempts
                rate_limit_window=120  # In 2 minutes
            )

            # Should allow 4 attempts without limiting
            for i in range(4):
                client.track_auth_attempt()
                assert client.is_rate_limited('authorize') is False

            # Fifth attempt triggers limit
            client.track_auth_attempt()
            assert client.is_rate_limited('authorize') is True

    def test_rate_limit_persistence(self, oauth_client):
        """Test that rate limit state persists appropriately"""
        # Track attempts
        oauth_client.track_auth_attempt()
        oauth_client.track_auth_attempt()

        # Get current state
        attempts_before = len(oauth_client._auth_attempts)

        # Simulate some time passing (but within window)
        time.sleep(0.1)

        # Track another attempt
        oauth_client.track_auth_attempt()

        # Should have all attempts tracked
        attempts_after = len(oauth_client._auth_attempts)
        assert attempts_after == attempts_before + 1

    def test_failed_auth_lockout(self, oauth_client):
        """Test temporary lockout after multiple failed auth attempts"""
        # Simulate multiple failed auth attempts
        for i in range(5):
            oauth_client.track_failed_auth()

        # Should be locked out
        assert oauth_client.is_locked_out() is True

        # Should not allow authorization
        with patch('services.mal_oauth2_protocol.webbrowser.open'):
            result = oauth_client.authorize(timeout=1)
            assert result is False

    def test_lockout_duration(self, oauth_client):
        """Test that lockout expires after duration"""
        # Trigger lockout
        for i in range(5):
            oauth_client.track_failed_auth()

        assert oauth_client.is_locked_out() is True

        # Simulate time passing by modifying lockout time
        oauth_client._lockout_until = time.time() - 1  # Set to past

        # Should no longer be locked out
        assert oauth_client.is_locked_out() is False

    def test_refresh_attempt_tracking(self, oauth_client):
        """Test tracking of refresh attempts for rate limiting"""
        with patch.object(oauth_client, '_do_refresh_access_token', return_value=False):
            # Track failed refresh attempts (need 5 to trigger rate limit)
            for i in range(5):
                oauth_client.refresh_access_token()

            # Check attempt count
            assert len(oauth_client._refresh_attempts) == 5

            # Should be rate limited after 5 attempts
            assert oauth_client.is_rate_limited('refresh') is True