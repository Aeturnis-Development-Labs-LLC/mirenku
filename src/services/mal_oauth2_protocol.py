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
from utils.error_sanitizer import ErrorSanitizer, sanitize_error

logger = logging.getLogger(__name__)


class MALOAuth2ProtocolClient:
    """OAuth2 client for MyAnimeList using protocol handler"""
    
    # OAuth2 endpoints
    AUTHORIZE_URL = "https://myanimelist.net/v1/oauth2/authorize"
    TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"
    API_BASE_URL = "https://api.myanimelist.net/v2"
    
    # Protocol-based callback (MAL adds trailing slash)
    REDIRECT_URI = "mirenku://auth/"
    
    # Required scopes
    SCOPES = "anime:read anime:write user:read"
    
    def __init__(self, client_id: str, token_storage_path: Path, refresh_buffer_minutes: int = 5,
                 state_expiry_minutes: int = 5, max_auth_attempts: int = 3, rate_limit_window: int = 60,
                 pkce_verifier_length: int = 128):
        """
        Initialize OAuth2 client with protocol handler

        Args:
            client_id: MAL application client ID
            token_storage_path: Path to store tokens
            refresh_buffer_minutes: Minutes before expiry to refresh token (default 5)
            state_expiry_minutes: Minutes before state parameter expires (default 5)
            max_auth_attempts: Maximum auth attempts before rate limiting (default 3)
            rate_limit_window: Time window in seconds for rate limiting (default 60)
            pkce_verifier_length: Length of PKCE code verifier (default 128, max security)
        """
        self.client_id = client_id
        self.token_storage_path = token_storage_path
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.code_verifier = None
        self.state = None
        self.redirect_uri = self.REDIRECT_URI
        self.refresh_buffer_minutes = refresh_buffer_minutes
        self.state_expiry_minutes = state_expiry_minutes
        self.max_auth_attempts = max_auth_attempts
        self.rate_limit_window = rate_limit_window
        self.pkce_verifier_length = min(max(43, pkce_verifier_length), 128)  # RFC 7636: 43-128 chars

        # Initialize token storage with encryption
        self.token_storage = TokenStorage(app_name="Mirenku")

        # OAuth callback event
        self.auth_received = threading.Event()
        self.auth_code = None
        self.auth_error = None

        # Refresh lock to prevent concurrent refreshes
        self._refresh_lock = threading.Lock()
        self._refresh_in_progress = False

        # Rate limiting tracking (local, following The Mirenku Way)
        self._auth_attempts = []  # List of attempt timestamps
        self._refresh_attempts = []  # List of refresh attempt timestamps
        self._failed_auth_count = 0  # Count of consecutive failed auths
        self._lockout_until = None  # Lockout expiry time
        self._rate_limit_lock = threading.Lock()  # Thread safety for rate limiting

        # Error sanitizer for security
        self.error_sanitizer = ErrorSanitizer()

        # Load existing tokens if available
        self._load_tokens()
    
    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge with maximum entropy
        Following The Mirenku Way: Maximum security, simple implementation

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Calculate bytes needed for desired verifier length
        # Base64 encoding produces 4 chars for every 3 bytes
        # So for 128 chars, we need 96 bytes (128 * 3 / 4 = 96)
        if self.pkce_verifier_length == 128:
            bytes_needed = 96
        elif self.pkce_verifier_length >= 86:
            bytes_needed = 64  # Produces 86 chars after base64
        elif self.pkce_verifier_length >= 43:
            bytes_needed = 32  # Produces 43 chars after base64
        else:
            bytes_needed = 32  # Minimum

        # Generate high-entropy random bytes using cryptographically secure random
        random_bytes = secrets.token_bytes(bytes_needed)

        # Convert to URL-safe base64 (using - and _ instead of + and /)
        code_verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')

        # Ensure we have exactly the desired length
        if len(code_verifier) > self.pkce_verifier_length:
            code_verifier = code_verifier[:self.pkce_verifier_length]
        elif len(code_verifier) < self.pkce_verifier_length:
            # Add more random characters if needed (shouldn't happen with correct calculation)
            extra_bytes = secrets.token_bytes((self.pkce_verifier_length - len(code_verifier)) * 3 // 4 + 1)
            extra_chars = base64.urlsafe_b64encode(extra_bytes).decode('utf-8').rstrip('=')
            code_verifier += extra_chars[:self.pkce_verifier_length - len(code_verifier)]

        # Generate code challenge using SHA256 (S256 method)
        challenge_bytes = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('ascii').rstrip('=')

        logger.debug(f"Generated PKCE pair: verifier length={len(code_verifier)}, challenge length={len(code_challenge)}")

        return code_verifier, code_challenge
    
    def _generate_state(self) -> str:
        """
        Generate state parameter with timestamp for CSRF protection
        Following The Mirenku Way: Simple, secure, local

        Returns:
            Base64-encoded JSON containing timestamp and nonce
        """
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'nonce': secrets.token_urlsafe(32)
        }

        # Encode as base64 for URL safety
        state_json = json.dumps(state_data)
        state = base64.urlsafe_b64encode(state_json.encode()).decode().rstrip('=')

        return state

    def _decode_state(self, state: str) -> Optional[Dict]:
        """
        Decode state parameter to extract timestamp and nonce

        Args:
            state: Base64-encoded state parameter

        Returns:
            Decoded state data or None if invalid
        """
        try:
            # Add padding if needed
            padding = 4 - len(state) % 4
            if padding != 4:
                state += '=' * padding

            # Decode from base64
            state_json = base64.urlsafe_b64decode(state).decode()
            state_data = json.loads(state_json)

            return state_data
        except Exception as e:
            logger.debug(f"Failed to decode state: {e}")
            return None

    def _validate_state_timestamp(self, state: str) -> bool:
        """
        Validate that state parameter hasn't expired

        Args:
            state: State parameter to validate

        Returns:
            True if state is valid and not expired
        """
        if not state:
            return False

        decoded = self._decode_state(state)
        if not decoded or 'timestamp' not in decoded:
            return False

        try:
            # Parse timestamp
            timestamp = datetime.fromisoformat(decoded['timestamp'])

            # Check if expired
            time_elapsed = datetime.now() - timestamp
            expiry_threshold = timedelta(minutes=self.state_expiry_minutes)

            if time_elapsed > expiry_threshold:
                logger.warning(f"State parameter expired ({time_elapsed.total_seconds():.0f} seconds old)")
                return False

            return True

        except Exception as e:
            logger.debug(f"Failed to validate state timestamp: {e}")
            return False
    
    def get_authorization_url(self) -> str:
        """
        Generate authorization URL for user consent
        
        Returns:
            Authorization URL to open in browser
        """
        # Generate PKCE pair and state
        self.code_verifier, code_challenge = self._generate_pkce_pair()
        self.state = self._generate_state()
        
        # Save PKCE verifier temporarily for callback
        self._save_temp_auth_state()
        
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
            # Sanitize error before logging
            sanitized_error = self.error_sanitizer.sanitize(error)
            logger.error(f"OAuth error: {sanitized_error}")
            self.auth_error = error
            self.auth_received.set()
            return
        
        # Load saved auth state if not present
        if not self.code_verifier or not self.state:
            logger.info("Loading saved PKCE verifier and state for callback validation")
            self._load_temp_auth_state()
        
        # Validate state timestamp first
        if not self._validate_state_timestamp(state):
            logger.error("State parameter expired")
            self.auth_error = "state_expired"
            self.auth_received.set()
            return

        # Then validate state matches
        if state != self.state:
            logger.error("State mismatch - possible CSRF attempt")
            self.auth_error = "state_mismatch"
            self.auth_received.set()
            return
        
        if not code:
            logger.error("No authorization code received")
            self.auth_error = "missing_code"
            self.auth_received.set()
            return
        
        # Store code and immediately exchange for tokens
        self.auth_code = code
        logger.info("Exchanging authorization code for tokens...")
        
        # Perform token exchange immediately
        success = self._exchange_code_for_tokens(code)
        if not success:
            self.auth_error = "token_exchange_failed"
        
        # Signal completion
        self.auth_received.set()
    
    def track_auth_attempt(self) -> None:
        """
        Track an authorization attempt for rate limiting
        Following The Mirenku Way: Simple local tracking
        """
        with self._rate_limit_lock:
            current_time = time.time()
            self._auth_attempts.append(current_time)
            # Clean old attempts outside the window
            cutoff_time = current_time - self.rate_limit_window
            self._auth_attempts = [t for t in self._auth_attempts if t > cutoff_time]

    def track_failed_auth(self) -> None:
        """
        Track a failed authorization for lockout mechanism
        """
        with self._rate_limit_lock:
            self._failed_auth_count += 1
            if self._failed_auth_count >= 5:
                # Lock out for 5 minutes after 5 failed attempts
                self._lockout_until = time.time() + 300
                logger.warning("Account locked out due to multiple failed auth attempts")

    def reset_rate_limit(self, operation: str) -> None:
        """
        Reset rate limit counters for an operation after success

        Args:
            operation: 'authorize' or 'refresh'
        """
        with self._rate_limit_lock:
            if operation == 'authorize':
                self._auth_attempts.clear()
                self._failed_auth_count = 0
                self._lockout_until = None
            elif operation == 'refresh':
                self._refresh_attempts.clear()

    def is_rate_limited(self, operation: str) -> bool:
        """
        Check if an operation is currently rate limited

        Args:
            operation: 'authorize' or 'refresh'

        Returns:
            True if rate limited
        """
        with self._rate_limit_lock:
            current_time = time.time()

            if operation == 'authorize':
                # Clean old attempts
                cutoff_time = current_time - self.rate_limit_window
                self._auth_attempts = [t for t in self._auth_attempts if t > cutoff_time]

                # Check if we've hit the limit
                attempt_count = len(self._auth_attempts)
                if attempt_count >= self.max_auth_attempts:
                    logger.warning(f"Rate limit active for {operation}: {attempt_count} attempts in last {self.rate_limit_window} seconds")
                    return True

            elif operation == 'refresh':
                # Clean old attempts
                cutoff_time = current_time - self.rate_limit_window
                self._refresh_attempts = [t for t in self._refresh_attempts if t > cutoff_time]

                # Check if we've hit the limit (5 refresh attempts)
                attempt_count = len(self._refresh_attempts)
                if attempt_count >= 5:
                    logger.warning(f"Rate limit active for {operation}: {attempt_count} attempts in last {self.rate_limit_window} seconds")
                    return True

            return False

    def is_locked_out(self) -> bool:
        """
        Check if account is locked out due to failed attempts

        Returns:
            True if currently locked out
        """
        with self._rate_limit_lock:
            if self._lockout_until is None:
                return False

            if time.time() < self._lockout_until:
                remaining = int(self._lockout_until - time.time())
                logger.warning(f"Account locked out for {remaining} more seconds")
                return True

            # Lockout expired, reset
            self._lockout_until = None
            self._failed_auth_count = 0
            return False

    def get_backoff_time(self) -> int:
        """
        Calculate exponential backoff time based on attempt count

        Returns:
            Backoff time in seconds
        """
        with self._rate_limit_lock:
            # Count recent attempts
            current_time = time.time()
            cutoff_time = current_time - self.rate_limit_window
            recent_attempts = [t for t in self._auth_attempts if t > cutoff_time]

            # Exponential backoff: 2^(n-1) seconds
            attempt_count = len(recent_attempts)
            if attempt_count == 0:
                return 0

            backoff = min(2 ** (attempt_count - 1), 60)  # Cap at 60 seconds
            return backoff

    def authorize(self, timeout: int = 120) -> bool:
        """
        Perform OAuth2 authorization flow with protocol handler

        Args:
            timeout: Timeout in seconds to wait for callback

        Returns:
            True if authorization successful
        """
        # Check rate limiting first
        if self.is_locked_out():
            logger.error("Cannot authorize: Account is locked out due to failed attempts")
            return False

        if self.is_rate_limited('authorize'):
            logger.warning("Rate limit exceeded for authorization. Please wait before trying again.")
            return False

        # Track this attempt
        self.track_auth_attempt()
        try:
            # Setup protocol handler
            protocol_handler = ProtocolHandler()
            protocol_handler.register_oauth_handler(self._handle_oauth_callback)
            
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
            logger.info(f"Waiting for up to {timeout} seconds for callback...")
            if not self.auth_received.wait(timeout):
                logger.error(f"Authorization timeout after {timeout} seconds")
                logger.error("No callback received from browser")
                return False
            
            # Check for errors
            if self.auth_error:
                logger.error(f"Authorization failed: {self.auth_error}")
                return False
            
            if not self.auth_code:
                logger.error("No authorization code received")
                return False
            
            # Token exchange already happened in callback handler
            # Just check if we have valid tokens
            if self.access_token and self.refresh_token:
                logger.info("Authorization and token exchange completed successfully")
                # Reset rate limiting on success
                self.reset_rate_limit('authorize')
                return True
            else:
                logger.error("Token exchange failed during callback processing")
                # Track failed auth for lockout
                self.track_failed_auth()
                return False
            
        except Exception as e:
            # Sanitize exception message
            sanitized_error = self.error_sanitizer.sanitize(str(e))
            logger.error(f"Authorization failed: {sanitized_error}")
            # Track failed auth for lockout
            self.track_failed_auth()
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
            # Load saved PKCE verifier if not present
            if not self.code_verifier:
                logger.info("Loading saved PKCE verifier for token exchange")
                self._load_temp_auth_state()
            
            if not self.code_verifier:
                logger.error("No PKCE code verifier available for token exchange")
                return False
            
            # Log important details for debugging
            logger.info("Token exchange attempt:")
            logger.info(f"  - Auth code (first 10 chars): {auth_code[:10]}...")
            logger.info(f"  - Code verifier (first 10 chars): {self.code_verifier[:10]}...")
            logger.info(f"  - Client ID: {self.client_id[:8]}..." if len(self.client_id) > 8 else f"  - Client ID: {self.client_id}")
            logger.info(f"  - Redirect URI: {self.REDIRECT_URI}")
            
            # Prepare token request
            data = {
                'client_id': self.client_id,
                'grant_type': 'authorization_code',
                'code': auth_code,
                'redirect_uri': self.REDIRECT_URI,
                'code_verifier': self.code_verifier
            }
            
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
                    
                    # Clear temp auth state after successful exchange
                    self._clear_temp_auth_state()
                    
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
                # Sanitize error description before logging
                sanitized_desc = self.error_sanitizer.sanitize(error_desc)
                logger.error(f"MAL Error: {error_msg} - {sanitized_desc}")
                
                # Provide helpful error message for common issues
                if error_msg == 'invalid_grant':
                    logger.error("Authorization code may have expired or been used already.")
                    logger.error("Please try connecting to MAL again.")
            except:
                pass
            
            return False
        except Exception as e:
            # Sanitize exception message
            sanitized_error = self.error_sanitizer.sanitize(str(e))
            logger.error(f"Token exchange failed: {sanitized_error}")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token with concurrency protection

        Returns:
            True if successful
        """
        # Check rate limiting
        if self.is_rate_limited('refresh'):
            logger.warning("Rate limit exceeded for token refresh. Please wait before trying again.")
            return False

        # Track refresh attempt
        with self._rate_limit_lock:
            self._refresh_attempts.append(time.time())

        # Prevent concurrent refresh attempts
        with self._refresh_lock:
            # If another thread is already refreshing, wait and return result
            if self._refresh_in_progress:
                logger.info("Token refresh already in progress, waiting...")
                # Wait a bit for the other refresh to complete
                time.sleep(0.5)
                # Check if token was successfully refreshed
                return not self._is_token_expired()

            self._refresh_in_progress = True

        try:
            result = self._do_refresh_access_token()
            if result:
                # Reset rate limit on success
                self.reset_rate_limit('refresh')
            return result
        finally:
            with self._refresh_lock:
                self._refresh_in_progress = False

    def _do_refresh_access_token(self) -> bool:
        """
        Internal method to perform actual token refresh

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
                    logger.info(f"New token expires at: {self.token_expiry}")
                    return True
                else:
                    logger.error(f"Token refresh failed with status {response.status}")
                    return False

        except Exception as e:
            # Sanitize exception message
            sanitized_error = self.error_sanitizer.sanitize(str(e))
            logger.error(f"Token refresh failed: {sanitized_error}")
            return False

    def refresh_access_token_with_retry(self, max_retries: int = 3) -> bool:
        """
        Refresh access token with network retry logic

        Args:
            max_retries: Maximum number of retry attempts

        Returns:
            True if successful
        """
        for attempt in range(max_retries):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt} of {max_retries}")
                time.sleep(2 ** attempt)  # Exponential backoff

            try:
                if self.refresh_access_token():
                    return True
            except urllib.error.URLError as e:
                logger.warning(f"Network error during refresh: {e}")
                if attempt == max_retries - 1:
                    logger.error("Max retries reached, giving up")
                    return False

        return False
    
    def is_authenticated(self) -> bool:
        """
        Check if client is authenticated

        Returns:
            True if authenticated with valid token
        """
        if not self.access_token:
            return False

        # Check if token needs refresh (expired or within buffer)
        if self.needs_token_refresh():
            logger.info("Token expiring soon (within 5-minute buffer), refreshing proactively")
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

    def needs_token_refresh(self) -> bool:
        """
        Check if token needs refresh (expired or within buffer window)

        Returns:
            True if token should be refreshed
        """
        if not self.token_expiry:
            # No expiry means token doesn't expire
            return False

        # Check if expired
        if self._is_token_expired():
            return True

        # Check if within refresh buffer window
        time_until_expiry = self.token_expiry - datetime.now()
        buffer_threshold = timedelta(minutes=self.refresh_buffer_minutes)

        return time_until_expiry <= buffer_threshold

    def check_token_expiry_status(self) -> None:
        """
        Check token expiry status and log appropriate warnings
        """
        if not self.token_expiry:
            return

        time_until_expiry = self.token_expiry - datetime.now()
        minutes_until_expiry = time_until_expiry.total_seconds() / 60

        if minutes_until_expiry <= 1:
            logger.critical(f"Token expires in {minutes_until_expiry:.1f} minutes!")
        elif minutes_until_expiry <= 3:
            logger.warning(f"Token expires in {minutes_until_expiry:.1f} minutes")
        elif minutes_until_expiry <= 5:
            logger.info(f"Token expires in {minutes_until_expiry:.1f} minutes (within refresh buffer)")
    
    def get_access_token(self) -> Optional[str]:
        """
        Get current access token, refreshing if needed

        Returns:
            Access token or None if not authenticated
        """
        if not self.access_token:
            return None

        # Check if we need to refresh proactively
        if self.needs_token_refresh():
            logger.info("Token needs refresh, refreshing proactively")
            if not self.refresh_access_token():
                return None

        return self.access_token
    
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
            stored_client_id = token_data.get('client_id')
            if stored_client_id and stored_client_id != self.client_id:
                logger.warning(f"Client ID mismatch in stored tokens (stored: {stored_client_id[:8]}..., current: {self.client_id[:8]}...). Clearing old tokens.")
                # Clear invalid tokens
                self.token_storage.delete_tokens()
                return
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            if token_data.get('token_expiry'):
                try:
                    self.token_expiry = datetime.fromisoformat(token_data['token_expiry'])
                except (ValueError, TypeError):
                    logger.warning("Invalid token expiry format, ignoring")
                    self.token_expiry = None
            
            if self.access_token and self.refresh_token:
                logger.info("Tokens loaded from secure storage")
            
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            # Clear potentially corrupted tokens
            try:
                self.token_storage.delete_tokens()
            except:
                pass
    
    def _sanitize_error_response(self, error_response: Dict) -> Dict:
        """
        Sanitize an OAuth error response dictionary

        Args:
            error_response: Error response to sanitize

        Returns:
            Sanitized error response
        """
        return self.error_sanitizer.sanitize_dict(error_response)

    def _sanitize_mal_error(self, error_msg: str) -> str:
        """
        Sanitize MAL-specific error messages

        Args:
            error_msg: Error message to sanitize

        Returns:
            Sanitized error message
        """
        return self.error_sanitizer.sanitize(error_msg)

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
    
    def _save_temp_auth_state(self):
        """Save temporary auth state (PKCE verifier and state) for callback"""
        try:
            temp_data = {
                'code_verifier': self.code_verifier,
                'state': self.state,
                'client_id': self.client_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save to a temporary file in the config directory
            temp_file = self.token_storage_path.parent / '.mal_auth_temp.json'
            with open(temp_file, 'w') as f:
                json.dump(temp_data, f)
            
            logger.debug(f"Saved temp auth state to {temp_file}")
            
        except Exception as e:
            logger.error(f"Failed to save temp auth state: {e}")
    
    def _load_temp_auth_state(self):
        """Load temporary auth state (PKCE verifier and state) for callback"""
        try:
            temp_file = self.token_storage_path.parent / '.mal_auth_temp.json'
            
            if not temp_file.exists():
                logger.warning("No temp auth state file found")
                return
            
            with open(temp_file, 'r') as f:
                temp_data = json.load(f)
            
            # Check if data is recent (within 10 minutes)
            timestamp = datetime.fromisoformat(temp_data.get('timestamp', ''))
            if datetime.now() - timestamp > timedelta(minutes=10):
                logger.warning("Temp auth state is too old, ignoring")
                temp_file.unlink()  # Delete old file
                return
            
            # Verify client ID matches
            if temp_data.get('client_id') != self.client_id:
                logger.warning("Client ID mismatch in temp auth state")
                return
            
            # Load the state
            self.code_verifier = temp_data.get('code_verifier')
            self.state = temp_data.get('state')
            
            logger.info(f"Loaded temp auth state (verifier: {bool(self.code_verifier)}, state: {bool(self.state)})")
            
            # Delete temp file after loading
            temp_file.unlink()
            
        except Exception as e:
            logger.error(f"Failed to load temp auth state: {e}")
    
    def _clear_temp_auth_state(self):
        """Clear temporary auth state file and memory"""
        try:
            # Clear from memory (prevents replay attacks)
            self.state = None
            self.code_verifier = None

            # Clear from file
            temp_file = self.token_storage_path.parent / '.mal_auth_temp.json'
            if temp_file.exists():
                temp_file.unlink()
                logger.debug("Cleared temp auth state")
        except Exception as e:
            logger.error(f"Failed to clear temp auth state: {e}")


def handle_protocol_url(url: str):
    """
    Global handler for protocol URLs
    Should be called from main application when protocol URL is received
    
    Args:
        url: Protocol URL (mirenku://...)
    """
    # Handle the URL directly - we're already in the primary instance
    # when this is called from main.py
    protocol_handler = ProtocolHandler()
    protocol_handler.handle_url(url)