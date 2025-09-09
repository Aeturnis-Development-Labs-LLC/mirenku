"""
Test suite for Protocol Handler
Tests URL parsing and routing for mirenku:// protocol
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from urllib.parse import quote

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.protocol_handler import ProtocolHandler


class TestProtocolHandlerParsing:
    """Test URL parsing functionality"""
    
    @pytest.fixture
    def handler(self):
        """Create ProtocolHandler instance"""
        return ProtocolHandler()
    
    def test_parse_basic_url(self, handler):
        """Test parsing basic protocol URL"""
        url = "mirenku://auth"
        result = handler.parse_url(url)
        
        assert result is not None
        assert result['scheme'] == 'mirenku'
        assert result['action'] == 'auth'
        assert result['params'] == {}
    
    def test_parse_url_with_params(self, handler):
        """Test parsing URL with query parameters"""
        url = "mirenku://auth?code=abc123&state=xyz789"
        result = handler.parse_url(url)
        
        assert result['scheme'] == 'mirenku'
        assert result['action'] == 'auth'
        assert result['params']['code'] == 'abc123'
        assert result['params']['state'] == 'xyz789'
    
    def test_parse_url_with_encoded_params(self, handler):
        """Test parsing URL with URL-encoded parameters"""
        url = f"mirenku://auth?code={quote('abc/123+456')}&state={quote('xyz 789')}"
        result = handler.parse_url(url)
        
        assert result['params']['code'] == 'abc/123+456'
        assert result['params']['state'] == 'xyz 789'
    
    def test_parse_invalid_scheme(self, handler):
        """Test parsing URL with wrong scheme"""
        url = "http://auth?code=123"
        result = handler.parse_url(url)
        
        assert result is None
    
    def test_parse_malformed_url(self, handler):
        """Test parsing malformed URL"""
        url = "not-a-valid-url"
        result = handler.parse_url(url)
        
        assert result is None
    
    def test_parse_empty_url(self, handler):
        """Test parsing empty URL"""
        result = handler.parse_url("")
        assert result is None
        
        result = handler.parse_url(None)
        assert result is None
    
    def test_parse_url_with_multiple_values(self, handler):
        """Test parsing URL with multiple values for same param"""
        url = "mirenku://test?param=value1&param=value2"
        result = handler.parse_url(url)
        
        # Should get list of values
        assert isinstance(result['params']['param'], list)
        assert 'value1' in result['params']['param']
        assert 'value2' in result['params']['param']


class TestProtocolHandlerRouting:
    """Test action routing functionality"""
    
    @pytest.fixture
    def handler(self):
        """Create ProtocolHandler with callbacks"""
        handler = ProtocolHandler()
        handler.auth_callback = Mock()
        handler.test_callback = Mock()
        return handler
    
    def test_register_auth_handler(self, handler):
        """Test registering auth handler"""
        callback = Mock()
        handler.register_handler('auth', callback)
        
        # Handle auth URL
        handler.handle_url("mirenku://auth?code=123")
        
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0]['code'] == '123'
    
    def test_register_multiple_handlers(self, handler):
        """Test registering multiple handlers"""
        auth_callback = Mock()
        test_callback = Mock()
        
        handler.register_handler('auth', auth_callback)
        handler.register_handler('test', test_callback)
        
        # Handle different URLs
        handler.handle_url("mirenku://auth?code=123")
        handler.handle_url("mirenku://test?message=hello")
        
        auth_callback.assert_called_once()
        test_callback.assert_called_once()
    
    def test_unregistered_action(self, handler):
        """Test handling unregistered action"""
        result = handler.handle_url("mirenku://unknown?param=value")
        
        # Should return False for unhandled action
        assert result is False
    
    def test_handler_exception(self, handler):
        """Test handler exception handling"""
        def bad_handler(params):
            raise ValueError("Test error")
        
        handler.register_handler('bad', bad_handler)
        
        # Should handle exception gracefully
        result = handler.handle_url("mirenku://bad")
        assert result is False
    
    def test_default_handler(self, handler):
        """Test default handler for unknown actions"""
        default_callback = Mock()
        handler.set_default_handler(default_callback)
        
        handler.handle_url("mirenku://unknown?param=value")
        
        default_callback.assert_called_once()


class TestProtocolHandlerOAuth:
    """Test OAuth-specific handling"""
    
    @pytest.fixture
    def handler(self):
        """Create handler with OAuth callback"""
        handler = ProtocolHandler()
        handler.oauth_callback = Mock()
        return handler
    
    def test_oauth_success_callback(self, handler):
        """Test OAuth success callback"""
        callback = Mock()
        handler.register_oauth_handler(callback)
        
        url = "mirenku://auth?code=test_code&state=test_state"
        handler.handle_url(url)
        
        callback.assert_called_once_with(
            code='test_code',
            state='test_state',
            error=None
        )
    
    def test_oauth_error_callback(self, handler):
        """Test OAuth error callback"""
        callback = Mock()
        handler.register_oauth_handler(callback)
        
        url = "mirenku://auth?error=access_denied&error_description=User+denied+access"
        handler.handle_url(url)
        
        callback.assert_called_once()
        args = callback.call_args[1]
        assert args['error'] == 'access_denied'
        assert args['code'] is None
    
    def test_oauth_state_validation(self, handler):
        """Test OAuth state parameter validation"""
        handler.set_expected_state("expected_state_123")
        
        # Valid state
        result = handler.validate_oauth_response({
            'code': 'test_code',
            'state': 'expected_state_123'
        })
        assert result is True
        
        # Invalid state
        result = handler.validate_oauth_response({
            'code': 'test_code',
            'state': 'wrong_state'
        })
        assert result is False
    
    def test_oauth_missing_code(self, handler):
        """Test OAuth response without code"""
        callback = Mock()
        handler.register_oauth_handler(callback)
        
        url = "mirenku://auth?state=test_state"  # No code
        handler.handle_url(url)
        
        callback.assert_called_once()
        args = callback.call_args[1]
        assert args['code'] is None
        assert args['error'] is not None


class TestProtocolHandlerSecurity:
    """Test security features"""
    
    @pytest.fixture
    def handler(self):
        """Create ProtocolHandler instance"""
        return ProtocolHandler()
    
    def test_sanitize_input(self, handler):
        """Test input sanitization"""
        # Test XSS attempt
        url = "mirenku://test?param=<script>alert('xss')</script>"
        result = handler.parse_url(url)
        
        # Should escape or remove dangerous content
        assert '<script>' not in str(result['params']['param'])
    
    def test_url_length_limit(self, handler):
        """Test URL length limit"""
        # Create very long URL
        long_param = 'x' * 10000
        url = f"mirenku://test?param={long_param}"
        
        # Should handle gracefully (implementation dependent)
        result = handler.parse_url(url)
        assert result is not None  # Should parse but maybe truncate
    
    def test_null_byte_injection(self, handler):
        """Test null byte injection prevention"""
        url = "mirenku://test?file=../../../etc/passwd%00.txt"
        result = handler.parse_url(url)
        
        # Should sanitize null bytes
        if result:
            param = result['params'].get('file', '')
            assert '\x00' not in param
    
    def test_path_traversal_prevention(self, handler):
        """Test path traversal prevention"""
        url = "mirenku://open?file=../../../sensitive.txt"
        result = handler.parse_url(url)
        
        # Should detect and handle path traversal attempts
        if result:
            param = result['params'].get('file', '')
            # Implementation should sanitize or reject
            assert '../' not in param or handler.is_safe_path(param) is False


class TestProtocolHandlerIntegration:
    """Test integration with other components"""
    
    @patch('utils.protocol_handler.SingleInstanceManager')
    def test_integration_with_single_instance(self, mock_single_instance):
        """Test integration with SingleInstanceManager"""
        handler = ProtocolHandler()
        
        # Simulate secondary instance sending URL
        mock_instance = mock_single_instance.return_value
        mock_instance.is_primary = False
        
        handler.handle_url("mirenku://auth?code=123", forward_to_primary=True)
        
        # Should forward to primary instance
        mock_instance.send_message_to_primary.assert_called_once()
    
    def test_integration_with_oauth_client(self):
        """Test integration with OAuth client"""
        from unittest.mock import Mock
        
        handler = ProtocolHandler()
        oauth_client = Mock()
        
        # Register OAuth client callback
        handler.register_oauth_handler(oauth_client.handle_callback)
        
        # Simulate OAuth callback
        handler.handle_url("mirenku://auth?code=test_code&state=test_state")
        
        # OAuth client should receive callback
        oauth_client.handle_callback.assert_called_once()
    
    def test_command_line_argument_handling(self):
        """Test handling protocol URL from command line"""
        handler = ProtocolHandler()
        
        # Simulate command line argument
        argv = ["mirenku.exe", "mirenku://auth?code=123"]
        
        url = handler.get_url_from_argv(argv)
        assert url == "mirenku://auth?code=123"
        
        # No protocol URL in arguments
        argv = ["mirenku.exe", "--debug"]
        url = handler.get_url_from_argv(argv)
        assert url is None