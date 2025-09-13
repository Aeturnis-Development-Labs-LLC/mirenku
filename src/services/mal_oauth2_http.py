"""
MAL OAuth2 client using HTTP localhost callback
Clean, simple, reliable OAuth implementation
"""

import base64
import json
import logging
import secrets
import socket
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

from utils.token_storage import TokenStorage

logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback"""

    def do_GET(self):
        """Handle GET request from OAuth callback"""
        # Parse the URL to get query parameters
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Store the parameters in the server instance
        self.server.auth_code = params.get("code", [None])[0]
        self.server.auth_state = params.get("state", [None])[0]
        self.server.auth_error = params.get("error", [None])[0]

        # Send response to browser
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if self.server.auth_error:
            html = f"""
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #d32f2f;">Authorization Failed</h1>
                <p>Error: {self.server.auth_error}</p>
                <p>You can close this window and try again.</p>
            </body>
            </html>
            """
        elif self.server.auth_code:
            html = """
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #388e3c;">Authorization Successful!</h1>
                <p>You can close this window and return to Mirenku.</p>
                <script>setTimeout(function() { window.close(); }, 2000);</script>
            </body>
            </html>
            """
        else:
            html = """
            <html>
            <head><title>Authorization</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <p>Processing authorization...</p>
            </body>
            </html>
            """

        self.wfile.write(html.encode())

        # Shutdown the server after handling the callback
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        """Suppress default HTTP logging"""


class MALOAuth2HTTPClient:
    """OAuth2 client for MyAnimeList using HTTP localhost callback"""

    # OAuth2 endpoints
    AUTHORIZE_URL = "https://myanimelist.net/v1/oauth2/authorize"
    TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"
    API_BASE_URL = "https://api.myanimelist.net/v2"

    # HTTP callback configuration
    CALLBACK_PORT = 8080
    REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

    # Required scopes
    SCOPES = "anime:read anime:write user:read"

    def __init__(self, client_id: str, token_storage_path: Path):
        """
        Initialize OAuth2 client with HTTP callback

        Args:
            client_id: MAL application client ID
            token_storage_path: Path to store tokens
        """
        self.client_id = client_id
        self.token_storage_path = token_storage_path

        # Initialize token storage with proper app name
        self.token_storage = TokenStorage("Mirenku")

        # Check if storage is available
        storage_info = self.token_storage.get_storage_info()
        if not storage_info.get("available", True):
            logger.warning("No secure token storage available - authentication may not persist")
        elif not storage_info.get("secure", True):
            logger.warning("Token storage is not using secure encryption")

        # OAuth state
        self.state = None
        self.code_verifier = None
        self.code_challenge = None

        # Token data
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None

        # Load existing tokens if available
        self._load_tokens()

    def _find_free_port(self) -> int:
        """Find a free port for the callback server"""
        # Try the default port first
        if self._is_port_free(self.CALLBACK_PORT):
            return self.CALLBACK_PORT

        # Try a range of ports
        for port in range(8080, 8090):
            if self._is_port_free(port):
                return port

        # If no port found, raise error
        raise RuntimeError("No free port available for OAuth callback")

    def _is_port_free(self, port: int) -> bool:
        """Check if a port is free"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return True
            except:
                return False

    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        )

        # For MAL, use plain method - they don't properly support S256
        # code_challenge is the same as code_verifier for plain method
        code_challenge = code_verifier

        return code_verifier, code_challenge

    def get_authorization_url(self) -> str:
        """
        Generate authorization URL for user to visit

        Returns:
            Authorization URL
        """
        # Generate PKCE pair
        self.code_verifier, self.code_challenge = self._generate_pkce_pair()

        # Generate state for CSRF protection
        self.state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "plain",  # MAL only supports plain, not S256
            "scope": self.SCOPES,
            "redirect_uri": self.REDIRECT_URI,
            "state": self.state,
        }

        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    def authorize(self) -> bool:
        """
        Start OAuth authorization flow

        Returns:
            True if successful
        """
        try:
            # Find a free port for the callback
            port = self._find_free_port()
            redirect_uri = f"http://localhost:{port}/callback"

            # Update redirect URI if port changed
            if port != self.CALLBACK_PORT:
                self.REDIRECT_URI = redirect_uri
                logger.info(f"Using port {port} for OAuth callback")

            # Generate authorization URL
            auth_url = self.get_authorization_url()
            logger.info(f"Generated authorization URL: {auth_url}")

            # Start HTTP server for callback
            logger.info(f"Starting OAuth callback server on port {port}")
            server = HTTPServer(("localhost", port), OAuthCallbackHandler)
            server.auth_code = None
            server.auth_state = None
            server.auth_error = None

            # Open browser for authorization
            logger.info("Opening browser for MAL authorization...")
            logger.info(f"Full URL being opened: {auth_url}")
            webbrowser.open(auth_url)

            # Wait for callback (with timeout)
            server.timeout = 120  # 2 minutes timeout
            logger.info("Waiting for authorization callback...")

            # Handle requests until shutdown
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()

            # Wait for the callback to be received
            timeout = time.time() + 120
            while server.auth_code is None and server.auth_error is None:
                if time.time() > timeout:
                    logger.error("Authorization timeout")
                    server.shutdown()
                    return False
                time.sleep(0.5)

            # Check for errors
            if server.auth_error:
                logger.error(f"Authorization error: {server.auth_error}")
                return False

            # Verify state
            if server.auth_state != self.state:
                logger.error("State mismatch - possible CSRF attack")
                return False

            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens...")
            success = self._exchange_code_for_tokens(server.auth_code)

            if success:
                logger.info("Authorization successful!")
                return True
            logger.error("Failed to exchange authorization code")
            return False

        except Exception as e:
            logger.error(f"Authorization failed: {e}", exc_info=True)
            return False

    def _exchange_code_for_tokens(self, auth_code: str) -> bool:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            auth_code: Authorization code from callback

        Returns:
            True if successful
        """
        try:
            logger.info(
                f"Exchanging code of length {len(auth_code)}: {auth_code[:10]}... (truncated)"
            )
            logger.info(f"Using redirect_uri: {self.REDIRECT_URI}")
            logger.info(
                f"Using code_verifier of length {len(self.code_verifier)}: {self.code_verifier[:10]}... (truncated)"
            )

            # Prepare token request
            data = {
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": self.REDIRECT_URI,
                "code_verifier": self.code_verifier,
            }

            # Make token request
            request = urllib.request.Request(
                self.TOKEN_URL,
                data=urlencode(data).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    token_data = json.loads(response.read().decode("utf-8"))

                    # Store tokens
                    self.access_token = token_data["access_token"]
                    self.refresh_token = token_data["refresh_token"]
                    expires_in = token_data.get("expires_in", 2678400)  # 31 days default
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

                    # Save tokens
                    if not self._save_tokens():
                        logger.error("Failed to save tokens - authentication incomplete")
                        # Clear tokens since we can't save them
                        self.access_token = None
                        self.refresh_token = None
                        self.token_expiry = None
                        return False

                    logger.info("Successfully obtained access and refresh tokens")
                    return True

        except urllib.error.HTTPError as e:
            logger.error(f"Token exchange HTTP error {e.code}")
            try:
                error_data = json.loads(e.read().decode("utf-8"))
                error_msg = error_data.get("error", "Unknown")
                error_desc = error_data.get("error_description", "No description")
                logger.error(f"MAL Error: {error_msg} - {error_desc}")
            except:
                pass
            return False

        except Exception as e:
            logger.error(f"Token exchange failed: {e}", exc_info=True)
            return False

    def refresh_access_token(self, silent: bool = False) -> bool:
        """
        Refresh access token using refresh token

        Args:
            silent: If True, don't log errors (useful for startup checks)

        Returns:
            True if successful
        """
        if not self.refresh_token:
            if not silent:
                logger.error("No refresh token available")
            return False

        try:
            # Prepare refresh request
            data = {
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }

            # Make refresh request
            request = urllib.request.Request(
                self.TOKEN_URL,
                data=urlencode(data).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    token_data = json.loads(response.read().decode("utf-8"))

                    # Update tokens
                    self.access_token = token_data["access_token"]
                    self.refresh_token = token_data["refresh_token"]
                    expires_in = token_data.get("expires_in", 2678400)
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

                    # Save tokens
                    if not self._save_tokens():
                        logger.error("Failed to save refreshed tokens")
                        return False

                    logger.info("Successfully refreshed access token")
                    return True

        except Exception as e:
            if not silent:
                logger.error(f"Token refresh failed: {e}")
            else:
                logger.debug(f"Token refresh failed silently: {e}")
            return False

    def is_authenticated(self, silent_refresh: bool = False) -> bool:
        """Check if client has valid authentication

        Args:
            silent_refresh: If True, don't log errors during token refresh
        """
        if not self.access_token:
            return False

        # Check if token is expired
        if self.token_expiry and datetime.now() >= self.token_expiry:
            # Try to refresh
            if self.refresh_access_token(silent=silent_refresh):
                return True
            return False

        return True

    def get_access_token(self, silent_refresh: bool = False) -> Optional[str]:
        """Get current access token, refreshing if needed

        Args:
            silent_refresh: If True, don't log errors during token refresh
        """
        if self.is_authenticated(silent_refresh=silent_refresh):
            return self.access_token
        return None

    def _save_tokens(self, user_accepts_risk: bool = False):
        """Save tokens to storage

        Args:
            user_accepts_risk: Whether user accepts insecure storage risk

        Returns:
            bool: True if saved successfully
        """
        try:
            token_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_expiry": self.token_expiry.isoformat() if self.token_expiry else None,
                "client_id": self.client_id,
            }

            # Check if storage is available
            storage_info = self.token_storage.get_storage_info()
            if not storage_info.get("available", True):
                logger.error("No secure token storage available")
                return False

            # Save with risk acceptance if needed
            success = self.token_storage.save_tokens(token_data, user_accepts_risk)
            if success:
                logger.debug("Tokens saved successfully")
            else:
                logger.error("Failed to save tokens - no secure storage available")
            return success
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            return False

    def _load_tokens(self):
        """Load tokens from storage"""
        try:
            token_data = self.token_storage.load_tokens()
            if token_data:
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                expiry_str = token_data.get("token_expiry")
                if expiry_str:
                    self.token_expiry = datetime.fromisoformat(expiry_str)
                logger.debug("Tokens loaded successfully")
        except Exception as e:
            logger.debug(f"No existing tokens found: {e}")

    def clear_tokens(self):
        """Clear all stored tokens"""
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        try:
            self.token_storage.delete_tokens()
            logger.info("Tokens cleared")
        except Exception as e:
            logger.error(f"Failed to clear tokens: {e}")

    def logout(self):
        """Logout and clear all authentication data"""
        self.clear_tokens()
        logger.info("User logged out from MAL")

    def make_api_request(
        self, endpoint: str, method: str = "GET", data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make an authenticated API request to MAL

        Args:
            endpoint: API endpoint (e.g., "/users/@me")
            method: HTTP method
            data: Request data for POST/PUT

        Returns:
            Response data or None if failed
        """
        if not self.is_authenticated():
            logger.error("Not authenticated")
            return None

        try:
            url = f"{self.API_BASE_URL}{endpoint}"

            # Prepare request
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            if data:
                request = urllib.request.Request(
                    url, data=json.dumps(data).encode("utf-8"), headers=headers, method=method
                )
            else:
                request = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.info("Token expired, attempting refresh")
                if self.refresh_access_token():
                    # Retry the request
                    return self.make_api_request(endpoint, method, data)
            logger.error(f"API request failed: {e.code}")

        except Exception as e:
            logger.error(f"API request error: {e}")

        return None
