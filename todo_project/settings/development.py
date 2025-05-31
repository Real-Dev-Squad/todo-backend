# Development specific settings
from .base import (
    JWT_COOKIE_SETTINGS,
    MAIN_APP,
    MIDDLEWARE,
)

DEBUG = True
ALLOWED_HOSTS = ["*"]

JWT_COOKIE_SETTINGS.update(
    {
        "RDS_SESSION_COOKIE_NAME": "rds-session-development",
        "RDS_SESSION_V2_COOKIE_NAME": "rds-session-v2-development",
        "COOKIE_SECURE": False,
    }
)

# RDS Backend Integration for development
MAIN_APP.update(
    {
        "RDS_BACKEND_BASE_URL": "http://localhost:3000",
    }
)

# CORS middleware for development
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
