import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from todo_project.db.config import DatabaseManager
from todo.models.rate_limit import RateLimitRule, RateLimitCache
from todo.services.dual_write_service import DualWriteService

logger = logging.getLogger(__name__)


class RateLimiterService:
    """Rate limiter service implementing sliding window algorithm with MongoDB storage"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.collection = self.db_manager.get_collection('rate_limit_cache')
        self.rules_collection = self.db_manager.get_collection('rate_limit_rules')
        self.dual_write_service = DualWriteService()
        self._default_rule = None
        self._rules_cache = {}
        self._last_rules_refresh = 0
        self._rules_cache_ttl = 60  # Refresh rules cache every 60 seconds
    
    def _get_default_rule(self) -> Dict:
        """Get or create default rate limiting rule"""
        if self._default_rule is None:
            # Check if default rule exists in MongoDB
            default_rule = self.rules_collection.find_one({"name": "default"})
            
            if not default_rule:
                # Create default rule
                default_rule = {
                    "name": "default",
                    "window_size_minutes": 5,
                    "num_windows": 3,
                    "requests_per_second": 120,
                    "sliding_scale_factor": 0.8,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                self.rules_collection.insert_one(default_rule)
            
            self._default_rule = default_rule
        
        return self._default_rule
    
    def _refresh_rules_cache(self):
        """Refresh the rules cache from MongoDB"""
        current_time = time.time()
        if current_time - self._last_rules_refresh > self._rules_cache_ttl:
            try:
                rules = list(self.rules_collection.find({"is_active": True}))
                self._rules_cache = {rule["name"]: rule for rule in rules}
                self._last_rules_refresh = current_time
                logger.debug(f"Refreshed rate limiting rules cache: {len(rules)} active rules")
            except Exception as e:
                logger.error(f"Failed to refresh rate limiting rules cache: {e}")
    
    def _get_rule(self, rule_name: str = "default") -> Dict:
        """Get rate limiting rule by name"""
        self._refresh_rules_cache()
        return self._rules_cache.get(rule_name, self._get_default_rule())
    
    def _get_current_window_start(self, window_size_minutes: int) -> datetime:
        """Get the start time of the current window"""
        now = timezone.now()
        window_size = timedelta(minutes=window_size_minutes)
        return now - (now - datetime.min.replace(tzinfo=now.tzinfo)) % window_size
    
    def _get_window_key(self, window_start: datetime) -> str:
        """Generate a key for the window"""
        return window_start.strftime("%Y%m%d%H%M")
    
    def _cleanup_old_windows(self, identifier: str, rule_name: str, current_time: datetime):
        """Clean up old window data for an identifier"""
        try:
            # Remove windows older than the total time span
            rule = self._get_rule(rule_name)
            max_age = timedelta(minutes=rule["window_size_minutes"] * rule["num_windows"])
            cutoff_time = current_time - max_age
            
            self.collection.delete_many({
                "identifier": identifier,
                "rule_name": rule_name,
                "window_start": {"$lt": cutoff_time}
            })
        except Exception as e:
            logger.error(f"Failed to cleanup old windows for {identifier}: {e}")
    
    def _get_sliding_window_count(self, identifier: str, rule_name: str, current_time: datetime) -> Tuple[int, float]:
        """Calculate request count using sliding window algorithm"""
        try:
            rule = self._get_rule(rule_name)
            window_size = timedelta(minutes=rule["window_size_minutes"])
            num_windows = rule["num_windows"]
            
            # Get current window start
            current_window_start = self._get_current_window_start(rule["window_size_minutes"])
            
            # Calculate the total time span
            total_span = window_size * num_windows
            
            # Get all windows within the time span
            cutoff_time = current_time - total_span
            
            # Query MongoDB for all relevant windows
            windows = list(self.collection.find({
                "identifier": identifier,
                "rule_name": rule_name,
                "window_start": {"$gte": cutoff_time}
            }).sort("window_start", 1))
            
            if not windows:
                return 0, 0.0
            
            # Calculate weighted request count using sliding window
            total_weighted_count = 0
            total_weight = 0
            
            for window in windows:
                window_start = window["window_start"]
                window_end = window_start + window_size
                
                if window_end <= current_time:
                    # Full window
                    weight = 1.0
                else:
                    # Partial window - calculate overlap
                    overlap = (current_time - window_start).total_seconds() / window_size.total_seconds()
                    weight = max(0.0, min(1.0, overlap))
                
                weighted_count = window["request_count"] * weight
                total_weighted_count += weighted_count
                total_weight += weight
            
            # Apply sliding scale factor
            if total_weight > 0:
                effective_count = total_weighted_count * rule["sliding_scale_factor"]
            else:
                effective_count = 0
            
            return int(effective_count), total_weight
            
        except Exception as e:
            logger.error(f"Failed to calculate sliding window count for {identifier}: {e}")
            return 0, 0.0
    
    def _update_window_count(self, identifier: str, rule_name: str, current_time: datetime):
        """Update the request count for the current window"""
        try:
            rule = self._get_rule(rule_name)
            window_size = timedelta(minutes=rule["window_size_minutes"])
            current_window_start = self._get_current_window_start(rule["window_size_minutes"])
            
            # Try to update existing window
            result = self.collection.update_one(
                {
                    "identifier": identifier,
                    "rule_name": rule_name,
                    "window_start": current_window_start
                },
                {
                    "$inc": {"request_count": 1},
                    "$set": {"last_request_time": current_time}
                },
                upsert=True
            )
            
            if result.upserted_id:
                # New window created, set created_at
                self.collection.update_one(
                    {"_id": result.upserted_id},
                    {"$set": {"created_at": current_time}}
                )
                
                # Sync to PostgreSQL using dual-write service
                window_data = {
                    "identifier": identifier,
                    "rule_name": rule_name,
                    "window_start": current_window_start,
                    "request_count": 1,
                    "last_request_time": current_time,
                    "created_at": current_time
                }
                
                try:
                    self.dual_write_service.create_document(
                        "rate_limit_cache",
                        window_data,
                        str(result.upserted_id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync rate limit cache to PostgreSQL: {e}")
            
        except Exception as e:
            logger.error(f"Failed to update window count for {identifier}: {e}")
    
    def is_rate_limited(self, identifier: str, rule_name: str = "default") -> Tuple[bool, Dict]:
        """Check if the identifier is rate limited"""
        try:
            current_time = timezone.now()
            
            # Cleanup old windows
            self._cleanup_old_windows(identifier, rule_name, current_time)
            
            # Get current request count
            current_count, window_weight = self._get_sliding_window_count(identifier, rule_name, current_time)
            
            # Get rule limits
            rule = self._get_rule(rule_name)
            max_requests_per_second = rule["requests_per_second"]
            window_size_minutes = rule["window_size_minutes"]
            
            # Calculate maximum requests for the current window weight
            max_requests = int(max_requests_per_second * window_size_minutes * 60 * window_weight)
            
            # Check if rate limited
            is_limited = current_count >= max_requests
            
            # Update window count if not limited
            if not is_limited:
                self._update_window_count(identifier, rule_name, current_time)
            
            # Prepare response
            response_data = {
                "is_limited": is_limited,
                "current_count": current_count,
                "max_requests": max_requests,
                "window_weight": window_weight,
                "window_size_minutes": window_size_minutes,
                "requests_per_second": max_requests_per_second,
                "remaining_requests": max(0, max_requests - current_count)
            }
            
            if is_limited:
                logger.warning(f"Rate limit exceeded for {identifier}: {current_count}/{max_requests} requests")
            
            return is_limited, response_data
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {identifier}: {e}")
            # On error, allow the request but log the issue
            return False, {"error": str(e)}
    
    def get_rate_limit_info(self, identifier: str, rule_name: str = "default") -> Dict:
        """Get current rate limit information for an identifier"""
        try:
            current_time = timezone.now()
            current_count, window_weight = self._get_sliding_window_count(identifier, rule_name, current_time)
            rule = self._get_rule(rule_name)
            
            return {
                "identifier": identifier,
                "rule_name": rule_name,
                "current_count": current_count,
                "window_weight": window_weight,
                "window_size_minutes": rule["window_size_minutes"],
                "requests_per_second": rule["requests_per_second"],
                "sliding_scale_factor": rule["sliding_scale_factor"],
                "last_updated": current_time.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting rate limit info for {identifier}: {e}")
            return {"error": str(e)}
    
    def update_rule(self, rule_name: str, **kwargs) -> bool:
        """Update a rate limiting rule dynamically"""
        try:
            # Update in MongoDB
            update_data = {"updated_at": datetime.utcnow()}
            update_data.update(kwargs)
            
            result = self.rules_collection.update_one(
                {"name": rule_name},
                {"$set": update_data},
                upsert=True
            )
            
            # Use dual-write service to sync to PostgreSQL
            if result.upserted_id or result.modified_count > 0:
                # Get the updated rule data
                rule_data = self.rules_collection.find_one({"name": rule_name})
                if rule_data:
                    # Generate a MongoDB ID if it's a new rule
                    mongo_id = str(result.upserted_id) if result.upserted_id else rule_name
                    
                    # Sync to PostgreSQL using dual-write service
                    self.dual_write_service.create_document(
                        "rate_limit_rules", 
                        rule_data, 
                        mongo_id
                    )
            
            # Clear cache to force refresh
            self._rules_cache = {}
            self._last_rules_refresh = 0
            
            logger.info(f"Updated rate limiting rule: {rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update rate limiting rule {rule_name}: {e}")
            return False
    
    def create_ttl_index(self):
        """Create TTL index for automatic cleanup of old rate limit data"""
        try:
            # Create TTL index on created_at field
            # Documents will be automatically deleted after 24 hours
            self.collection.create_index(
                "created_at", 
                expireAfterSeconds=24 * 60 * 60  # 24 hours
            )
            logger.info("Created TTL index on rate_limit_cache collection")
        except Exception as e:
            logger.error(f"Failed to create TTL index: {e}")


# Global instance
rate_limiter_service = RateLimiterService()
