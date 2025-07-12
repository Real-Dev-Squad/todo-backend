import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-w$a*-^hjqf&snr6qd&jkcq%0*5twb!_)qe0&z(2y-17umjr5tn",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

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
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.common.CommonMiddleware",
    "todo.middlewares.jwt_auth.JWTAuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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

# APPEND_SLASH = False # Fix the routing issue with trailing slashes and then uncomment this line

JWT_AUTH = {
    "ALGORITHM": "RS256",
    "PUBLIC_KEY": os.getenv("RDS_PUBLIC_KEY"),
}

GOOGLE_OAUTH = {
    "CLIENT_ID": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    "REDIRECT_URI": os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
}

TESTING = (
    "test" in sys.argv or "pytest" in sys.modules or os.getenv("TESTING") == "True"
)

if TESTING:
    # Test JWT configuration (HS256 - simpler for tests)
    JWT_CONFIG = {
        "ALGORITHM": "HS256",
        "PRIVATE_KEY": "test-secret-key-for-jwt-signing-very-long-key-needed-for-security",
        "PUBLIC_KEY": "test-secret-key-for-jwt-signing-very-long-key-needed-for-security",
        "ACCESS_TOKEN_LIFETIME": int(os.getenv("ACCESS_LIFETIME", "3600")),
        "REFRESH_TOKEN_LIFETIME": int(os.getenv("REFRESH_LIFETIME", "604800")),
    }
else:
    JWT_CONFIG = {
        "ALGORITHM": "RS256",
        "PRIVATE_KEY": os.getenv("PRIVATE_KEY"),
        "PUBLIC_KEY": os.getenv("PUBLIC_KEY"),
        "ACCESS_TOKEN_LIFETIME": int(os.getenv("ACCESS_LIFETIME", "3600")),
        "REFRESH_TOKEN_LIFETIME": int(os.getenv("REFRESH_LIFETIME", "604800")),
    }

COOKIE_SETTINGS = {
    "ACCESS_COOKIE_NAME": os.getenv("ACCESS_COOKIE_NAME", "ext-access"),
    "REFRESH_COOKIE_NAME": os.getenv("REFRESH_COOKIE_NAME", "ext-refresh"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", "localhost"),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "true").lower() == "true",
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "Strict"),
    "COOKIE_PATH": "/",
}

SERVICES = {
    "TODO_UI": {
        "URL": os.getenv("TODO_UI_BASE_URL", "http://localhost:3000"),
        "REDIRECT_PATH": os.getenv("TODO_UI_REDIRECT_PATH", "dashboard"),
    },
    "TODO_BACKEND": {
        "URL": os.getenv("TODO_BACKEND_BASE_URL", "http://localhost:8000"),
    },
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
    "/v1/auth/logout",
    "/v1/auth/google/status",
    "/v1/auth/google/refresh",
]

# Swagger/OpenAPI Configuration
SPECTACULAR_SETTINGS = {
    "TITLE": "Todo API",
    "DESCRIPTION": "A comprehensive Todo API with authentication and task management",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/v1/",
    "SWAGGER_UI_SETTINGS": {
        "url": os.getenv("SWAGGER_UI_URL", "/api/schema"),
    },
    "SERVERS": [
        {
            "url": f"{SERVICES.get('TODO_BACKEND').get('URL')}",
            "description": "Development server",
        },
    ],
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

STATIC_URL = "/static/"

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS").split(",")
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

CSRF_COOKIE_SECURE = COOKIE_SETTINGS.get("COOKIE_SECURE")

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
