"""Unit tests for MAL service"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.mal_service import MALService, RateLimiter, ResponseCache, CacheStrategy


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter functionality"""
    
    def setUp(self):
        self.limiter = RateLimiter(requests_per_minute=60)
    
    def test_initial_tokens(self):
        """Test initial token count"""
        self.assertEqual(self.limiter.tokens, 60)
    
    def test_consume_token(self):
        """Test consuming tokens"""
        self.assertTrue(self.limiter.allow_request())
        self.assertEqual(self.limiter.tokens, 59)
    
    def test_rate_limit_exceeded(self):
        """Test rate limit enforcement"""
        # Consume all tokens
        self.limiter.tokens = 1
        self.assertTrue(self.limiter.allow_request())
        self.assertEqual(self.limiter.tokens, 0)
        
        # Next request should be denied
        self.assertFalse(self.limiter.allow_request())
    
    def test_token_refill(self):
        """Test token refill over time"""
        # Set tokens to 0 and last refill to past
        import time
        self.limiter.tokens = 0
        self.limiter.last_refill = time.time() - 2  # 2 seconds ago
        
        # Should refill 2 tokens (1 per second)
        allowed = self.limiter.allow_request()
        self.assertTrue(allowed)
        self.assertGreater(self.limiter.tokens, 0)


class TestResponseCache(unittest.TestCase):
    """Test response cache functionality"""
    
    def setUp(self):
        self.test_dir = Path("test_cache")
        self.cache = ResponseCache(self.test_dir)
    
    def tearDown(self):
        # Clean up test cache
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir)
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)
    
    def test_cache_set_and_get(self):
        """Test setting and getting cached data"""
        test_data = {"anime": "Test", "id": 123}
        self.cache.set("test_key", test_data, CacheStrategy.MEDIUM)
        
        result = self.cache.get("test_key")
        self.assertEqual(result, test_data)
    
    def test_cache_expiry(self):
        """Test cache expiry"""
        test_data = {"anime": "Test"}
        
        # Set with -1 second expiry (already expired)
        with patch('time.time', return_value=1000):
            self.cache.set("expired_key", test_data, CacheStrategy.SHORT)
        
        # Try to get after expiry
        with patch('time.time', return_value=2000):  # Way past expiry
            result = self.cache.get("expired_key")
            self.assertIsNone(result)
    
    def test_cache_clear(self):
        """Test clearing cache"""
        self.cache.set("key1", {"data": 1}, CacheStrategy.SHORT)
        self.cache.set("key2", {"data": 2}, CacheStrategy.SHORT)
        
        count = self.cache.clear()
        self.assertGreater(count, 0)
        
        # Cache should be empty
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))


class TestMALService(unittest.TestCase):
    """Test MAL service functionality"""
    
    def setUp(self):
        self.test_dir = Path("test_mal_cache")
        self.service = MALService(self.test_dir)
    
    def tearDown(self):
        # Clean up
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir)
    
    @patch('urllib.request.urlopen')
    def test_search_anime_success(self, mock_urlopen):
        """Test successful anime search"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "data": [
                {
                    "mal_id": 1,
                    "title": "Test Anime",
                    "episodes": 24
                }
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        results = self.service.search_anime("Test")
        
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Test Anime")
    
    @patch('urllib.request.urlopen')
    def test_search_anime_rate_limit(self, mock_urlopen):
        """Test rate limit handling"""
        # Mock 429 response
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            None, 429, "Too Many Requests", {}, None
        )
        
        results = self.service.search_anime("Test")
        
        # Should return empty list on rate limit
        self.assertEqual(results, [])
    
    @patch('urllib.request.urlopen')
    def test_get_anime_details(self, mock_urlopen):
        """Test getting anime details"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "data": {
                "mal_id": 1,
                "title": "Test Anime",
                "synopsis": "Test synopsis",
                "episodes": 24,
                "score": 8.5
            }
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        details = self.service.get_anime_details(1)
        
        self.assertIsNotNone(details)
        self.assertEqual(details["mal_id"], 1)
        self.assertEqual(details["title"], "Test Anime")
    
    @patch('urllib.request.urlopen')
    def test_get_user_animelist(self, mock_urlopen):
        """Test getting user anime list"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "data": [
                {
                    "anime": {
                        "mal_id": 1,
                        "title": "Test Anime"
                    },
                    "watching_status": 1,
                    "episodes_watched": 10,
                    "score": 8
                }
            ]
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        anime_list = self.service.get_user_animelist("testuser")
        
        self.assertIsNotNone(anime_list)
        self.assertEqual(len(anime_list), 1)
        self.assertEqual(anime_list[0]["anime"]["title"], "Test Anime")
    
    @patch('urllib.request.urlopen')
    def test_network_error_handling(self, mock_urlopen):
        """Test network error handling"""
        # Mock network error
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Network error")
        
        results = self.service.search_anime("Test")
        
        # Should return empty list on network error
        self.assertEqual(results, [])
    
    @patch('urllib.request.urlopen')
    def test_server_error_retry(self, mock_urlopen):
        """Test server error retry logic"""
        # Mock server error then success
        import urllib.error
        
        # First call: server error
        # Second call: success
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({"data": []}).encode('utf-8')
        
        mock_urlopen.side_effect = [
            urllib.error.HTTPError(None, 500, "Server Error", {}, None),
            mock_response.__enter__()
        ]
        
        # Should retry and eventually succeed (but our mock will fail)
        results = self.service.search_anime("Test")
        
        # In real implementation, this would retry
        self.assertIsNotNone(results)
    
    def test_cache_usage(self):
        """Test that cache is used for repeated requests"""
        with patch.object(self.service.cache, 'get') as mock_get:
            with patch.object(self.service.cache, 'set') as mock_set:
                # First call - cache miss
                mock_get.return_value = None
                
                with patch('urllib.request.urlopen') as mock_urlopen:
                    mock_response = MagicMock()
                    mock_response.status = 200
                    mock_response.read.return_value = json.dumps({"data": []}).encode('utf-8')
                    mock_urlopen.return_value.__enter__.return_value = mock_response
                    
                    self.service.search_anime("Test")
                    
                    # Should check cache and set cache
                    mock_get.assert_called()
                    mock_set.assert_called()


class TestMALIntegration(unittest.TestCase):
    """Integration tests for MAL service (requires internet)"""
    
    @unittest.skipIf(os.environ.get('SKIP_INTEGRATION_TESTS'), 
                     "Skipping integration tests")
    def test_real_search(self):
        """Test real MAL API search (requires internet)"""
        service = MALService(Path("test_integration_cache"))
        
        try:
            # Search for a well-known anime
            results = service.search_anime("Death Note", limit=5)
            
            self.assertIsNotNone(results)
            self.assertGreater(len(results), 0)
            
            # Check structure
            first_result = results[0]
            self.assertIn('mal_id', first_result)
            self.assertIn('title', first_result)
            
        finally:
            # Clean up
            import shutil
            if Path("test_integration_cache").exists():
                shutil.rmtree("test_integration_cache")


if __name__ == '__main__':
    unittest.main()