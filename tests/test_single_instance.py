"""
Test suite for Single Instance Manager
Ensures only one instance of the application runs and handles IPC
"""

import pytest
import sys
import os
import json
import time
import tempfile
import threading
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.single_instance import SingleInstanceManager


class TestSingleInstanceBasics:
    """Test basic single instance functionality"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for lock files"""
        return tmp_path
    
    @pytest.fixture
    def manager(self, temp_dir):
        """Create SingleInstanceManager with temp directory"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            manager = SingleInstanceManager()
            yield manager
            # Cleanup
            manager.release()
    
    def test_acquire_lock_when_available(self, manager):
        """Test acquiring lock when no other instance exists"""
        assert manager.acquire_lock() is True
        assert manager.is_primary is True
    
    def test_acquire_lock_when_taken(self, temp_dir):
        """Test acquiring lock when another instance exists"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            # First instance
            manager1 = SingleInstanceManager()
            assert manager1.acquire_lock() is True
            
            # Second instance should fail
            manager2 = SingleInstanceManager()
            assert manager2.acquire_lock() is False
            assert manager2.is_primary is False
            
            # Cleanup
            manager1.release()
            manager2.release()
    
    def test_release_lock(self, manager):
        """Test releasing lock"""
        manager.acquire_lock()
        assert manager.is_primary is True
        
        manager.release()
        assert manager.is_primary is False
        
        # Another instance should now be able to acquire
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = manager.lock_dir
            manager2 = SingleInstanceManager()
            assert manager2.acquire_lock() is True
            manager2.release()
    
    def test_lock_file_creation(self, manager, temp_dir):
        """Test lock file is created with PID"""
        manager.acquire_lock()
        
        lock_file = temp_dir / "mirenku.lock"
        assert lock_file.exists()
        
        # Check PID is written
        content = lock_file.read_text()
        data = json.loads(content)
        assert data["pid"] == os.getpid()
        assert "timestamp" in data
    
    def test_stale_lock_detection(self, temp_dir):
        """Test detection and cleanup of stale locks"""
        lock_file = temp_dir / "mirenku.lock"
        
        # Create stale lock (non-existent PID)
        stale_data = {
            "pid": 99999999,  # Non-existent PID
            "timestamp": time.time() - 3600  # 1 hour old
        }
        lock_file.write_text(json.dumps(stale_data))
        
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            manager = SingleInstanceManager()
            
            # Should be able to acquire despite stale lock
            assert manager.acquire_lock() is True
            manager.release()
    
    def test_is_running_check(self, temp_dir):
        """Test checking if another instance is running"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            manager1 = SingleInstanceManager()
            manager2 = SingleInstanceManager()
            
            # No instance running
            assert manager1.is_another_instance_running() is False
            
            # Start first instance
            manager1.acquire_lock()
            
            # Second instance should detect first
            assert manager2.is_another_instance_running() is True
            
            manager1.release()
            manager2.release()


class TestSingleInstanceIPC:
    """Test Inter-Process Communication"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory"""
        return tmp_path
    
    @pytest.fixture
    def primary_manager(self, temp_dir):
        """Create primary instance manager"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            manager = SingleInstanceManager()
            manager.acquire_lock()
            yield manager
            manager.release()
    
    def test_send_message_to_primary(self, primary_manager, temp_dir):
        """Test sending message to primary instance"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            # Secondary instance
            secondary = SingleInstanceManager()
            
            # Send message
            message = {"action": "open_url", "url": "mirenku://auth?code=123"}
            result = secondary.send_message_to_primary(message)
            
            assert result is True
            
            # Check message file exists
            message_file = temp_dir / "mirenku.msg"
            assert message_file.exists()
            
            secondary.release()
    
    def test_receive_message_in_primary(self, primary_manager, temp_dir):
        """Test primary instance receives messages"""
        # Create message file
        message_file = temp_dir / "mirenku.msg"
        message = {"action": "open_url", "url": "mirenku://auth?code=123"}
        message_file.write_text(json.dumps(message))
        
        # Primary should receive message
        received = primary_manager.check_for_messages()
        
        assert received is not None
        assert received["action"] == "open_url"
        assert received["url"] == "mirenku://auth?code=123"
        
        # Message file should be deleted after reading
        assert not message_file.exists()
    
    def test_message_callback_registration(self, primary_manager):
        """Test registering callback for messages"""
        callback = Mock()
        primary_manager.register_message_callback(callback)
        
        # Simulate message
        message = {"action": "test"}
        primary_manager._handle_message(message)
        
        callback.assert_called_once_with(message)
    
    def test_start_message_listener(self, primary_manager):
        """Test message listener thread"""
        callback = Mock()
        primary_manager.register_message_callback(callback)
        
        # Start listener in thread
        listener_thread = primary_manager.start_message_listener()
        
        assert listener_thread is not None
        assert listener_thread.is_alive()
        
        # Stop listener
        primary_manager.stop_message_listener()
        listener_thread.join(timeout=2)
        
        assert not listener_thread.is_alive()
    
    def test_message_queue_ordering(self, primary_manager, temp_dir):
        """Test messages are processed in order"""
        messages_received = []
        
        def callback(msg):
            messages_received.append(msg["id"])
        
        primary_manager.register_message_callback(callback)
        
        # Send multiple messages
        for i in range(3):
            message_file = temp_dir / "mirenku.msg"
            message = {"id": i, "action": "test"}
            message_file.write_text(json.dumps(message))
            time.sleep(0.1)  # Ensure ordering
            primary_manager.check_for_messages()
        
        # Check order
        assert messages_received == [0, 1, 2]


