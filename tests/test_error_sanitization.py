"""
Test suite for error message sanitization
Ensures sensitive data is never exposed in logs or error messages
Following The Mirenku Way: Clear, honest errors without exposing secrets
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestErrorSanitization:
    """Test error message sanitization functionality"""

    @pytest.fixture
    def sanitizer(self):
        """Create error sanitizer instance"""
        from utils.error_sanitizer import ErrorSanitizer
        return ErrorSanitizer()

    def test_sanitize_token_in_error(self, sanitizer):
        """Test that tokens are sanitized in error messages"""
        error_msg = "Failed to authenticate with token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"
        sanitized = sanitizer.sanitize(error_msg)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token" not in sanitized
        assert "Bearer [REDACTED]" in sanitized or "[TOKEN REDACTED]" in sanitized

    def test_sanitize_refresh_token(self, sanitizer):
        """Test that refresh tokens are sanitized"""
        error_msg = "Refresh failed with token: refresh_token_abc123xyz789"
        sanitized = sanitizer.sanitize(error_msg)

        assert "refresh_token_abc123xyz789" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_client_id(self, sanitizer):
        """Test that client IDs are partially masked"""
        error_msg = "Invalid client_id: test_client_id_12345"
        sanitized = sanitizer.sanitize(error_msg)

        # Should show partial client ID for debugging but not full
        assert "test_client_id_12345" not in sanitized
        assert "test...***" in sanitized  # Shows first 4 chars then mask

    def test_sanitize_authorization_code(self, sanitizer):
        """Test that auth codes are sanitized"""
        error_msg = "Invalid authorization code: def50200a1b2c3d4e5f6789"
        sanitized = sanitizer.sanitize(error_msg)

        assert "def50200a1b2c3d4e5f6789" not in sanitized
        assert "[REDACTED]" in sanitized  # Code gets fully redacted

    def test_sanitize_urls_with_secrets(self, sanitizer):
        """Test that URLs with embedded secrets are sanitized"""
        error_msg = "Failed to connect to https://api.example.com/auth?client_secret=secret123&code=abc456"
        sanitized = sanitizer.sanitize(error_msg)

        assert "secret123" not in sanitized
        assert "abc456" not in sanitized
        assert "client_secret=[REDACTED]" in sanitized
        assert "code=[REDACTED]" in sanitized

    def test_preserve_non_sensitive_info(self, sanitizer):
        """Test that non-sensitive information is preserved"""
        error_msg = "Connection timeout after 30 seconds to myanimelist.net"
        sanitized = sanitizer.sanitize(error_msg)

        # Should preserve useful debugging info
        assert "30 seconds" in sanitized
        assert "myanimelist.net" in sanitized

    def test_sanitize_file_paths(self, sanitizer):
        """Test that user-specific file paths are sanitized"""
        error_msg = "Failed to read file: C:\\Users\\JohnDoe\\AppData\\Roaming\\Mirenku\\tokens.json"
        sanitized = sanitizer.sanitize(error_msg)

        assert "JohnDoe" not in sanitized
        assert "[USER]" in sanitized or "***" in sanitized
        assert "tokens.json" in sanitized  # Keep filename for debugging

    def test_sanitize_json_payloads(self, sanitizer):
        """Test that JSON payloads with secrets are sanitized"""
        error_msg = '{"access_token": "secret_token_123", "expires_in": 3600}'
        sanitized = sanitizer.sanitize(error_msg)

        assert "secret_token_123" not in sanitized
        assert '"access_token": "[REDACTED]"' in sanitized
        assert '"expires_in": 3600' in sanitized  # Non-sensitive data preserved

    def test_logging_integration(self, sanitizer, caplog):
        """Test that sanitizer integrates with logging"""
        # Set up sanitized logger
        logger = logging.getLogger("test_logger")
        handler = sanitizer.create_sanitized_handler()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Log message with sensitive data
        with caplog.at_level(logging.DEBUG):
            logger.error("Auth failed with token: Bearer secret_token_xyz")

        # Check that logged message is sanitized
        assert "secret_token_xyz" not in caplog.text
        assert "[REDACTED]" in caplog.text or "Bearer ***" in caplog.text

    def test_exception_message_sanitization(self, sanitizer):
        """Test that exception messages are sanitized"""
        try:
            raise ValueError("Invalid token: Bearer eyJhbGciOiJIUzI1NiIs")
        except ValueError as e:
            sanitized_error = sanitizer.sanitize_exception(e)

        assert "eyJhbGciOiJIUzI1NiIs" not in str(sanitized_error)
        assert "Invalid token" in str(sanitized_error)

    def test_sanitize_multiple_secrets(self, sanitizer):
        """Test sanitizing multiple secrets in one message"""
        error_msg = (
            "OAuth failed: client_id=abc123def456, client_secret=xyz789, "
            "access_token=token123, refresh_token=refresh456"
        )
        sanitized = sanitizer.sanitize(error_msg)

        # All secrets should be sanitized
        assert "xyz789" not in sanitized  # Secret fully redacted
        assert "token123" not in sanitized  # Token redacted
        assert "refresh456" not in sanitized  # Refresh token redacted
        assert sanitized.count("[REDACTED]") >= 3  # At least 3 secrets redacted

    def test_sanitize_base64_tokens(self, sanitizer):
        """Test that Base64 encoded tokens are detected and sanitized"""
        error_msg = "Token validation failed: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
        sanitized = sanitizer.sanitize(error_msg)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "[TOKEN REDACTED]" in sanitized or "[REDACTED]" in sanitized

    def test_sanitize_preserves_error_type(self, sanitizer):
        """Test that error types and codes are preserved for debugging"""
        error_msg = "HTTP 401: Unauthorized - Token expired"
        sanitized = sanitizer.sanitize(error_msg)

        assert "HTTP 401" in sanitized
        assert "Unauthorized" in sanitized
        assert "Token expired" in sanitized

    def test_custom_patterns(self, sanitizer):
        """Test adding custom sanitization patterns"""
        # Add custom pattern for API keys
        sanitizer.add_pattern(r'api_key=([a-zA-Z0-9]+)', 'api_key=[REDACTED]')

        error_msg = "Request failed with api_key=supersecretkey123"
        sanitized = sanitizer.sanitize(error_msg)

        assert "supersecretkey123" not in sanitized
        assert "api_key=[REDACTED]" in sanitized

    def test_performance_with_large_text(self, sanitizer):
        """Test that sanitization is performant with large error messages"""
        import time

        # Create large error message with multiple secrets
        large_error = "Error: " + "token=secret123 " * 1000

        start_time = time.time()
        sanitized = sanitizer.sanitize(large_error)
        elapsed = time.time() - start_time

        # Should complete quickly (under 100ms for 1000 tokens)
        assert elapsed < 0.1
        assert "secret123" not in sanitized

class TestSanitizingFilterIntegration:
    """Regression (F3): the sanitizer must be wired into the live logging
    pipeline, not just exist as an unused utility."""

    def test_handler_filter_scrubs_secrets(self, tmp_path):
        from utils.logging_config import SanitizingFilter

        log_file = tmp_path / "test.log"
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.addFilter(SanitizingFilter())

        test_logger = logging.getLogger("test_sanitizing_filter")
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)
        try:
            secret = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.super_secret"
            test_logger.info(f"Auth failed with token: {secret}")
        finally:
            handler.close()
            test_logger.removeHandler(handler)

        content = log_file.read_text(encoding="utf-8")
        assert "super_secret" not in content
        assert "Auth failed" in content

    def test_setup_logging_attaches_filter(self, tmp_path):
        from utils.logging_config import SanitizingFilter, setup_logging

        setup_logging(log_dir=tmp_path / "logs", log_level="INFO")
        root = logging.getLogger()
        try:
            assert any(
                any(isinstance(f, SanitizingFilter) for f in h.filters)
                for h in root.handlers
            )
        finally:
            for h in list(root.handlers):
                h.close()
                root.removeHandler(h)
