"""Offline queue service for handling MAL operations when offline"""

import logging
import json
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class QueueOperation(Enum):
    """Types of queued operations"""
    SEARCH = "search"
    IMPORT = "import"
    FETCH_DETAILS = "fetch_details"
    FETCH_USER_LIST = "fetch_user_list"
    DOWNLOAD_IMAGE = "download_image"


class OfflineQueueService:
    """Service for queuing MAL operations when offline or rate limited"""
    
    def __init__(self, database, mal_service):
        """Initialize offline queue service
        
        Args:
            database: Database instance
            mal_service: MAL service instance
        """
        self.db = database
        self.mal_service = mal_service
        self.queue = []
        self.processing = False
        self.lock = threading.Lock()
        self.callbacks = {}
        self.max_retries = 3
        self.retry_delay = 60  # seconds
        
        # Load persisted queue from database
        self._load_queue()
        
        # Start processing thread
        self._start_processor()
    
    def _load_queue(self):
        """Load persisted queue from database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM sync_queue 
                    WHERE status IN ('pending', 'processing')
                    ORDER BY created_at ASC
                """)
                
                for row in cursor.fetchall():
                    operation = {
                        'id': row['id'],
                        'type': row['operation'],
                        'data': json.loads(row['data']) if row['data'] else {},
                        'retry_count': row['retry_count'],
                        'created_at': row['created_at']
                    }
                    self.queue.append(operation)
            
            if self.queue:
                logger.info(f"Loaded {len(self.queue)} queued operations")
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")
    
    def add_to_queue(self, operation: QueueOperation, data: Dict, 
                     callback: Optional[Callable] = None) -> int:
        """Add operation to offline queue
        
        Args:
            operation: Type of operation
            data: Operation data
            callback: Optional callback when operation completes
            
        Returns:
            Queue ID
        """
        with self.lock:
            # Create queue entry
            queue_id = self._persist_to_db(operation, data)
            
            queue_item = {
                'id': queue_id,
                'type': operation.value,
                'data': data,
                'retry_count': 0,
                'created_at': datetime.now()
            }
            
            self.queue.append(queue_item)
            
            # Store callback if provided
            if callback:
                self.callbacks[queue_id] = callback
            
            logger.info(f"Queued {operation.value} operation (ID: {queue_id})")
            
            # Try to process immediately
            self._try_process_queue()
            
            return queue_id
    
    def _persist_to_db(self, operation: QueueOperation, data: Dict) -> int:
        """Persist queue item to database
        
        Args:
            operation: Operation type
            data: Operation data
            
        Returns:
            Queue ID
        """
        with self.db.get_cursor() as cursor:
            # For MAL operations, we'll use anime_id 0 as a placeholder
            cursor.execute("""
                INSERT INTO sync_queue (anime_id, operation, data, status)
                VALUES (0, ?, ?, 'pending')
            """, (operation.value, json.dumps(data)))
            
            return cursor.lastrowid
    
    def _start_processor(self):
        """Start background queue processor thread"""
        thread = threading.Thread(target=self._process_loop, daemon=True)
        thread.start()
    
    def _process_loop(self):
        """Background loop for processing queue"""
        while True:
            try:
                time.sleep(30)  # Check every 30 seconds
                self._try_process_queue()
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
    
    def _try_process_queue(self):
        """Try to process pending queue items"""
        if self.processing or not self.queue:
            return
        
        # Check if MAL is accessible
        if not self._is_mal_available():
            logger.debug("MAL not available, queue processing deferred")
            return
        
        with self.lock:
            self.processing = True
        
        try:
            while self.queue and self._is_mal_available():
                item = self.queue[0]
                
                # Check retry count
                if item['retry_count'] >= self.max_retries:
                    logger.error(f"Max retries exceeded for {item['type']} (ID: {item['id']})")
                    self._mark_failed(item['id'], "Max retries exceeded")
                    self.queue.pop(0)
                    continue
                
                # Process operation
                success = self._process_item(item)
                
                if success:
                    logger.info(f"Successfully processed {item['type']} (ID: {item['id']})")
                    self._mark_completed(item['id'])
                    self.queue.pop(0)
                    
                    # Execute callback if exists
                    if item['id'] in self.callbacks:
                        try:
                            self.callbacks[item['id']](item['data'])
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                        del self.callbacks[item['id']]
                else:
                    # Increment retry count and wait
                    item['retry_count'] += 1
                    self._update_retry_count(item['id'], item['retry_count'])
                    
                    # Move to end of queue
                    self.queue.pop(0)
                    self.queue.append(item)
                    
                    # Wait before retrying
                    time.sleep(self.retry_delay)
        finally:
            with self.lock:
                self.processing = False
    
    def _is_mal_available(self) -> bool:
        """Check if MAL API is available
        
        Returns:
            True if available
        """
        try:
            # Try a simple search to test connectivity
            result = self.mal_service.search_anime("test", limit=1)
            return result is not None
        except Exception:
            return False
    
    def _process_item(self, item: Dict) -> bool:
        """Process a queue item
        
        Args:
            item: Queue item
            
        Returns:
            True if successful
        """
        try:
            operation = item['type']
            data = item['data']
            
            if operation == QueueOperation.SEARCH.value:
                result = self.mal_service.search_anime(
                    data.get('query'),
                    limit=data.get('limit', 20)
                )
                return result is not None
                
            elif operation == QueueOperation.FETCH_DETAILS.value:
                result = self.mal_service.get_anime_details(data.get('mal_id'))
                return result is not None
                
            elif operation == QueueOperation.FETCH_USER_LIST.value:
                result = self.mal_service.get_user_animelist(
                    data.get('username'),
                    status=data.get('status')
                )
                return result is not None
                
            elif operation == QueueOperation.DOWNLOAD_IMAGE.value:
                # This would be handled by image service
                return True
                
            else:
                logger.warning(f"Unknown operation type: {operation}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process {item['type']}: {e}")
            return False
    
    def _mark_completed(self, queue_id: int):
        """Mark queue item as completed"""
        from utils.timezone import get_current_datetime
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sync_queue 
                SET status = 'completed', processed_at = ?
                WHERE id = ?
            """, (get_current_datetime(), queue_id))
    
    def _mark_failed(self, queue_id: int, error_msg: str):
        """Mark queue item as failed"""
        from utils.timezone import get_current_datetime
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sync_queue 
                SET status = 'failed', error_message = ?, processed_at = ?
                WHERE id = ?
            """, (error_msg, get_current_datetime(), queue_id))
    
    def _update_retry_count(self, queue_id: int, count: int):
        """Update retry count for queue item"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sync_queue 
                SET retry_count = ?
                WHERE id = ?
            """, (count, queue_id))
    
    def get_queue_status(self) -> Dict:
        """Get queue status information
        
        Returns:
            Dictionary with queue statistics
        """
        with self.lock:
            pending = len(self.queue)
        
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM sync_queue
                GROUP BY status
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['status']] = row['count']
        
        return {
            'pending': pending,
            'completed': stats.get('completed', 0),
            'failed': stats.get('failed', 0),
            'processing': self.processing,
            'mal_available': self._is_mal_available()
        }
    
    def clear_completed(self):
        """Clear completed items from database"""
        with self.db.get_cursor() as cursor:
            cursor.execute("DELETE FROM sync_queue WHERE status = 'completed'")
            logger.info("Cleared completed queue items")
    
    def retry_failed(self):
        """Retry all failed items"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                UPDATE sync_queue 
                SET status = 'pending', retry_count = 0, error_message = NULL
                WHERE status = 'failed'
            """)
            
            # Reload queue
            self._load_queue()
            logger.info("Retrying failed queue items")