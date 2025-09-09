"""
Test suite for Protocol Manager
Tests Windows Registry protocol registration/unregistration
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.protocol_manager import ProtocolManager


class TestProtocolManagerWindows:
    """Test Windows Registry protocol registration"""
    
    @pytest.fixture
    def manager(self):
        """Create ProtocolManager instance"""
        return ProtocolManager()
    
    @pytest.fixture
    def mock_registry(self):
        """Mock Windows Registry operations"""
        with patch('utils.protocol_manager.winreg') as mock_winreg:
            mock_key = MagicMock()
            mock_key.__enter__ = MagicMock(return_value=mock_key)
            mock_key.__exit__ = MagicMock(return_value=None)
            
            mock_winreg.CreateKey.return_value = mock_key
            mock_winreg.OpenKey.return_value = mock_key
            mock_winreg.HKEY_CURRENT_USER = 'HKEY_CURRENT_USER'
            mock_winreg.REG_SZ = 1
            mock_winreg.KEY_ALL_ACCESS = 983103
            
            # Mock QueryInfoKey to return no subkeys
            mock_winreg.QueryInfoKey.return_value = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            yield mock_winreg
    
    @patch('utils.protocol_manager.platform.system')
    def test_register_protocol_windows(self, mock_platform, mock_registry, manager):
        """Test protocol registration on Windows"""
        mock_platform.return_value = 'Windows'
        
        exe_path = r"C:\Program Files\Mirenku\mirenku.exe"
        result = manager.register_protocol(exe_path)
        
        assert result is True
        # Verify registry keys were created
        assert mock_registry.CreateKey.called
        assert mock_registry.SetValueEx.called
        
    @patch('utils.protocol_manager.platform.system')
    def test_register_protocol_with_custom_scheme(self, mock_platform, mock_registry, manager):
        """Test registration with custom protocol scheme"""
        mock_platform.return_value = 'Windows'
        
        exe_path = r"C:\Program Files\Mirenku\mirenku.exe"
        result = manager.register_protocol(exe_path, protocol="customapp")
        
        assert result is True
        # Should register customapp:// instead of mirenku://
        calls = mock_registry.CreateKey.call_args_list
        assert any('customapp' in str(call) for call in calls)
    
    @patch('utils.protocol_manager.platform.system')
    def test_unregister_protocol_windows(self, mock_platform, mock_registry, manager):
        """Test protocol unregistration on Windows"""
        mock_platform.return_value = 'Windows'
        
        result = manager.unregister_protocol()
        
        assert result is True
        assert mock_registry.DeleteKey.called
    
    @patch('utils.protocol_manager.platform.system')
    def test_is_registered_true(self, mock_platform, mock_registry, manager):
        """Test checking if protocol is registered (exists)"""
        mock_platform.return_value = 'Windows'
        mock_registry.OpenKey.return_value = MagicMock()
        
        result = manager.is_registered()
        
        assert result is True
        assert mock_registry.OpenKey.called
    
    @patch('utils.protocol_manager.platform.system')
    def test_is_registered_false(self, mock_platform, mock_registry, manager):
        """Test checking if protocol is not registered"""
        mock_platform.return_value = 'Windows'
        mock_registry.OpenKey.side_effect = FileNotFoundError()
        
        result = manager.is_registered()
        
        assert result is False
    
    @patch('utils.protocol_manager.platform.system')
    def test_get_registered_path(self, mock_platform, mock_registry, manager):
        """Test getting the registered executable path"""
        mock_platform.return_value = 'Windows'
        expected_path = r"C:\Program Files\Mirenku\mirenku.exe"
        mock_registry.QueryValueEx.return_value = (f'"{expected_path}" "%1"', 1)
        
        result = manager.get_registered_path()
        
        assert result == expected_path
        assert mock_registry.QueryValueEx.called
    
    @patch('utils.protocol_manager.platform.system')
    def test_needs_reregistration_when_moved(self, mock_platform, mock_registry, manager):
        """Test detecting when app has moved and needs reregistration"""
        mock_platform.return_value = 'Windows'
        old_path = r"C:\OldPath\mirenku.exe"
        new_path = r"C:\NewPath\mirenku.exe"
        
        # Mock that protocol is registered with old path
        mock_registry.QueryValueEx.return_value = (f'"{old_path}" "%1"', 1)
        
        result = manager.needs_reregistration(new_path)
        
        assert result is True
    
    @patch('utils.protocol_manager.platform.system')
    def test_needs_reregistration_when_not_moved(self, mock_platform, mock_registry, manager):
        """Test no reregistration needed when app hasn't moved"""
        mock_platform.return_value = 'Windows'
        current_path = r"C:\Program Files\Mirenku\mirenku.exe"
        
        # Mock that protocol is registered with same path
        mock_registry.QueryValueEx.return_value = (f'"{current_path}" "%1"', 1)
        
        result = manager.needs_reregistration(current_path)
        
        assert result is False
    
    @patch('utils.protocol_manager.platform.system')
    def test_auto_reregister_on_move(self, mock_platform, mock_registry, manager):
        """Test automatic reregistration when app moves"""
        mock_platform.return_value = 'Windows'
        old_path = r"C:\OldPath\mirenku.exe"
        new_path = r"C:\NewPath\mirenku.exe"
        
        # Mock that protocol is registered with old path
        mock_registry.QueryValueEx.return_value = (f'"{old_path}" "%1"', 1)
        
        result = manager.auto_reregister(new_path)
        
        assert result is True
        # Should unregister old and register new
        assert mock_registry.DeleteKey.called
        assert mock_registry.CreateKey.called
    
    @patch('utils.protocol_manager.platform.system')
    def test_register_protocol_admin_error(self, mock_platform, mock_registry, manager):
        """Test handling of permission errors during registration"""
        mock_platform.return_value = 'Windows'
        mock_registry.CreateKey.side_effect = PermissionError("Access denied")
        
        exe_path = r"C:\Program Files\Mirenku\mirenku.exe"
        result = manager.register_protocol(exe_path)
        
        assert result is False
    
    @patch('utils.protocol_manager.platform.system')
    def test_development_mode_no_registration(self, mock_platform, mock_registry):
        """Test that development mode doesn't actually register"""
        mock_platform.return_value = 'Windows'
        
        # Create manager in development mode
        manager = ProtocolManager(development_mode=True)
        
        exe_path = r"C:\Program Files\Mirenku\mirenku.exe"
        result = manager.register_protocol(exe_path)
        
        assert result is True
        # Should not actually modify registry in dev mode
        assert not mock_registry.CreateKey.called


class TestProtocolManagerCrossPlatform:
    """Test cross-platform behavior"""
    
    @patch('utils.protocol_manager.platform.system')
    def test_unsupported_platform(self, mock_platform):
        """Test behavior on unsupported platforms"""
        mock_platform.return_value = 'Linux'
        
        manager = ProtocolManager()
        result = manager.register_protocol("/usr/bin/mirenku")
        
        # Should return False or raise NotImplementedError
        assert result is False
    
    @patch('utils.protocol_manager.platform.system')
    def test_macos_not_implemented(self, mock_platform):
        """Test macOS returns not implemented"""
        mock_platform.return_value = 'Darwin'
        
        manager = ProtocolManager()
        result = manager.register_protocol("/Applications/Mirenku.app")
        
        assert result is False