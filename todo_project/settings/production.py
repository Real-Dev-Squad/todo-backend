# Production specific settings
from .base import (
    JWT_COOKIE_SETTINGS,
    MAIN_APP,
    MIDDLEWARE,
)
import os

DEBUG = False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

JWT_COOKIE_SETTINGS.update(
    {
        "RDS_SESSION_COOKIE_NAME": "rds-session",
        "RDS_SESSION_V2_COOKIE_NAME": "rds-session-v2",
        "COOKIE_DOMAIN": ".realdevsquad.com",
        "COOKIE_SECURE": True,
    }
)

MAIN_APP.update(
    {
        "RDS_BACKEND_BASE_URL": "https://api.realdevsquad.com",
        "TODO_FRONTEND_BASE_URL": "https://todo.realdevsquad.com",  # placeholder
        "AUTH_REDIRECT_URL": "https://todo.realdevsquad.com?v2=true",  # placeholder
    }
)

# Production CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://todo.realdevsquad.com",
]

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")
