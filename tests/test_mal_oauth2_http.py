"""
Test suite for MALOAuth2HTTPClient — the live OAuth client (F8).

The deleted protocol-client tests covered a client nothing used; this file
covers the client the app actually runs: PKCE-plain, CSRF state, port
fallback, token refresh, persist-failure handling, and 401-retry.
"""

import json
import pytest
import socket
import sys
import os
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import parse_qs, urlparse

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def client(tmp_path):
    """Client with token storage patched out"""
    with patch('services.mal_oauth2_http.TokenStorage') as mock_storage_cls:
        storage = mock_storage_cls.return_value
        storage.get_storage_info.return_value = {"available": True, "secure": True}
        storage.load_tokens.return_value = None
        storage.save_tokens.return_value = True
        from services.mal_oauth2_http import MALOAuth2HTTPClient
        c = MALOAuth2HTTPClient("test_client_id", tmp_path / "tokens.json")
        yield c


def make_response(payload, status=200):
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(payload).encode()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=response)
    ctx.__exit__ = MagicMock(return_value=None)
    return ctx


class TestPKCE:
    def test_pkce_is_plain_method(self, client):
        """MAL does not properly support S256: challenge must equal verifier"""
        verifier, challenge = client._generate_pkce_pair()
        assert challenge == verifier

    def test_verifier_length_valid(self, client):
        """RFC 7636: verifier must be 43-128 characters"""
        verifier, _ = client._generate_pkce_pair()
        assert 43 <= len(verifier) <= 128

    def test_verifiers_are_unique(self, client):
        assert client._generate_pkce_pair()[0] != client._generate_pkce_pair()[0]

    def test_authorization_url_contents(self, client):
        url = client.get_authorization_url()
        params = parse_qs(urlparse(url).query)

        assert params["response_type"] == ["code"]
        assert params["client_id"] == ["test_client_id"]
        assert params["code_challenge_method"] == ["plain"]
        assert params["code_challenge"] == [client.code_verifier]
        assert params["state"][0] == client.state
        assert len(client.state) >= 32


