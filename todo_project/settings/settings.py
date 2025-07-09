import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-w$a*-^hjqf&snr6qd&jkcq%0*5twb!_)qe0&z(2y-17umjr5tn",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Environment configuration
ENV = os.getenv("ENV", "DEVELOPMENT").upper()

# Allowed hosts configuration
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Database configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "todo",
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.common.CommonMiddleware",
    "todo.middlewares.jwt_auth.JWTAuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Add CORS middleware for all environments
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

ROOT_URLCONF = "todo_project.urls"
WSGI_APPLICATION = "todo_project.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = False

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "oauth-sessions",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "todo.exceptions.exception_handler.handle_exception",
    "DEFAULT_PAGINATION_SETTINGS": {
        "DEFAULT_PAGE_LIMIT": 20,
        "MAX_PAGE_LIMIT": 200,
    },
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# JWT Configuration
JWT_AUTH = {
    "ALGORITHM": "RS256",
    "PUBLIC_KEY": os.getenv("RDS_PUBLIC_KEY") or "",
}

# JWT Cookie Settings
JWT_COOKIE_SETTINGS = {
    "RDS_SESSION_COOKIE_NAME": os.getenv("RDS_SESSION_COOKIE_NAME", "rds-session-development"),
    "RDS_SESSION_V2_COOKIE_NAME": os.getenv("RDS_SESSION_V2_COOKIE_NAME", "rds-session-v2-development"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", None),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "False").lower() == "true",
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "Lax"),
    "COOKIE_PATH": "/",
}

# Google OAuth Configuration
GOOGLE_OAUTH = {
    "CLIENT_ID": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    "REDIRECT_URI": os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
    "SCOPES": ["openid", "email", "profile"],
}

# Testing configuration
TESTING = "test" in sys.argv or "pytest" in sys.modules or os.getenv("TESTING") == "True"

if TESTING:
    # Test JWT configuration (HS256 - simpler for tests)
    GOOGLE_JWT = {
        "ALGORITHM": "HS256",
        "PRIVATE_KEY": "test-secret-key-for-jwt-signing-very-long-key-needed-for-security",
        "PUBLIC_KEY": "test-secret-key-for-jwt-signing-very-long-key-needed-for-security",
        "ACCESS_TOKEN_LIFETIME": int(os.getenv("GOOGLE_JWT_ACCESS_LIFETIME", "3600")),
        "REFRESH_TOKEN_LIFETIME": int(os.getenv("GOOGLE_JWT_REFRESH_LIFETIME", "604800")),
    }
else:
    GOOGLE_JWT = {
        "ALGORITHM": "RS256",
        "PRIVATE_KEY": os.getenv("GOOGLE_JWT_PRIVATE_KEY"),
        "PUBLIC_KEY": os.getenv("GOOGLE_JWT_PUBLIC_KEY"),
        "ACCESS_TOKEN_LIFETIME": int(os.getenv("GOOGLE_JWT_ACCESS_LIFETIME", "3600")),
        "REFRESH_TOKEN_LIFETIME": int(os.getenv("GOOGLE_JWT_REFRESH_LIFETIME", "604800")),
    }

# Google Cookie Settings
GOOGLE_COOKIE_SETTINGS = {
    "ACCESS_COOKIE_NAME": os.getenv("GOOGLE_ACCESS_COOKIE_NAME", "ext-access"),
    "REFRESH_COOKIE_NAME": os.getenv("GOOGLE_REFRESH_COOKIE_NAME", "ext-refresh"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", None),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "False").lower() == "true",
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "Lax"),
    "COOKIE_PATH": "/",
}

# Frontend and Service URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# RDS Backend Integration
MAIN_APP = {
    "RDS_BACKEND_BASE_URL": os.getenv("RDS_BACKEND_BASE_URL", "http://localhost:8087"),
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

PUBLIC_PATHS = [
    "/favicon.ico",
    "/v1/health",
    "/api/docs",
    "/api/docs/",
    "/api/schema",
    "/api/schema/",
    "/api/redoc",
    "/api/redoc/",
    "/static/",
    "/v1/auth/google/login",
    "/v1/auth/google/callback",
    "/v1/auth/google/logout",
    "/v1/auth/google/status",
    "/v1/auth/google/refresh",
]

# CORS Configuration
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "True").lower() == "true"

if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")

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

# Security Settings
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", None)
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"

# Swagger/OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "Todo API",
    "DESCRIPTION": "A comprehensive Todo API with authentication and task management",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/v1/",
    "TAGS": [
        {"name": "tasks", "description": "Task management operations"},
        {"name": "auth", "description": "Authentication operations"},
        {"name": "health", "description": "Health check endpoints"},
    ],
    "CONTACT": {
        "name": "API Support",
        "email": "support@example.com",
    },
    "LICENSE": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    "EXTERNAL_DOCS": {
        "description": "Find more info here",
        "url": "https://github.com/your-repo/todo-backend",
    },
}

# Environment-specific Swagger settings
if ENV == "PRODUCTION":
    SPECTACULAR_SETTINGS.update({
        "SWAGGER_UI_SETTINGS": {
            "url": "/todo/api/schema",
        },
    })
elif ENV == "STAGING":
    SPECTACULAR_SETTINGS.update({
        "SWAGGER_UI_SETTINGS": {
            "url": "/staging-todo/api/schema",
        },
    })

STATIC_URL = "/static/" 