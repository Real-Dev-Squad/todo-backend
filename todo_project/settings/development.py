# Add settings for development environment here
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

# Development specific settings
JWT_COOKIE_SETTINGS.update(
    {
        "RDS_SESSION_COOKIE_NAME": "rds-session-development",
        "RDS_SESSION_V2_COOKIE_NAME": "rds-session-v2-development",
        "COOKIE_DOMAIN": "localhost",
        # "COOKIE_SAMESITE": "Lax",
    }
)

# RDS Backend Integration for development
MAIN_APP.update(
    {
        "RDS_BACKEND_BASE_URL": "http://localhost:3000",
        "TODO_FRONTEND_BASE_URL": "http://localhost:4000",
        "AUTH_REDIRECT_URL": "http://localhost:4000?v2=true",
    }
)

# Development CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:4000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:4000",
    "http://127.0.0.1:8000",
]

# Add CORS middleware for development
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")