class TestPortFallback:
    def test_default_port_when_free(self, client):
        with patch.object(client, '_is_port_free', return_value=True):
            assert client._find_free_port() == client.CALLBACK_PORT

    def test_fallback_when_default_taken(self, client):
        """If 8080 is occupied, the next free port in 8080-8089 is used"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
            blocker.bind(("localhost", client.CALLBACK_PORT))
            port = client._find_free_port()
            assert port != client.CALLBACK_PORT
            assert 8080 <= port <= 8089

    def test_no_ports_raises(self, client):
        with patch.object(client, '_is_port_free', return_value=False):
            with pytest.raises(RuntimeError):
                client._find_free_port()


class TestTokenExchange:
    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_successful_exchange_saves_tokens(self, mock_urlopen, client):
        client.code_verifier = "verifier"
        mock_urlopen.return_value = make_response({
            "access_token": "at", "refresh_token": "rt", "expires_in": 3600,
        })

        assert client._exchange_code_for_tokens("authcode") is True
        assert client.access_token == "at"
        assert client.refresh_token == "rt"
        assert client.token_expiry > datetime.now()

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_persist_failure_refuses_success(self, mock_urlopen, client):
        """If tokens cannot be saved, the client must NOT claim the user is
        authenticated — a 'connected' state that vanishes on restart is worse
        than a clean failure."""
        client.code_verifier = "verifier"
        client.token_storage.save_tokens.return_value = False
        mock_urlopen.return_value = make_response({
            "access_token": "at", "refresh_token": "rt",
        })

        assert client._exchange_code_for_tokens("authcode") is False
        assert client.access_token is None
        assert client.refresh_token is None

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_http_error_returns_false(self, mock_urlopen, client):
        client.code_verifier = "verifier"
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=400, msg="Bad Request", hdrs={}, fp=None
        )
        assert client._exchange_code_for_tokens("authcode") is False


class TestTokenRefresh:
    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_refresh_success(self, mock_urlopen, client):
        client.refresh_token = "old_rt"
        mock_urlopen.return_value = make_response({
            "access_token": "new_at", "refresh_token": "new_rt", "expires_in": 3600,
        })

        assert client.refresh_access_token() is True
        assert client.access_token == "new_at"
        assert client.refresh_token == "new_rt"

    def test_refresh_without_refresh_token(self, client):
        client.refresh_token = None
        assert client.refresh_access_token() is False

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_refresh_network_failure(self, mock_urlopen, client):
        client.refresh_token = "rt"
        mock_urlopen.side_effect = urllib.error.URLError("offline")
        assert client.refresh_access_token() is False

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_refresh_persist_failure(self, mock_urlopen, client):
        client.refresh_token = "rt"
        client.token_storage.save_tokens.return_value = False
        mock_urlopen.return_value = make_response({
            "access_token": "new_at", "refresh_token": "new_rt",
        })
        assert client.refresh_access_token() is False


class TestIsAuthenticated:
    def test_no_token(self, client):
        assert client.is_authenticated() is False

    def test_valid_token(self, client):
        client.access_token = "at"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        assert client.is_authenticated() is True

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_expired_token_triggers_refresh(self, mock_urlopen, client):
        client.access_token = "at"
        client.refresh_token = "rt"
        client.token_expiry = datetime.now() - timedelta(hours=1)
        mock_urlopen.return_value = make_response({
            "access_token": "new_at", "refresh_token": "new_rt", "expires_in": 3600,
        })

        assert client.is_authenticated() is True
        assert client.access_token == "new_at"

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_expired_token_failed_refresh(self, mock_urlopen, client):
        client.access_token = "at"
        client.refresh_token = "rt"
        client.token_expiry = datetime.now() - timedelta(hours=1)
        mock_urlopen.side_effect = urllib.error.URLError("offline")

        assert client.is_authenticated() is False


class TestMakeApiRequest:
    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_bearer_header_sent(self, mock_urlopen, client):
        client.access_token = "at"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        mock_urlopen.return_value = make_response({"ok": True})

        result = client.make_api_request("/users/@me")

        assert result == {"ok": True}
        request = mock_urlopen.call_args[0][0]
        assert request.headers["Authorization"] == "Bearer at"

    def test_unauthenticated_returns_none(self, client):
        assert client.make_api_request("/users/@me") is None

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_401_refreshes_and_retries(self, mock_urlopen, client):
        """A mid-session 401 (token revoked server-side) must refresh once
        and retry the original request."""
        client.access_token = "at"
        client.refresh_token = "rt"
        client.token_expiry = datetime.now() + timedelta(hours=1)

        mock_urlopen.side_effect = [
            urllib.error.HTTPError(url="x", code=401, msg="Unauthorized", hdrs={}, fp=None),
            make_response({"access_token": "new_at", "refresh_token": "new_rt",
                           "expires_in": 3600}),
            make_response({"name": "TestUser"}),
        ]

        result = client.make_api_request("/users/@me")

        assert result == {"name": "TestUser"}
        assert client.access_token == "new_at"
        assert mock_urlopen.call_count == 3

    @patch('services.mal_oauth2_http.urllib.request.urlopen')
    def test_non_401_error_returns_none(self, mock_urlopen, client):
        client.access_token = "at"
        client.token_expiry = datetime.now() + timedelta(hours=1)
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=500, msg="Server Error", hdrs={}, fp=None
        )
        assert client.make_api_request("/users/@me") is None


class TestStateValidation:
    def test_state_mismatch_rejected(self, client):
        """CSRF protection: a callback with the wrong state must fail without
        exchanging the code"""
        client.state = "expected_state"

        server = Mock()

        class FakeCallbackThread:
            """Simulates the callback arriving with a forged state"""

            def __init__(self, target=None, **kwargs):
                self.daemon = False

            def start(self):
                server.auth_code = "code"
                server.auth_state = "attacker_state"
                server.auth_error = None

        with patch.object(client, '_find_free_port', return_value=8080), \
             patch('services.mal_oauth2_http.HTTPServer', return_value=server), \
             patch('services.mal_oauth2_http.webbrowser.open'), \
             patch('services.mal_oauth2_http.threading.Thread', FakeCallbackThread), \
             patch.object(client, 'get_authorization_url', return_value="https://x"), \
             patch.object(client, '_exchange_code_for_tokens') as mock_exchange:
            # keep client.state as set above (get_authorization_url is mocked)
            assert client.authorize() is False
            mock_exchange.assert_not_called()
