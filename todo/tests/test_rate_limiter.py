from django.test import TestCase, RequestFactory
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

from todo.services.rate_limiter_service import RateLimiterService
from todo.middlewares.rate_limiter import RateLimiterMiddleware


class RateLimiterServiceTest(TestCase):
    """Test cases for RateLimiterService"""
    
    def setUp(self):
        self.service = RateLimiterService()
        self.mock_collection = MagicMock()
        self.mock_rules_collection = MagicMock()
        self.service.collection = self.mock_collection
        self.service.rules_collection = self.mock_rules_collection
        
        # Mock default rule
        self.default_rule = {
            "name": "default",
            "window_size_minutes": 5,
            "num_windows": 3,
            "requests_per_second": 120,
            "sliding_scale_factor": 0.8,
            "is_active": True
        }
        self.service._default_rule = self.default_rule
        self.service._rules_cache = {"default": self.default_rule}
    
    def test_get_default_rule(self):
        """Test getting default rule"""
        rule = self.service._get_rule("default")
        self.assertEqual(rule["name"], "default")
        self.assertEqual(rule["requests_per_second"], 120)
    
    def test_get_current_window_start(self):
        """Test window start calculation"""
        window_start = self.service._get_current_window_start(5)
        self.assertIsInstance(window_start, datetime)
        
        # Window should be aligned to 5-minute boundaries
        minutes = window_start.minute
        self.assertIn(minutes, [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    
    def test_cleanup_old_windows(self):
        """Test cleanup of old windows"""
        current_time = timezone.now()
        self.service._cleanup_old_windows("127.0.0.1", "default", current_time)
        
        # Verify delete_many was called
        self.mock_collection.delete_many.assert_called_once()
    
    def test_sliding_window_count_no_windows(self):
        """Test sliding window count with no existing windows"""
        current_time = timezone.now()
        self.mock_collection.find.return_value = []
        
        count, weight = self.service._get_sliding_window_count("127.0.0.1", "default", current_time)
        
        self.assertEqual(count, 0)
        self.assertEqual(weight, 0.0)
    
    def test_sliding_window_count_with_windows(self):
        """Test sliding window count with existing windows"""
        current_time = timezone.now()
        window_start = current_time - timedelta(minutes=2)
        
        mock_windows = [
            {
                "window_start": window_start,
                "request_count": 50
            }
        ]
        
        self.mock_collection.find.return_value = mock_windows
        
        count, weight = self.service._get_sliding_window_count("127.0.0.1", "default", current_time)
        
        self.assertGreater(count, 0)
        self.assertGreater(weight, 0.0)
    
    def test_update_window_count(self):
        """Test updating window count"""
        current_time = timezone.now()
        self.mock_collection.update_one.return_value = MagicMock(upserted_id=None)
        
        self.service._update_window_count("127.0.0.1", "default", current_time)
        
        # Verify update_one was called
        self.mock_collection.update_one.assert_called_once()
    
    def test_is_rate_limited_not_limited(self):
        """Test rate limiting when not limited"""
        current_time = timezone.now()
        
        with patch.object(self.service, '_get_sliding_window_count', return_value=(50, 1.0)):
            is_limited, data = self.service.is_rate_limited("127.0.0.1", "default")
            
            self.assertFalse(is_limited)
            self.assertIn("current_count", data)
            self.assertIn("max_requests", data)
    
    def test_is_rate_limited_exceeded(self):
        """Test rate limiting when limit exceeded"""
        current_time = timezone.now()
        
        with patch.object(self.service, '_get_sliding_window_count', return_value=(150, 1.0)):
            is_limited, data = self.service.is_rate_limited("127.0.0.1", "default")
            
            self.assertTrue(is_limited)
            self.assertIn("current_count", data)
            self.assertIn("max_requests", data)
    
    def test_update_rule(self):
        """Test updating rate limiting rules"""
        self.mock_rules_collection.update_one.return_value = MagicMock(modified_count=1)
        
        success = self.service.update_rule("default", requests_per_second=100)
        
        self.assertTrue(success)
        self.mock_rules_collection.update_one.assert_called_once()
    
    def test_create_ttl_index(self):
        """Test creating TTL index"""
        self.service.create_ttl_index()
        
        # Verify create_index was called with TTL parameters
        self.mock_collection.create_index.assert_called_once()
        call_args = self.mock_collection.create_index.call_args
        self.assertEqual(call_args[0][0], "created_at")


class RateLimiterMiddlewareTest(TestCase):
    """Test cases for RateLimiterMiddleware"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RateLimiterMiddleware()
        
        # Mock the rate limiter service
        self.mock_service = MagicMock()
        self.middleware.rate_limiter_service = self.mock_service
    
    def test_get_client_ip_remote_addr(self):
        """Test IP extraction from REMOTE_ADDR"""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
    
    def test_get_client_ip_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header"""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.100'
        
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')
    
    def test_get_client_ip_x_real_ip(self):
        """Test IP extraction from X-Real-IP header"""
        request = self.factory.get('/')
        request.META['HTTP_X_REAL_IP'] = '172.16.0.1'
        
        ip = self.middleware._get_client_ip(request)
        self.assertEqual(ip, '172.16.0.1')
    
    def test_should_skip_rate_limiting_admin(self):
        """Test skipping rate limiting for admin paths"""
        request = self.factory.get('/admin/')
        
        should_skip = self.middleware._should_skip_rate_limiting(request)
        self.assertTrue(should_skip)
    
    def test_should_skip_rate_limiting_api(self):
        """Test not skipping rate limiting for API paths"""
        request = self.factory.get('/api/tasks/')
        
        should_skip = self.middleware._should_skip_rate_limiting(request)
        self.assertFalse(should_skip)
    
    def test_process_request_rate_limited(self):
        """Test processing request when rate limited"""
        request = self.factory.get('/api/tasks/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Mock rate limiter to return limited
        self.mock_service.is_rate_limited.return_value = (True, {
            "current_count": 150,
            "max_requests": 120,
            "window_size_minutes": 5,
            "requests_per_second": 120
        })
        
        response = self.middleware.process_request(request)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)
        
        # Check response content
        response_data = json.loads(response.content)
        self.assertEqual(response_data["error"], "rate limit reached")
    
    def test_process_request_not_rate_limited(self):
        """Test processing request when not rate limited"""
        request = self.factory.get('/api/tasks/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Mock rate limiter to return not limited
        self.mock_service.is_rate_limited.return_value = (False, {
            "current_count": 50,
            "max_requests": 120,
            "window_size_minutes": 5,
            "requests_per_second": 120
        })
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertTrue(hasattr(request, 'rate_limit_data'))
    
    def test_process_response_with_rate_limit_data(self):
        """Test adding rate limit headers to response"""
        request = self.factory.get('/api/tasks/')
        request.rate_limit_data = {
            "max_requests": 120,
            "remaining_requests": 70,
            "window_size_minutes": 5
        }
        
        response = self.factory.get('/api/tasks/')
        
        processed_response = self.middleware.process_response(request, response)
        
        # Check that headers were added
        self.assertIn('X-RateLimit-Limit', processed_response)
        self.assertIn('X-RateLimit-Remaining', processed_response)
        self.assertIn('X-RateLimit-Reset', processed_response)
        self.assertIn('X-RateLimit-Exceeded', processed_response)
    
    def test_process_response_without_rate_limit_data(self):
        """Test processing response without rate limit data"""
        request = self.factory.get('/api/tasks/')
        response = self.factory.get('/api/tasks/')
        
        processed_response = self.middleware.process_response(request, response)
        
        # Response should be unchanged
        self.assertEqual(response, processed_response)
    
    def test_middleware_error_handling(self):
        """Test middleware error handling"""
        request = self.factory.get('/api/tasks/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Mock rate limiter to raise exception
        self.mock_service.is_rate_limited.side_effect = Exception("Database error")
        
        response = self.middleware.process_request(request)
        
        # On error, should allow request to proceed
        self.assertIsNone(response)
