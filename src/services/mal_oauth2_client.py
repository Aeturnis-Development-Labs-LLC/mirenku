"""MAL OAuth2 client with PKCE support for desktop applications"""

import logging
import secrets
import hashlib
import base64
import json
import webbrowser
import threading
import time
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OAuth2CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth2 callback"""
    
    def do_GET(self):
        """Handle GET request from OAuth2 callback"""
        # Parse the URL to get query parameters
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        # Store the authorization code or error
        if 'code' in params:
            self.server.auth_code = params['code'][0]
            self.server.state = params.get('state', [None])[0]
            success = True
            message = "Authorization successful! You can close this window."
        elif 'error' in params:
            self.server.error = params['error'][0]
            self.server.error_description = params.get('error_description', ['Unknown error'])[0]
            success = False
            message = f"Authorization failed: {self.server.error_description}"
        else:
            success = False
            message = "Invalid callback response"
        
        # Send response to browser
        self.send_response(200 if success else 400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Anime Tracker - MAL Authorization</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: {'#4CAF50' if success else '#f44336'};
                    color: white;
                }}
                .container {{
                    text-align: center;
                    padding: 2em;
                    background: rgba(0,0,0,0.1);
                    border-radius: 10px;
                }}
                h1 {{ margin-bottom: 0.5em; }}
                p {{ font-size: 1.2em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{'Success!' if success else 'Failed'}</h1>
                <p>{message}</p>
                <p><small>This window will close automatically...</small></p>
            </div>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass


class MALOAuth2Client:
    """OAuth2 client for MyAnimeList API v2"""
    
    # OAuth2 endpoints
    AUTHORIZE_URL = "https://myanimelist.net/v1/oauth2/authorize"
    TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"
    API_BASE_URL = "https://api.myanimelist.net/v2"
    
    # Local callback server
    REDIRECT_URI = "http://localhost:8888/callback"
    CALLBACK_PORT = 8888
    
    # Required scopes
    SCOPES = "anime:read anime:write user:read"
    
    def __init__(self, client_id: str, token_storage_path: Path):
        """Initialize OAuth2 client
        
        Args:
            client_id: MAL application client ID
            token_storage_path: Path to store tokens (encrypted)
        """
        self.client_id = client_id
        self.token_storage_path = token_storage_path
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.code_verifier = None
        self.state = None
        
        # Load existing tokens if available
        self._load_tokens()
    
    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        # Use 32 bytes to get a 43-character string after base64 encoding
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
        """Generate authorization URL for user consent
        
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
    
    def _start_callback_server(self, timeout: int = 120) -> Optional[str]:
        """Start local HTTP server to receive callback
        
        Args:
            timeout: Timeout in seconds to wait for callback
            
        Returns:
            Authorization code if successful, None otherwise
        """
        # Create HTTP server
        server = HTTPServer(('localhost', self.CALLBACK_PORT), OAuth2CallbackHandler)
        server.auth_code = None
        server.state = None
        server.error = None
        server.error_description = None
        server.timeout = 1  # Check every second
        
        # Start server in a thread
        def serve():
            start_time = time.time()
            while time.time() - start_time < timeout:
                server.handle_request()
                if server.auth_code or server.error:
                    break
        
        thread = threading.Thread(target=serve)
        thread.daemon = True
        thread.start()
        
        # Wait for callback
        thread.join(timeout)
        
        # Validate state to prevent CSRF
        if server.auth_code and server.state == self.state:
            return server.auth_code
        elif server.error:
            raise Exception(f"Authorization failed: {server.error_description}")
        else:
            raise Exception("Authorization timeout or invalid state")
    
    def authorize(self) -> bool:
        """Perform OAuth2 authorization flow
        
        Returns:
            True if authorization successful
        """
        try:
            # Get authorization URL
            auth_url = self.get_authorization_url()
            logger.info(f"Opening browser for MAL authorization...")
            logger.debug(f"Auth URL: {auth_url}")
            
            # Open browser
            if not webbrowser.open(auth_url):
                logger.error("Failed to open browser")
                return False
            
            # Wait for callback
            logger.info(f"Waiting for authorization callback on port {self.CALLBACK_PORT}...")
            auth_code = self._start_callback_server()
            
            if not auth_code:
                logger.error("Failed to receive authorization code")
                return False
            
            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens...")
            return self._exchange_code_for_tokens(auth_code)
            
        except Exception as e:
            logger.error(f"Authorization failed: {e}", exc_info=True)
            return False
    
    def _exchange_code_for_tokens(self, auth_code: str) -> bool:
        """Exchange authorization code for access and refresh tokens
        
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
            
            logger.debug(f"Token exchange data: client_id={self.client_id}, code={auth_code[:10]}..., redirect_uri={self.REDIRECT_URI}")
            
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
                    
                    # Save tokens
                    self._save_tokens()
                    
                    logger.info("Successfully obtained access token")
                    return True
                else:
                    logger.error(f"Token exchange failed with status {response.status}")
                    return False
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"Token exchange HTTP error {e.code}: {error_body}")
            
            # Parse MAL error response
            try:
                import json
                error_data = json.loads(error_body)
                error_msg = error_data.get('error', 'Unknown')
                error_desc = error_data.get('error_description', error_data.get('message', 'No description'))
                logger.error(f"MAL Error: {error_msg} - {error_desc}")
                
                # Common error explanations
                if error_msg == 'invalid_request':
                    logger.error("This usually means the redirect_uri doesn't match or PKCE is incorrect")
                elif error_msg == 'invalid_grant':
                    logger.error("The authorization code may have expired or been used already")
            except:
                pass
            
            return False
        except Exception as e:
            logger.error(f"Token exchange failed: {e}", exc_info=True)
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token
        
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
                    
                    # Save tokens
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
        """Check if client is authenticated
        
        Returns:
            True if authenticated with valid token
        """
        if not self.access_token:
            return False
        
        # Check if token is expired
        if self.token_expiry and datetime.now() >= self.token_expiry:
            # Try to refresh
            if self.refresh_access_token():
                return True
            else:
                return False
        
        return True
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token, refreshing if needed
        
        Returns:
            Access token or None if not authenticated
        """
        if self.is_authenticated():
            return self.access_token
        return None
    
    def _save_tokens(self):
        """Save tokens to encrypted storage"""
        try:
            # Create token data
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None
            }
            
            # TODO: Encrypt before saving
            # For now, just save as JSON (INSECURE - needs encryption)
            self.token_storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.token_storage_path, 'w') as f:
                json.dump(token_data, f)
            
            logger.info("Tokens saved to storage")
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
    
    def _load_tokens(self):
        """Load tokens from encrypted storage"""
        try:
            if not self.token_storage_path.exists():
                return
            
            # TODO: Decrypt after loading
            # For now, just load as JSON (INSECURE - needs encryption)
            with open(self.token_storage_path, 'r') as f:
                token_data = json.load(f)
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            if token_data.get('token_expiry'):
                self.token_expiry = datetime.fromisoformat(token_data['token_expiry'])
            
            logger.info("Tokens loaded from storage")
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
    
    def logout(self):
        """Clear tokens and logout"""
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        
        # Delete token file
        if self.token_storage_path.exists():
            self.token_storage_path.unlink()
        
        logger.info("Logged out and tokens cleared")
    
    def make_api_request(self, endpoint: str, method: str = "GET", 
                        data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated API request to MAL
        
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