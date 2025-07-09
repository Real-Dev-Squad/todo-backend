# Staging specific settings
from .base import *
import os

DEBUG = True
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "staging-api.realdevsquad.com,services.realdevsquad.com").split(",")

# Service domains configuration
SERVICE_DOMAINS = {
    "RDS_API": "staging-api.realdevsquad.com",
    "AUTH": "services.realdevsquad.com",
    "FRONTEND": "staging-todo.realdevsquad.com",
}

# Base URL configuration
BASE_URL = "https://"

GOOGLE_OAUTH.update(
    {
        "REDIRECT_URI": f"{BASE_URL}{SERVICE_DOMAINS['AUTH']}/staging-todo/v1/auth/google/callback",
    }
)

FRONTEND_URL = f"{BASE_URL}{SERVICE_DOMAINS['FRONTEND']}"

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
        "RDS_BACKEND_BASE_URL": f"{BASE_URL}{SERVICE_DOMAINS['RDS_API']}",
    }
)

# Staging CORS settings
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    f"{BASE_URL}{SERVICE_DOMAINS['FRONTEND']}",
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
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_DOMAIN = ".realdevsquad.com"
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

SPECTACULAR_SETTINGS.update({
    "SWAGGER_UI_SETTINGS": {
        "url": "/staging-todo/api/schema",
    },
})