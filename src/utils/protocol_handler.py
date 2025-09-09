"""
Protocol Handler for mirenku:// URLs
Parses and routes protocol URLs to appropriate handlers
"""

import logging
import html
from typing import Optional, Dict, Any, Callable, List
from urllib.parse import urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)

# Maximum URL length for security
MAX_URL_LENGTH = 2048


class ProtocolHandler:
    """Handles mirenku:// protocol URLs"""
    
    def __init__(self, protocol_scheme: str = "mirenku"):
        """
        Initialize Protocol Handler
        
        Args:
            protocol_scheme: Protocol scheme to handle (default: mirenku)
        """
        self.protocol_scheme = protocol_scheme
        self.handlers = {}
        self.default_handler = None
        self.oauth_callback = None
        self.expected_state = None
        
        # Pre-register common handlers
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self):
        """Register built-in handlers"""
        # OAuth handler is registered separately via register_oauth_handler
        pass
    
    def parse_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a protocol URL
        
        Args:
            url: Protocol URL to parse
            
        Returns:
            Parsed URL data or None if invalid
        """
        if not url:
            return None
        
        # Check URL length
        if len(url) > MAX_URL_LENGTH:
            logger.warning(f"URL exceeds maximum length: {len(url)}")
            url = url[:MAX_URL_LENGTH]
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme != self.protocol_scheme:
                logger.warning(f"Invalid scheme: {parsed.scheme}")
                return None
            
            # Extract action from netloc or path
            action = parsed.netloc or parsed.path.lstrip('/')
            if not action:
                logger.warning("No action specified in URL")
                return None
            
            # Parse query parameters
            params = {}
            if parsed.query:
                query_params = parse_qs(parsed.query)
                # Convert single-value lists to strings
                for key, values in query_params.items():
                    if len(values) == 1:
                        params[key] = unquote(values[0])
                    else:
                        params[key] = [unquote(v) for v in values]
            
            # Sanitize parameters
            params = self._sanitize_params(params)
            
            return {
                'scheme': parsed.scheme,
                'action': action,
                'params': params,
                'raw_url': url
            }
            
        except Exception as e:
            logger.error(f"Error parsing URL: {e}")
            return None
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters for security
        
        Args:
            params: Parameters to sanitize
            
        Returns:
            Sanitized parameters
        """
        sanitized = {}
        
        for key, value in params.items():
            # Sanitize key
            key = html.escape(key)
            
            # Sanitize value(s)
            if isinstance(value, list):
                sanitized[key] = [self._sanitize_value(v) for v in value]
            else:
                sanitized[key] = self._sanitize_value(value)
        
        return sanitized
    
    def _sanitize_value(self, value: str) -> str:
        """
        Sanitize a single value
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        if not isinstance(value, str):
            return value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Escape HTML
        value = html.escape(value)
        
        # Remove path traversal attempts
        value = value.replace('../', '').replace('..\\', '')
        
        return value
    
    def register_handler(self, action: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Register a handler for an action
        
        Args:
            action: Action name
            handler: Callback function
        """
        self.handlers[action] = handler
        logger.info(f"Registered handler for action: {action}")
    
    def set_default_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """
        Set default handler for unknown actions
        
        Args:
            handler: Default callback function
        """
        self.default_handler = handler
    
    def register_oauth_handler(self, callback: Callable):
        """
        Register OAuth callback handler
        
        Args:
            callback: OAuth callback function
        """
        self.oauth_callback = callback
        
        # Register auth action handler
        def auth_handler(params):
            code = params.get('code')
            state = params.get('state')
            error = params.get('error')
            error_description = params.get('error_description', 'Unknown error')
            
            if self.oauth_callback:
                self.oauth_callback(
                    code=code,
                    state=state,
                    error=error or (None if code else 'missing_code')
                )
        
        self.register_handler('auth', auth_handler)
    
    def handle_url(self, url: str, forward_to_primary: bool = False) -> bool:
        """
        Handle a protocol URL
        
        Args:
            url: Protocol URL to handle
            forward_to_primary: Forward to primary instance if not primary
            
        Returns:
            True if handled successfully
        """
        # Parse URL
        parsed = self.parse_url(url)
        if not parsed:
            logger.error(f"Failed to parse URL: {url}")
            return False
        
        action = parsed['action']
        params = parsed['params']
        
        # Check if we should forward to primary instance
        if forward_to_primary:
            try:
                from utils.single_instance import SingleInstanceManager
                instance_mgr = SingleInstanceManager()
                if not instance_mgr.is_primary:
                    # Forward to primary
                    return instance_mgr.send_message_to_primary({
                        'action': 'protocol_url',
                        'url': url
                    })
            except ImportError:
                pass
        
        # Find handler
        handler = self.handlers.get(action)
        
        if not handler and self.default_handler:
            handler = self.default_handler
        
        if not handler:
            logger.warning(f"No handler for action: {action}")
            return False
        
        # Execute handler
        try:
            handler(params)
            logger.info(f"Successfully handled action: {action}")
            return True
            
        except Exception as e:
            logger.error(f"Error in handler for {action}: {e}")
            return False
    
    def set_expected_state(self, state: str):
        """
        Set expected OAuth state for validation
        
        Args:
            state: Expected state value
        """
        self.expected_state = state
    
    def validate_oauth_response(self, params: Dict[str, Any]) -> bool:
        """
        Validate OAuth response parameters
        
        Args:
            params: OAuth response parameters
            
        Returns:
            True if valid
        """
        # Check for error
        if 'error' in params:
            logger.error(f"OAuth error: {params.get('error')}")
            return False
        
        # Check for code
        if 'code' not in params:
            logger.error("OAuth response missing code")
            return False
        
        # Validate state if expected
        if self.expected_state:
            state = params.get('state')
            if state != self.expected_state:
                logger.error(f"State mismatch: expected {self.expected_state}, got {state}")
                return False
        
        return True
    
    def is_safe_path(self, path: str) -> bool:
        """
        Check if a path is safe (no traversal)
        
        Args:
            path: Path to check
            
        Returns:
            True if safe
        """
        # Check for path traversal
        if '../' in path or '..\\' in path:
            return False
        
        # Check for absolute paths
        if path.startswith('/') or path.startswith('\\'):
            return False
        
        # Check for drive letters (Windows)
        if len(path) > 1 and path[1] == ':':
            return False
        
        return True
    
    def get_url_from_argv(self, argv: List[str]) -> Optional[str]:
        """
        Extract protocol URL from command line arguments
        
        Args:
            argv: Command line arguments
            
        Returns:
            Protocol URL if found
        """
        for arg in argv[1:]:  # Skip program name
            if arg.startswith(f"{self.protocol_scheme}://"):
                return arg
        
        return None
    
    @staticmethod
    def register_with_system(exe_path: str) -> bool:
        """
        Register protocol with system (convenience method)
        
        Args:
            exe_path: Path to executable
            
        Returns:
            True if successful
        """
        try:
            from utils.protocol_manager import ProtocolManager
            manager = ProtocolManager()
            return manager.register_protocol(exe_path)
        except ImportError:
            logger.error("ProtocolManager not available")
            return False