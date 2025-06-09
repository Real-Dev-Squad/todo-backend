# Staging specific settings
from .base import *

DEBUG = False
ALLOWED_HOSTS = ["staging-api.realdevsquad.com", "services.realdevsquad.com"]

GOOGLE_OAUTH.update(
    {
        "REDIRECT_URI": "https://services.realdevsquad.com/staging-todo/v1/auth/google/callback",
    }
)

FRONTEND_URL = "https://staging-todo.realdevsquad.com"


JWT_COOKIE_SETTINGS.update(
    {
        "RDS_SESSION_COOKIE_NAME": "rds-session-staging",
        "RDS_SESSION_V2_COOKIE_NAME": "rds-session-v2-staging",
        "COOKIE_DOMAIN": ".realdevsquad.com",
        "COOKIE_SECURE": True,
    }
)

GOOGLE_COOKIE_SETTINGS.update(
    {
        "COOKIE_DOMAIN": ".realdevsquad.com",
        "COOKIE_SECURE": True,
        "COOKIE_SAMESITE": "None",
    }
)

MAIN_APP.update(
    {
        "RDS_BACKEND_BASE_URL": "https://staging-api.realdevsquad.com",
    }
)

# Staging CORS settings
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://staging-todo.realdevsquad.com",
]

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

# Security settings for staging
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_DOMAIN = ".realdevsquad.com"
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True
