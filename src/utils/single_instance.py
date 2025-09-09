"""
Single Instance Manager for ensuring only one application instance runs
Handles IPC (Inter-Process Communication) for protocol URLs
"""

import json
import logging
import os
import platform
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class SingleInstanceManager:
    """Manages single instance enforcement and IPC"""
    
    def __init__(self, app_name: str = "Mirenku"):
        """
        Initialize Single Instance Manager
        
        Args:
            app_name: Application name for lock file
        """
        self.app_name = app_name
        self.lock_dir = self._get_lock_dir()
        self.lock_file = self.lock_dir / f"{app_name.lower()}.lock"
        self.message_file = self.lock_dir / f"{app_name.lower()}.msg"
        self.is_primary = False
        self.message_callback = None
        self.listener_thread = None
        self.stop_listener = threading.Event()
        
        # Ensure lock directory exists
        self.lock_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_lock_dir(self) -> Path:
        """
        Get platform-specific directory for lock files
        
        Returns:
            Path to lock directory
        """
        system = platform.system()
        
        if system == 'Windows':
            # Windows: Use temp directory
            temp_dir = os.environ.get('TEMP', os.environ.get('TMP', r'C:\Temp'))
            return Path(temp_dir) / self.app_name
            
        elif system == 'Darwin':  # macOS
            # macOS: Use /tmp or /var/folders
            return Path('/tmp') / self.app_name.lower()
            
        else:  # Linux and others
            # Linux: Use /tmp or /var/run/user
            user_runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
            if user_runtime_dir:
                return Path(user_runtime_dir) / self.app_name.lower()
            else:
                return Path('/tmp') / self.app_name.lower()
    
    def acquire_lock(self) -> bool:
        """
        Try to acquire the application lock
        
        Returns:
            True if lock acquired (primary instance), False otherwise
        """
        try:
            # Check if lock file exists
            if self.lock_file.exists():
                try:
                    # Read existing lock
                    with open(self.lock_file, 'r') as f:
                        lock_data = json.load(f)
                    
                    pid = lock_data.get('pid')
                    
                    # Check if process is still running
                    if self._is_process_running(pid):
                        logger.info(f"Another instance is running (PID: {pid})")
                        return False
                    else:
                        logger.info(f"Stale lock detected (PID: {pid}), removing")
                        self.lock_file.unlink()
                        
                except (json.JSONDecodeError, KeyError):
                    # Corrupted lock file, remove it
                    logger.warning("Corrupted lock file, removing")
                    self.lock_file.unlink()
            
            # Create new lock
            lock_data = {
                'pid': os.getpid(),
                'timestamp': time.time()
            }
            
            with open(self.lock_file, 'w') as f:
                json.dump(lock_data, f)
            
            self.is_primary = True
            logger.info(f"Lock acquired (PID: {os.getpid()})")
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing lock file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            return False
    
    def release(self):
        """Release the application lock"""
        if self.is_primary:
            try:
                if self.lock_file.exists():
                    self.lock_file.unlink()
                logger.info("Lock released")
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")
            finally:
                self.is_primary = False
        
        # Stop listener if running
        if self.listener_thread and self.listener_thread.is_alive():
            self.stop_message_listener()
    
    def is_another_instance_running(self) -> bool:
        """
        Check if another instance is running
        
        Returns:
            True if another instance is running
        """
        if not self.lock_file.exists():
            return False
        
        try:
            with open(self.lock_file, 'r') as f:
                lock_data = json.load(f)
            
            pid = lock_data.get('pid')
            return self._is_process_running(pid)
            
        except (json.JSONDecodeError, IOError):
            return False
    
    def _is_process_running(self, pid: Optional[int]) -> bool:
        """
        Check if a process with given PID is running
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process is running
        """
        if pid is None:
            return False
        
        # If current process, it's definitely running
        if pid == os.getpid():
            return True
        
        if HAS_PSUTIL:
            return psutil.pid_exists(pid)
        else:
            # Fallback: Try to send signal 0 (doesn't actually send signal)
            try:
                os.kill(pid, 0)
                return True
            except (OSError, PermissionError):
                return False
    
    def send_message_to_primary(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the primary instance
        
        Args:
            message: Message data to send
            
        Returns:
            True if message sent successfully
        """
        try:
            # Add timestamp to message
            message['timestamp'] = time.time()
            message['sender_pid'] = os.getpid()
            
            # Write message to file
            with open(self.message_file, 'w') as f:
                json.dump(message, f)
            
            logger.info(f"Message sent to primary instance: {message.get('action')}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def check_for_messages(self) -> Optional[Dict[str, Any]]:
        """
        Check for and retrieve messages (primary instance only)
        
        Returns:
            Message data if available, None otherwise
        """
        if not self.is_primary:
            return None
        
        if not self.message_file.exists():
            return None
        
        try:
            # Read message
            with open(self.message_file, 'r') as f:
                message = json.load(f)
            
            # Delete message file
            self.message_file.unlink()
            
            # Handle message
            self._handle_message(message)
            
            return message
            
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading message: {e}")
            # Delete corrupted message file
            try:
                self.message_file.unlink()
            except:
                pass
            return None
    
    def register_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback for handling messages
        
        Args:
            callback: Function to call with message data
        """
        self.message_callback = callback
    
    def _handle_message(self, message: Dict[str, Any]):
        """
        Handle a received message
        
        Args:
            message: Message data
        """
        logger.info(f"Handling message: {message.get('action')}")
        
        if self.message_callback:
            try:
                self.message_callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
    
    def start_message_listener(self) -> threading.Thread:
        """
        Start a background thread to listen for messages
        
        Returns:
            The listener thread
        """
        if not self.is_primary:
            logger.warning("Only primary instance can start message listener")
            return None
        
        if self.listener_thread and self.listener_thread.is_alive():
            logger.warning("Message listener already running")
            return self.listener_thread
        
        self.stop_listener.clear()
        self.listener_thread = threading.Thread(
            target=self._message_listener_loop,
            daemon=True
        )
        self.listener_thread.start()
        
        logger.info("Message listener started")
        return self.listener_thread
    
    def _message_listener_loop(self):
        """Background loop to check for messages"""
        while not self.stop_listener.is_set():
            try:
                self.check_for_messages()
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
    
    def stop_message_listener(self):
        """Stop the message listener thread"""
        if self.listener_thread and self.listener_thread.is_alive():
            self.stop_listener.set()
            logger.info("Stopping message listener")
    
    def handle_protocol_url(self, url: str) -> bool:
        """
        Handle a protocol URL (convenience method)
        
        Args:
            url: Protocol URL to handle
            
        Returns:
            True if handled successfully
        """
        if self.is_primary:
            # Handle directly
            self._handle_message({
                'action': 'open_url',
                'url': url,
                'timestamp': time.time()
            })
            return True
        else:
            # Send to primary instance
            return self.send_message_to_primary({
                'action': 'open_url',
                'url': url
            })
    
    def __enter__(self):
        """Context manager entry"""
        self.acquire_lock()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False