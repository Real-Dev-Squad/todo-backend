# Development specific settings
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

GOOGLE_OAUTH.update(
    {
        "REDIRECT_URI": "http://localhost:8000/v1/auth/google/callback",
    }
)

FRONTEND_URL = "http://localhost:4000"

JWT_COOKIE_SETTINGS.update(
    {
        "RDS_SESSION_COOKIE_NAME": "rds-session-development",
        "RDS_SESSION_V2_COOKIE_NAME": "rds-session-v2-development",
        "COOKIE_SECURE": False,
    }
)

GOOGLE_COOKIE_SETTINGS.update(
    {
        "COOKIE_DOMAIN": None,
        "COOKIE_SECURE": False,
        "COOKIE_SAMESITE": "Lax",
    }
)


MAIN_APP.update(
    {
        "RDS_BACKEND_BASE_URL": "http://localhost:3000",
    }
)

# CORS middleware for development
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