class TestSingleInstancePlatform:
    """Test platform-specific behavior"""
    
    @patch('utils.single_instance.platform.system')
    def test_windows_lock_dir(self, mock_platform):
        """Test Windows lock directory location"""
        mock_platform.return_value = 'Windows'
        
        with patch.dict(os.environ, {'TEMP': r'C:\Users\Test\AppData\Local\Temp'}):
            manager = SingleInstanceManager()
            lock_dir = manager._get_lock_dir()
            
            assert 'Temp' in str(lock_dir)
            assert 'Mirenku' in str(lock_dir)
    
    @patch('utils.single_instance.platform.system')
    def test_linux_lock_dir(self, mock_platform):
        """Test Linux lock directory location"""
        mock_platform.return_value = 'Linux'
        
        manager = SingleInstanceManager()
        lock_dir = manager._get_lock_dir()
        
        assert '/tmp' in str(lock_dir) or '/var/run' in str(lock_dir)
        assert 'mirenku' in str(lock_dir).lower()
    
    @patch('utils.single_instance.platform.system')
    def test_macos_lock_dir(self, mock_platform):
        """Test macOS lock directory location"""
        mock_platform.return_value = 'Darwin'
        
        manager = SingleInstanceManager()
        lock_dir = manager._get_lock_dir()
        
        assert '/tmp' in str(lock_dir) or '/var/folders' in str(lock_dir)
        assert 'mirenku' in str(lock_dir).lower()


class TestSingleInstanceEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory"""
        return tmp_path
    
    def test_corrupted_lock_file(self, temp_dir):
        """Test handling of corrupted lock file"""
        lock_file = temp_dir / "mirenku.lock"
        lock_file.write_text("not valid json{]")
        
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            manager = SingleInstanceManager()
            
            # Should handle corruption and acquire lock
            assert manager.acquire_lock() is True
            manager.release()
    
    def test_permission_denied_lock_file(self, temp_dir):
        """Test handling when lock file has permission issues"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                manager = SingleInstanceManager()
                
                # Should handle permission error gracefully
                assert manager.acquire_lock() is False
    
    def test_concurrent_lock_attempts(self, temp_dir):
        """Test multiple threads trying to acquire lock"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            results = []
            
            def try_acquire():
                manager = SingleInstanceManager()
                result = manager.acquire_lock()
                results.append(result)
                if result:
                    time.sleep(0.5)  # Hold lock briefly
                    manager.release()
            
            # Start multiple threads
            threads = []
            for _ in range(5):
                t = threading.Thread(target=try_acquire)
                threads.append(t)
                t.start()
            
            # Wait for all threads
            for t in threads:
                t.join()
            
            # Only one should have acquired the lock
            assert sum(results) == 1
    
    def test_cleanup_on_crash(self, temp_dir):
        """Test cleanup when process crashes"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            # Simulate process that acquired lock and "crashed"
            lock_file = temp_dir / "mirenku.lock"
            crashed_data = {
                "pid": os.getpid(),  # Current PID (will mock as dead)
                "timestamp": time.time()
            }
            lock_file.write_text(json.dumps(crashed_data))
            
            with patch('utils.single_instance.psutil.pid_exists', return_value=False):
                manager = SingleInstanceManager()
                
                # Should detect dead process and acquire lock
                assert manager.acquire_lock() is True
                manager.release()
    
    def test_rapid_message_sending(self, temp_dir):
        """Test sending many messages rapidly"""
        with patch('utils.single_instance.SingleInstanceManager._get_lock_dir') as mock_dir:
            mock_dir.return_value = temp_dir
            
            primary = SingleInstanceManager()
            primary.acquire_lock()
            
            messages_received = []
            primary.register_message_callback(lambda m: messages_received.append(m))
            
            # Send many messages rapidly
            secondary = SingleInstanceManager()
            for i in range(10):
                secondary.send_message_to_primary({"id": i})
                time.sleep(0.01)  # Small delay
                primary.check_for_messages()
            
            # All messages should be received
            assert len(messages_received) == 10
            
            primary.release()
            secondary.release()