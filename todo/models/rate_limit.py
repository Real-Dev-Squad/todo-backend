from django.db import models


class RateLimitRule(models.Model):
    """Model for storing rate limiting rules and configuration"""

    name = models.CharField(max_length=100, unique=True)
    window_size_minutes = models.IntegerField(default=5)
    num_windows = models.IntegerField(default=3)
    requests_per_second = models.IntegerField(default=120)
    sliding_scale_factor = models.FloatField(default=0.8)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rate_limit_rules"
        verbose_name = "Rate Limit Rule"
        verbose_name_plural = "Rate Limit Rules"

    def __str__(self):
        return f"{self.name}: {self.requests_per_second} req/sec over {self.num_windows}x{self.window_size_minutes}min"


class RateLimitCache(models.Model):
    """Model for storing rate limiting cache data in MongoDB"""

    identifier = models.CharField(max_length=100, db_index=True)  # IP address or other identifier
    rule_name = models.CharField(max_length=100)
    window_start = models.DateTimeField()
    request_count = models.IntegerField(default=0)
    last_request_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rate_limit_cache"
        verbose_name = "Rate Limit Cache"
        verbose_name_plural = "Rate Limit Cache"
        indexes = [
            models.Index(fields=["identifier", "rule_name", "window_start"]),
            models.Index(fields=["created_at"]),  # For TTL cleanup
        ]

    def __str__(self):
        return f"{self.identifier}: {self.rule_name} - {self.request_count} requests"
