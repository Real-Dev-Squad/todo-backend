import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from todo.services.rate_limiter_service import rate_limiter_service

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(MiddlewareMixin):
    """Middleware for applying rate limiting globally to all requests"""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        # Create TTL index on startup
        try:
            rate_limiter_service.create_ttl_index()
        except Exception as e:
            logger.error(f"Failed to create TTL index on startup: {e}")

    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        # Check for forwarded IP headers (for proxy/load balancer setups)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Get the first IP in the chain
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("HTTP_X_REAL_IP")

        if not ip:
            ip = request.META.get("REMOTE_ADDR")

        # Fallback to localhost if no IP found
        if not ip:
            ip = "127.0.0.1"

        return ip

    def _should_skip_rate_limiting(self, request):
        """Check if rate limiting should be skipped for this request"""
        # Skip rate limiting for health checks and admin endpoints
        path = request.path.lower()

        skip_paths = [
            "/health/",
            "/healthcheck/",
            "/admin/",
            "/static/",
            "/media/",
            "/favicon.ico",
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    def process_request(self, request):
        """Process the request and apply rate limiting"""
        try:
            # Skip rate limiting for certain paths
            if self._should_skip_rate_limiting(request):
                return None

            # Get client IP address
            client_ip = self._get_client_ip(request)

            # Check rate limit
            is_limited, rate_limit_data = rate_limiter_service.is_rate_limited(
                identifier=client_ip, rule_name="default"
            )

            if is_limited:
                # Rate limit exceeded - return 429 error
                response_data = {
                    "error": "rate limit reached",
                    "message": "Too many requests. Please try again later.",
                    "rate_limit_info": {
                        "current_count": rate_limit_data.get("current_count", 0),
                        "max_requests": rate_limit_data.get("max_requests", 0),
                        "window_size_minutes": rate_limit_data.get("window_size_minutes", 5),
                        "requests_per_second": rate_limit_data.get("requests_per_second", 120),
                    },
                }

                response = JsonResponse(response_data, status=429, content_type="application/json")

                # Add rate limit headers
                response["X-RateLimit-Limit"] = str(rate_limit_data.get("max_requests", 0))
                response["X-RateLimit-Remaining"] = str(rate_limit_data.get("remaining_requests", 0))
                response["X-RateLimit-Reset"] = str(rate_limit_data.get("window_size_minutes", 5) * 60)
                response["X-RateLimit-Exceeded"] = "true"

                logger.warning(f"Rate limit exceeded for IP {client_ip}: {rate_limit_data}")
                return response

            # Rate limit not exceeded - add rate limit headers to response
            request.rate_limit_data = rate_limit_data
            return None

        except Exception as e:
            logger.error(f"Error in rate limiter middleware: {e}")
            # On error, allow the request to proceed
            return None

    def process_response(self, request, response):
        """Add rate limit headers to successful responses"""
        try:
            # Add rate limit headers if available
            if hasattr(request, "rate_limit_data"):
                rate_data = request.rate_limit_data

                response["X-RateLimit-Limit"] = str(rate_data.get("max_requests", 0))
                response["X-RateLimit-Remaining"] = str(rate_data.get("remaining_requests", 0))
                response["X-RateLimit-Reset"] = str(rate_data.get("window_size_minutes", 5) * 60)
                response["X-RateLimit-Exceeded"] = "false"

        except Exception as e:
            logger.error(f"Error adding rate limit headers: {e}")

        return response
