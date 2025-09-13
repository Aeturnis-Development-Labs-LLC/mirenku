"""
Error message sanitizer for Mirenku
Ensures sensitive data is never exposed in logs or error messages
Following The Mirenku Way: Clear, honest errors without exposing secrets
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache


class ErrorSanitizer:
    """Sanitizes error messages to remove sensitive information"""

    def __init__(self):
        """Initialize the error sanitizer with default patterns"""
        # Patterns for sensitive data (pattern, replacement)
        self.patterns: List[Tuple[re.Pattern, str]] = [
            # Bearer tokens (JWT or other)
            (re.compile(r'Bearer\s+[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*\.?[A-Za-z0-9\-_=]*'),
             'Bearer [REDACTED]'),

            # Generic tokens (base64-like strings > 20 chars)
            (re.compile(r'\b(token|access_token|refresh_token)["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-_=]{20,})["\']?', re.IGNORECASE),
             r'\1=[REDACTED]'),

            # Authorization codes
            (re.compile(r'\b(code|authorization_code)["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-_]{10,})["\']?', re.IGNORECASE),
             r'\1=[REDACTED]'),

            # Authorization code in sentence format
            (re.compile(r'authorization code:\s*([A-Za-z0-9\-_]{10,})', re.IGNORECASE),
             r'authorization code: [CODE REDACTED]'),

            # Client secrets
            (re.compile(r'\b(client_secret|secret)["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-_]+)["\']?', re.IGNORECASE),
             r'\1=[REDACTED]'),

            # Client IDs (partial masking) - must come before shorter token patterns
            (re.compile(r'\b(client_id)["\']?\s*[:=]\s*["\']?([A-Za-z0-9\-_]{4})([A-Za-z0-9\-_]{4,})["\']?', re.IGNORECASE),
             r'\1=\2...***'),

            # URLs with query parameters containing secrets
            (re.compile(r'(client_secret|access_token|refresh_token|code)=([^&\s]+)'),
             r'\1=[REDACTED]'),

            # File paths with usernames (Windows)
            (re.compile(r'C:\\Users\\([^\\]+)\\'),
             r'C:\\Users\\[USER]\\'),

            # File paths with usernames (Unix-like)
            (re.compile(r'/home/([^/]+)/'),
             r'/home/[USER]/'),

            # MAL-specific tokens
            (re.compile(r'mal_token_[A-Za-z0-9]+'),
             'mal_token_[REDACTED]'),

            # Refresh tokens specifically
            (re.compile(r'refresh_token_[A-Za-z0-9]+'),
             'refresh_token_[REDACTED]'),

            # Base64 encoded JWT tokens
            (re.compile(r'eyJ[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*\.?[A-Za-z0-9\-_=]*'),
             '[TOKEN REDACTED]'),

            # JSON tokens specifically
            (re.compile(r'"(access_token|refresh_token)"\s*:\s*"([^"]+)"', re.IGNORECASE),
             r'"\1": "[REDACTED]"'),

            # Quoted tokens in error messages (including refresh_token patterns)
            (re.compile(r"'(refresh_[A-Za-z0-9\-_]+)'", re.IGNORECASE),
             r"'[REDACTED]'"),
            (re.compile(r"'([A-Za-z0-9\-_]{10,})'", re.IGNORECASE),
             r"'[REDACTED]'"),

            # Generic long alphanumeric strings that might be tokens (>40 chars to avoid false positives)
            (re.compile(r'\b[A-Za-z0-9]{40,}\b'),
             '[POSSIBLE TOKEN REDACTED]'),
        ]

        # Patterns to preserve (these override sanitization)
        self.preserve_patterns = [
            re.compile(r'HTTP\s+\d{3}'),  # HTTP status codes
            re.compile(r'\d+\s+seconds?'),  # Time durations
            re.compile(r'expires_in["\']?\s*[:=]\s*\d+'),  # Token expiry times
        ]

    def sanitize(self, message: str) -> str:
        """
        Sanitize a message by removing sensitive information

        Args:
            message: The message to sanitize

        Returns:
            Sanitized message
        """
        if not message:
            return message

        sanitized = message

        # Apply sanitization patterns
        for pattern, replacement in self.patterns:
            sanitized = pattern.sub(replacement, sanitized)

        return sanitized

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a dictionary by removing sensitive values

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        if not data:
            return data

        sanitized = {}
        sensitive_keys = {
            'access_token', 'refresh_token', 'token',
            'client_secret', 'secret', 'password',
            'authorization', 'api_key', 'private_key'
        }

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                # Sanitize string values that might contain secrets
                if len(value) > 10:  # Only sanitize non-trivial strings
                    sanitized[key] = self.sanitize(value)
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = self.sanitize_dict(value)
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_exception(self, exception: Exception) -> Exception:
        """
        Create a sanitized version of an exception

        Args:
            exception: The exception to sanitize

        Returns:
            New exception with sanitized message
        """
        sanitized_msg = self.sanitize(str(exception))
        return type(exception)(sanitized_msg)

    def add_pattern(self, pattern: str, replacement: str):
        """
        Add a custom sanitization pattern

        Args:
            pattern: Regex pattern to match
            replacement: Replacement string
        """
        self.patterns.append((re.compile(pattern), replacement))

    def create_sanitized_handler(self) -> logging.Handler:
        """
        Create a logging handler that sanitizes messages

        Returns:
            Logging handler with sanitization
        """
        return SanitizedLogHandler(self)

    @lru_cache(maxsize=128)
    def is_sensitive(self, text: str) -> bool:
        """
        Quick check if text might contain sensitive data

        Args:
            text: Text to check

        Returns:
            True if text might contain sensitive data
        """
        # Quick checks for common sensitive patterns
        sensitive_indicators = [
            'token', 'secret', 'password', 'Bearer',
            'client_id', 'client_secret', 'refresh_token',
            'access_token', 'authorization', 'api_key'
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in sensitive_indicators)


class SanitizedLogHandler(logging.StreamHandler):
    """Logging handler that sanitizes log messages"""

    def __init__(self, sanitizer: ErrorSanitizer, stream=None):
        """
        Initialize the sanitized log handler

        Args:
            sanitizer: ErrorSanitizer instance to use
            stream: Stream to write to (default: sys.stderr)
        """
        super().__init__(stream)
        self.sanitizer = sanitizer

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record after sanitizing it

        Args:
            record: Log record to emit
        """
        # Sanitize the message
        original_msg = record.getMessage()
        if self.sanitizer.is_sensitive(original_msg):
            record.msg = self.sanitizer.sanitize(original_msg)
            record.args = ()  # Clear args to prevent re-formatting

        # Also sanitize any exception info
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_value:
                sanitized_exc = self.sanitizer.sanitize_exception(exc_value)
                record.exc_info = (exc_type, sanitized_exc, exc_tb)

        # Call the parent handler to actually emit the record
        super().emit(record)


# Global sanitizer instance
_global_sanitizer = ErrorSanitizer()


def sanitize_error(message: str) -> str:
    """
    Convenience function to sanitize an error message

    Args:
        message: Message to sanitize

    Returns:
        Sanitized message
    """
    return _global_sanitizer.sanitize(message)


def setup_sanitized_logging(logger_name: Optional[str] = None):
    """
    Set up sanitized logging for a logger

    Args:
        logger_name: Name of logger to configure (None for root logger)
    """
    logger = logging.getLogger(logger_name)

    # Remove existing handlers
    logger.handlers.clear()

    # Add sanitized handler
    handler = _global_sanitizer.create_sanitized_handler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

    return logger