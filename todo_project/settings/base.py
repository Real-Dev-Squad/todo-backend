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

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else []

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

# Postgres Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "todo_postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "todo_password")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "todo",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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

ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "").split(",")


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

GOOGLE_OAUTH = {
    "CLIENT_ID": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    "REDIRECT_URI": os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
}

TESTING = "test" in sys.argv or "pytest" in sys.modules or os.getenv("TESTING") == "True"

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
        "REFRESH_TOKEN_LIFETIME": int(os.getenv("REFRESH_TOKEN_LIFETIME", "604800")),
    }

COOKIE_SETTINGS = {
    "ACCESS_COOKIE_NAME": os.getenv("ACCESS_TOKEN_COOKIE_NAME", "todo-access"),
    "REFRESH_COOKIE_NAME": os.getenv("REFRESH_TOKEN_COOKIE_NAME", "todo-refresh"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", "localhost"),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "True").lower() == "true",
    "COOKIE_HTTPONLY": os.getenv("COOKIE_HTTPONLY", "True").lower() == "true",
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

# Database Configuration
# Only configure PostgreSQL if not in testing mode
if not TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": POSTGRES_DB,
            "USER": POSTGRES_USER,
            "PASSWORD": POSTGRES_PASSWORD,
            "HOST": POSTGRES_HOST,
            "PORT": POSTGRES_PORT,
            "OPTIONS": {
                "sslmode": "prefer",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# Dual-Write Configuration
DUAL_WRITE_ENABLED = os.getenv("DUAL_WRITE_ENABLED", "True").lower() == "true"
DUAL_WRITE_RETRY_ATTEMPTS = int(os.getenv("DUAL_WRITE_RETRY_ATTEMPTS", "3"))
DUAL_WRITE_RETRY_DELAY = int(os.getenv("DUAL_WRITE_RETRY_DELAY", "5"))  # seconds

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
        "url": os.getenv("SWAGGER_UI_PATH", "/api/schema"),
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

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
