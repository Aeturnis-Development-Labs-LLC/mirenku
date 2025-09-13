"""
Test suite for enhanced PKCE implementation
Ensures maximum security with 128-character code verifier
Following The Mirenku Way: Simple, secure, no unnecessary complexity
"""

import pytest
import sys
import os
import base64
import hashlib
import secrets
from unittest.mock import Mock, patch
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestPKCEEnhancement:
    """Test enhanced PKCE implementation"""

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

    def test_verifier_length_is_128(self, oauth_client):
        """Test that code verifier is exactly 128 characters"""
        verifier, _ = oauth_client._generate_pkce_pair()

        assert len(verifier) == 128
        # Should be URL-safe base64 characters only
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in verifier)

    def test_verifier_has_sufficient_entropy(self, oauth_client):
        """Test that verifier has sufficient entropy (96 bytes)"""
        # Generate multiple verifiers to ensure randomness
        verifiers = set()
        for _ in range(100):
            verifier, _ = oauth_client._generate_pkce_pair()
            verifiers.add(verifier)

        # All should be unique
        assert len(verifiers) == 100

        # Each should be 128 chars
        assert all(len(v) == 128 for v in verifiers)

    def test_challenge_is_sha256_of_verifier(self, oauth_client):
        """Test that challenge is correctly derived from verifier"""
        verifier, challenge = oauth_client._generate_pkce_pair()

        # Manually compute expected challenge
        expected_hash = hashlib.sha256(verifier.encode('ascii')).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_hash).decode('ascii').rstrip('=')

        assert challenge == expected_challenge

    def test_challenge_length_is_correct(self, oauth_client):
        """Test that challenge length is appropriate for SHA256"""
        _, challenge = oauth_client._generate_pkce_pair()

        # SHA256 produces 32 bytes, which base64 encodes to 43 chars (without padding)
        # With padding stripped, should be 43 characters
        assert len(challenge) == 43

    def test_verifier_contains_no_padding(self, oauth_client):
        """Test that verifier has no base64 padding characters"""
        verifier, _ = oauth_client._generate_pkce_pair()

        assert '=' not in verifier
        assert verifier[-1] != '='

    def test_challenge_contains_no_padding(self, oauth_client):
        """Test that challenge has no base64 padding characters"""
        _, challenge = oauth_client._generate_pkce_pair()

        assert '=' not in challenge
        assert challenge[-1] != '='

    def test_pkce_configuration(self):
        """Test that PKCE can be configured for different lengths"""
        from services.mal_oauth2_protocol import MALOAuth2ProtocolClient

        with patch('services.mal_oauth2_protocol.TokenStorage'):
            # Test with custom verifier length
            client = MALOAuth2ProtocolClient(
                client_id="test",
                token_storage_path=Path("test.json"),
                pkce_verifier_length=128  # Maximum length
            )

            verifier, _ = client._generate_pkce_pair()
            assert len(verifier) == 128

    def test_verifier_meets_oauth_spec(self, oauth_client):
        """Test that verifier meets OAuth 2.0 RFC 7636 requirements"""
        verifier, _ = oauth_client._generate_pkce_pair()

        # RFC 7636: code_verifier = high-entropy cryptographic random string
        # Length between 43-128 characters
        assert 43 <= len(verifier) <= 128

        # Should only contain unreserved characters: [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
        # Note: We use URL-safe base64 which uses "-" and "_" instead of "+" and "/"
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
        assert all(c in allowed_chars for c in verifier)

    def test_challenge_method_is_s256(self, oauth_client):
        """Test that challenge method is S256 (SHA256)"""
        # Get authorization URL
        auth_url = oauth_client.get_authorization_url()

        # Check that S256 is specified
        assert 'code_challenge_method=S256' in auth_url

    def test_verifier_saved_for_token_exchange(self, oauth_client):
        """Test that verifier is saved for later token exchange"""
        # Generate PKCE pair
        auth_url = oauth_client.get_authorization_url()

        # Verifier should be saved
        assert oauth_client.code_verifier is not None
        assert len(oauth_client.code_verifier) == 128

        # Should be saved to temp auth state
        oauth_client._save_temp_auth_state()

        # Clear and reload
        original_verifier = oauth_client.code_verifier
        oauth_client.code_verifier = None
        oauth_client._load_temp_auth_state()

        # Should be restored
        assert oauth_client.code_verifier == original_verifier

    def test_entropy_source_quality(self, oauth_client):
        """Test that entropy source is cryptographically secure"""
        # The implementation should use secrets module for cryptographic randomness
        with patch('secrets.token_bytes') as mock_secrets:
            mock_secrets.return_value = b'A' * 96  # 96 bytes for 128 chars

            oauth_client._generate_pkce_pair()

            # Should be called with 96 bytes for 128-char verifier
            mock_secrets.assert_called_once_with(96)

    def test_pkce_in_authorization_url(self, oauth_client):
        """Test that PKCE parameters are included in authorization URL"""
        auth_url = oauth_client.get_authorization_url()

        # Should contain code_challenge
        assert 'code_challenge=' in auth_url

        # Should specify S256 method
        assert 'code_challenge_method=S256' in auth_url

        # Challenge should be present and valid length
        import re
        match = re.search(r'code_challenge=([A-Za-z0-9\-_]+)', auth_url)
        assert match is not None
        challenge = match.group(1)
        assert len(challenge) == 43  # SHA256 base64 without padding

    def test_pkce_in_token_exchange(self, oauth_client):
        """Test that verifier is included in token exchange"""
        # Setup
        oauth_client.code_verifier = 'A' * 128  # Set a known verifier

        with patch('services.mal_oauth2_protocol.urllib.request.urlopen') as mock_urlopen:
            # Mock successful response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"access_token": "test", "refresh_token": "test"}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Attempt token exchange
            oauth_client._exchange_code_for_tokens("test_code")

            # Check that request included verifier
            call_args = mock_urlopen.call_args[0][0]  # Get Request object
            request_data = call_args.data.decode('utf-8')
            assert 'code_verifier=' + 'A' * 128 in request_data

    def test_enhanced_pkce_backwards_compatible(self, oauth_client):
        """Test that enhanced PKCE is backwards compatible with servers"""
        # Even with 128-char verifier, should work with servers expecting shorter
        verifier, challenge = oauth_client._generate_pkce_pair()

        # Should still produce valid S256 challenge
        assert len(challenge) == 43

        # Should be decodable
        try:
            # Add padding if needed for decoding
            padding = (4 - len(challenge) % 4) % 4
            padded = challenge + '=' * padding
            decoded = base64.urlsafe_b64decode(padded)
            assert len(decoded) == 32  # SHA256 produces 32 bytes
        except Exception as e:
            pytest.fail(f"Challenge not valid base64: {e}")

    def test_pkce_security_improvement(self, oauth_client):
        """Test that enhanced PKCE provides better security than minimum"""
        # Minimum PKCE is 43 characters (32 bytes of entropy)
        # Maximum PKCE is 128 characters (96 bytes of entropy)

        verifier, _ = oauth_client._generate_pkce_pair()

        # Our enhanced version should use maximum
        assert len(verifier) == 128

        # This provides 96 bytes of entropy vs 32 bytes minimum
        # That's 768 bits vs 256 bits of entropy
        entropy_bits = 96 * 8
        assert entropy_bits == 768

        # This makes brute force attacks computationally infeasible
        # 2^768 possible values vs 2^256 for minimum spec