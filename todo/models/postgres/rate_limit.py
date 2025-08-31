from django.db import models
from django.utils import timezone
from datetime import timedelta


class PostgresRateLimitRule(models.Model):
    """PostgreSQL model for storing rate limiting rules and configuration"""
    
    name = models.CharField(max_length=100, unique=True)
    window_size_minutes = models.IntegerField(default=5)
    num_windows = models.IntegerField(default=3)
    requests_per_second = models.IntegerField(default=120)
    sliding_scale_factor = models.FloatField(default=0.8)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'postgres_rate_limit_rules'
        verbose_name = 'Postgres Rate Limit Rule'
        verbose_name_plural = 'Postgres Rate Limit Rules'
    
    def __str__(self):
        return f"{self.name}: {self.requests_per_second} req/sec over {self.num_windows}x{self.window_size_minutes}min"


class PostgresRateLimitCache(models.Model):
    """PostgreSQL model for storing rate limiting cache data"""
    
    identifier = models.CharField(max_length=100, db_index=True)  
    rule_name = models.CharField(max_length=100)
    window_start = models.DateTimeField()
    request_count = models.IntegerField(default=0)
    last_request_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'postgres_rate_limit_cache'
        verbose_name = 'Postgres Rate Limit Cache'
        verbose_name_plural = 'Postgres Rate Limit Cache'
        indexes = [
            models.Index(fields=['identifier', 'rule_name', 'window_start']),
            models.Index(fields=['created_at']),  # For cleanup queries
        ]
    
    def __str__(self):
        return f"{self.identifier}: {self.rule_name} - {self.request_count} requests"
