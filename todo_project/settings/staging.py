# Staging specific settings
from .base import *

DEBUG = False
ALLOWED_HOSTS = ["staging-api.realdevsquad.com", "services.realdevsquad.com"]

JWT_COOKIE_SETTINGS.update(
    {
        "RDS_SESSION_COOKIE_NAME": "rds-session-staging",
        "RDS_SESSION_V2_COOKIE_NAME": "rds-session-v2-staging",
        "COOKIE_DOMAIN": ".realdevsquad.com",
        "COOKIE_SECURE": True,
    }
)

MAIN_APP.update(
    {
        "RDS_BACKEND_BASE_URL": "https://staging-api.realdevsquad.com",
    }
)

# Staging CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://staging-todo.realdevsquad.com",
]

# Security settings for staging
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")
