"""
MAL OAuth2 client using Protocol Handler (mirenku://)
Replaces HTTP server with custom protocol for OAuth callbacks
"""

import logging
import secrets
import hashlib
import base64
import json
import webbrowser
import threading
import time
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta

# Import our components
from utils.token_storage import TokenStorage
from utils.protocol_handler import ProtocolHandler
from utils.single_instance import SingleInstanceManager

logger = logging.getLogger(__name__)


class MALOAuth2ProtocolClient:
    """OAuth2 client for MyAnimeList using protocol handler"""
    
    # OAuth2 endpoints
    AUTHORIZE_URL = "https://myanimelist.net/v1/oauth2/authorize"
    TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"
    API_BASE_URL = "https://api.myanimelist.net/v2"
    
    # Protocol-based callback
    REDIRECT_URI = "mirenku://auth"
    
    # Required scopes
    SCOPES = "anime:read anime:write user:read"
    
    def __init__(self, client_id: str, token_storage_path: Path):
        """
        Initialize OAuth2 client with protocol handler
        
        Args:
            client_id: MAL application client ID
            token_storage_path: Path to store tokens
        """
        self.client_id = client_id
        self.token_storage_path = token_storage_path
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.code_verifier = None
        self.state = None
        self.redirect_uri = self.REDIRECT_URI
        
        # Initialize token storage with encryption
        self.token_storage = TokenStorage(app_name="Mirenku")
        
        # OAuth callback event
        self.auth_received = threading.Event()
        self.auth_code = None
        self.auth_error = None
        
        # Load existing tokens if available
        self._load_tokens()
    
    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash)
        challenge_bytes = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('ascii').rstrip('=')
        
        return code_verifier, code_challenge
    
    def _generate_state(self) -> str:
        """Generate random state for CSRF protection"""
        return secrets.token_urlsafe(32)
    
    def get_authorization_url(self) -> str:
        """
        Generate authorization URL for user consent
        
        Returns:
            Authorization URL to open in browser
        """
        # Generate PKCE pair and state
        self.code_verifier, code_challenge = self._generate_pkce_pair()
        self.state = self._generate_state()
        
        # Build authorization URL
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'scope': self.SCOPES,
            'redirect_uri': self.REDIRECT_URI,
            'state': self.state
        }
        
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"
    
    def _handle_oauth_callback(self, code: Optional[str], state: Optional[str], 
                              error: Optional[str]):
        """
        Handle OAuth callback from protocol handler
        
        Args:
            code: Authorization code
            state: State parameter for CSRF validation
            error: Error from authorization
        """
        if error:
            logger.error(f"OAuth error: {error}")
            self.auth_error = error
            self.auth_received.set()
            return
        
        # Validate state
        if state != self.state:
            logger.error(f"State mismatch: expected {self.state}, got {state}")
            self.auth_error = "state_mismatch"
            self.auth_received.set()
            return
        
        if not code:
            logger.error("No authorization code received")
            self.auth_error = "missing_code"
            self.auth_received.set()
            return
        
        # Store code and signal receipt
        self.auth_code = code
        self.auth_received.set()
    
    def authorize(self, timeout: int = 120) -> bool:
        """
        Perform OAuth2 authorization flow with protocol handler
        
        Args:
            timeout: Timeout in seconds to wait for callback
            
        Returns:
            True if authorization successful
        """
        try:
            # Setup protocol handler
            protocol_handler = ProtocolHandler()
            protocol_handler.register_oauth_handler(self._handle_oauth_callback)
            
            # Check if we need single instance handling
            instance_mgr = SingleInstanceManager()
            if not instance_mgr.is_primary:
                logger.warning("Not primary instance, forwarding OAuth to primary")
                # In a real app, we'd communicate with the primary instance
                return False
            
            # Get authorization URL
            auth_url = self.get_authorization_url()
            logger.info("Opening browser for MAL authorization...")
            logger.debug(f"Auth URL: {auth_url[:50]}...")  # Log partial URL
            
            # Reset event and error
            self.auth_received.clear()
            self.auth_code = None
            self.auth_error = None
            
            # Open browser
            if not webbrowser.open(auth_url):
                logger.error("Failed to open browser")
                return False
            
            # Wait for callback
            logger.info("Waiting for authorization callback via protocol handler...")
            if not self.auth_received.wait(timeout):
                logger.error("Authorization timeout")
                return False
            
            # Check for errors
            if self.auth_error:
                logger.error(f"Authorization failed: {self.auth_error}")
                return False
            
            if not self.auth_code:
                logger.error("No authorization code received")
                return False
            
            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens...")
            return self._exchange_code_for_tokens(self.auth_code)
            
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
            # Prepare token request
            data = {
                'client_id': self.client_id,
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.REDIRECT_URI,
                'code_verifier': self.code_verifier
            }
            
            logger.debug(f"Token exchange with client_id={self.client_id}")
            
            # Make token request
            request = urllib.request.Request(
                self.TOKEN_URL,
                data=urlencode(data).encode('utf-8'),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    token_data = json.loads(response.read().decode('utf-8'))
                    
                    # Store tokens
                    self.access_token = token_data['access_token']
                    self.refresh_token = token_data['refresh_token']
                    expires_in = token_data.get('expires_in', 2678400)  # 31 days default
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Save tokens with encryption
                    self._save_tokens()
                    
                    logger.info("Successfully obtained access token")
                    return True
                else:
                    logger.error(f"Token exchange failed with status {response.status}")
                    return False
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"Token exchange HTTP error {e.code}")
            
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get('error', 'Unknown')
                error_desc = error_data.get('error_description', 'No description')
                logger.error(f"MAL Error: {error_msg} - {error_desc}")
            except:
                pass
            
            return False
        except Exception as e:
            logger.error(f"Token exchange failed: {e}", exc_info=True)
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token
        
        Returns:
            True if successful
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            # Prepare refresh request
            data = {
                'client_id': self.client_id,
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            # Make refresh request
            request = urllib.request.Request(
                self.TOKEN_URL,
                data=urlencode(data).encode('utf-8'),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    token_data = json.loads(response.read().decode('utf-8'))
                    
                    # Update tokens
                    self.access_token = token_data['access_token']
                    self.refresh_token = token_data['refresh_token']
                    expires_in = token_data.get('expires_in', 2678400)
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Save tokens with encryption
                    self._save_tokens()
                    
                    logger.info("Successfully refreshed access token")
                    return True
                else:
                    logger.error(f"Token refresh failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if client is authenticated
        
        Returns:
            True if authenticated with valid token
        """
        if not self.access_token:
            return False
        
        # Check if token is expired
        if self._is_token_expired():
            # Try to refresh
            if self.refresh_access_token():
                return True
            else:
                return False
        
        return True
    
    def _is_token_expired(self) -> bool:
        """Check if access token is expired"""
        if not self.token_expiry:
            return True
        return datetime.now() >= self.token_expiry
    
    def get_access_token(self) -> Optional[str]:
        """
        Get current access token, refreshing if needed
        
        Returns:
            Access token or None if not authenticated
        """
        if self.is_authenticated():
            return self.access_token
        return None
    
    def _save_tokens(self):
        """Save tokens using encrypted storage"""
        try:
            # Create token data
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
                'client_id': self.client_id
            }
            
            # Use TokenStorage for encryption
            if self.token_storage.save_tokens(token_data):
                logger.info("Tokens saved securely")
            else:
                logger.error("Failed to save tokens securely")
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def _load_tokens(self):
        """Load tokens from encrypted storage"""
        try:
            # Use TokenStorage for decryption
            token_data = self.token_storage.load_tokens()
            
            if not token_data:
                return
            
            # Verify client ID matches
            if token_data.get('client_id') != self.client_id:
                logger.warning("Client ID mismatch in stored tokens")
                return
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            if token_data.get('token_expiry'):
                self.token_expiry = datetime.fromisoformat(token_data['token_expiry'])
            
            logger.info("Tokens loaded from secure storage")
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
    
    def logout(self):
        """Clear tokens and logout"""
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Clear from secure storage
        try:
            self.token_storage.save_tokens(None)
        except:
            pass
        
        logger.info("Logged out and tokens cleared")
    
    def make_api_request(self, endpoint: str, method: str = "GET", 
                        data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make authenticated API request to MAL
        
        Args:
            endpoint: API endpoint (relative to base URL)
            method: HTTP method
            data: Request data for POST/PATCH
            
        Returns:
            Response data or None on error
        """
        if not self.is_authenticated():
            logger.error("Not authenticated")
            return None
        
        try:
            url = f"{self.API_BASE_URL}{endpoint}"
            
            # Prepare request
            if data and method in ["POST", "PATCH"]:
                request_data = urlencode(data).encode('utf-8')
                request = urllib.request.Request(
                    url,
                    data=request_data,
                    method=method,
                    headers={
                        'Authorization': f'Bearer {self.access_token}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )
            else:
                request = urllib.request.Request(
                    url,
                    headers={'Authorization': f'Bearer {self.access_token}'}
                )
            
            with urllib.request.urlopen(request) as response:
                if response.status in [200, 201]:
                    return json.loads(response.read().decode('utf-8'))
                else:
                    logger.error(f"API request failed with status {response.status}")
                    return None
                    
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Token expired, try refresh
                if self.refresh_access_token():
                    # Retry request
                    return self.make_api_request(endpoint, method, data)
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None


def handle_protocol_url(url: str):
    """
    Global handler for protocol URLs
    Should be called from main application when protocol URL is received
    
    Args:
        url: Protocol URL (mirenku://...)
    """
    # Check if we're the primary instance
    instance_mgr = SingleInstanceManager()
    if not instance_mgr.is_primary:
        # Forward to primary instance
        instance_mgr.send_message_to_primary({
            'action': 'protocol_url',
            'url': url
        })
        return
    
    # Handle the URL
    protocol_handler = ProtocolHandler()
    protocol_handler.handle_url(url)