"""
Test suite for OAuth state parameter timestamp and expiration
Ensures state parameters expire after 5 minutes to prevent CSRF attacks
Following The Mirenku Way: Simple, local, secure
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import secrets
import base64
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestOAuthStateTimestamp:
    """Test OAuth state parameter security enhancements"""

    # Constants
    STATE_EXPIRY_MINUTES = 5

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
        return client

    def test_state_includes_timestamp(self, oauth_client):
        """Test that generated state includes timestamp"""
        state = oauth_client._generate_state()

        # State should be base64 encoded JSON with timestamp
        decoded = oauth_client._decode_state(state)

        assert decoded is not None
        assert 'timestamp' in decoded
        assert 'nonce' in decoded

        # Timestamp should be recent (within 1 second)
        timestamp = datetime.fromisoformat(decoded['timestamp'])
        time_diff = abs((datetime.now() - timestamp).total_seconds())
        assert time_diff < 1.0

    def test_state_validation_with_valid_timestamp(self, oauth_client):
        """Test state validation accepts recent timestamps"""
        # Generate a state
        state = oauth_client._generate_state()

        # Validate it immediately
        is_valid = oauth_client._validate_state_timestamp(state)

        assert is_valid is True

    def test_state_validation_rejects_expired_timestamp(self, oauth_client):
        """Test state validation rejects expired timestamps"""
        # Create an expired state
        expired_time = datetime.now() - timedelta(minutes=6)
        state_data = {
            'timestamp': expired_time.isoformat(),
            'nonce': secrets.token_urlsafe(32)
        }

        # Encode it
        state_json = json.dumps(state_data)
        state = base64.urlsafe_b64encode(state_json.encode()).decode().rstrip('=')

        # Validate it
        is_valid = oauth_client._validate_state_timestamp(state)

        assert is_valid is False

    def test_state_validation_rejects_invalid_format(self, oauth_client):
        """Test state validation handles invalid state formats gracefully"""
        # Test various invalid states
        invalid_states = [
            "not_base64",
            base64.urlsafe_b64encode(b"not json").decode(),
            base64.urlsafe_b64encode(json.dumps({"no": "timestamp"}).encode()).decode(),
            None,
            "",
            "%%%invalid%%%"
        ]

        for invalid_state in invalid_states:
            is_valid = oauth_client._validate_state_timestamp(invalid_state)
            assert is_valid is False, f"Should reject invalid state: {invalid_state}"

    def test_state_validation_boundary_conditions(self, oauth_client):
        """Test state validation at exact expiry boundaries"""
        # Test at 4:59 - should be valid
        almost_expired = datetime.now() - timedelta(minutes=4, seconds=59)
        state_data = {
            'timestamp': almost_expired.isoformat(),
            'nonce': secrets.token_urlsafe(32)
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        assert oauth_client._validate_state_timestamp(state) is True

        # Test at 5:01 - should be invalid
        just_expired = datetime.now() - timedelta(minutes=5, seconds=1)
        state_data = {
            'timestamp': just_expired.isoformat(),
            'nonce': secrets.token_urlsafe(32)
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        assert oauth_client._validate_state_timestamp(state) is False

    def test_oauth_callback_validates_timestamp(self, oauth_client):
        """Test that OAuth callback validates state timestamp"""
        # Generate a valid state
        oauth_client.state = oauth_client._generate_state()

        # Mock an expired state coming back
        expired_time = datetime.now() - timedelta(minutes=6)
        expired_state_data = {
            'timestamp': expired_time.isoformat(),
            'nonce': secrets.token_urlsafe(32)
        }
        expired_state = base64.urlsafe_b64encode(
            json.dumps(expired_state_data).encode()
        ).decode()

        # Try to handle callback with expired state
        oauth_client._handle_oauth_callback(
            code="test_code",
            state=expired_state,
            error=None
        )

        # Should set error for expired state
        assert oauth_client.auth_error == "state_expired"

    def test_state_storage_and_retrieval(self, oauth_client):
        """Test that state is properly stored and retrieved"""
        # Generate state
        state = oauth_client._generate_state()
        oauth_client.state = state

        # Save temp auth state
        oauth_client._save_temp_auth_state()

        # Clear state
        oauth_client.state = None

        # Load it back
        oauth_client._load_temp_auth_state()

        # Should be the same
        assert oauth_client.state == state

        # Should still be valid
        assert oauth_client._validate_state_timestamp(oauth_client.state) is True

    def test_state_cleanup_after_use(self, oauth_client):
        """Test that state is cleaned up after successful auth"""
        # Generate and save state
        oauth_client.state = oauth_client._generate_state()
        oauth_client.code_verifier = "test_verifier"
        oauth_client._save_temp_auth_state()

        # Mock successful token exchange that clears state
        def mock_exchange_side_effect(code):
            oauth_client._clear_temp_auth_state()
            return True

        with patch.object(oauth_client, '_exchange_code_for_tokens', side_effect=mock_exchange_side_effect):
            oauth_client._handle_oauth_callback(
                code="test_code",
                state=oauth_client.state,
                error=None
            )

        # State should be cleared after successful exchange
        assert oauth_client.state is None

    def test_state_logging_security(self, oauth_client):
        """Test that state parameter is not fully logged"""
        with patch('services.mal_oauth2_protocol.logger') as mock_logger:
            state = oauth_client._generate_state()

            # Generate auth URL (which logs state)
            oauth_client.get_authorization_url()

            # Check that full state is never logged
            for call in mock_logger.debug.call_args_list:
                if call and call[0]:
                    log_message = str(call[0][0])
                    # State should be truncated or masked in logs
                    assert state not in log_message

    def test_concurrent_auth_attempts(self, oauth_client):
        """Test handling of multiple concurrent auth attempts"""
        # First auth attempt
        state1 = oauth_client._generate_state()
        oauth_client.state = state1

        # Second auth attempt (user opened new tab)
        state2 = oauth_client._generate_state()

        # States should be different
        assert state1 != state2

        # Both should be valid
        assert oauth_client._validate_state_timestamp(state1) is True
        assert oauth_client._validate_state_timestamp(state2) is True

        # Only the matching state should be accepted
        oauth_client.state = state2
        oauth_client._handle_oauth_callback(
            code="test_code",
            state=state1,  # Wrong state
            error=None
        )
        assert oauth_client.auth_error == "state_mismatch"

    def test_state_timestamp_configuration(self):
        """Test that state expiry can be configured"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient

        with patch('services.mal_oauth2_protocol.TokenStorage'):
            # Test with custom expiry
            client = MALOAuth2ProtocolClient(
                client_id="test",
                token_storage_path=Path("test.json"),
                state_expiry_minutes=10  # Custom 10-minute expiry
            )

            # Create state that's 8 minutes old (valid for 10-min window)
            old_time = datetime.now() - timedelta(minutes=8)
            state_data = {
                'timestamp': old_time.isoformat(),
                'nonce': secrets.token_urlsafe(32)
            }
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

            assert client._validate_state_timestamp(state) is True

            # But 11 minutes old should fail
            older_time = datetime.now() - timedelta(minutes=11)
            state_data['timestamp'] = older_time.isoformat()
            state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

            assert client._validate_state_timestamp(state) is False

    def test_state_prevents_replay_attacks(self, oauth_client):
        """Test that state cannot be reused"""
        # Generate state
        state = oauth_client._generate_state()
        oauth_client.state = state

        # First use should work and clear state
        def mock_exchange_side_effect(code):
            oauth_client._clear_temp_auth_state()
            return True

        with patch.object(oauth_client, '_exchange_code_for_tokens', side_effect=mock_exchange_side_effect):
            oauth_client._handle_oauth_callback(
                code="test_code",
                state=state,
                error=None
            )

        # State should be cleared after use
        assert oauth_client.state is None

        # Second use should fail (state mismatch since oauth_client.state is None)
        oauth_client._handle_oauth_callback(
            code="another_code",
            state=state,
            error=None
        )
        assert oauth_client.auth_error == "state_mismatch"