import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-w$a*-^hjqf&snr6qd&jkcq%0*5twb!_)qe0&z(2y-17umjr5tn",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
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

ROOT_URLCONF = "todo_project.urls"
WSGI_APPLICATION = "todo_project.wsgi.application"

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
}

JWT_AUTH = {
    "ALGORITHM": "RS256",
    "PUBLIC_KEY": os.getenv("RDS_PUBLIC_KEY") or "",
}

JWT_COOKIE_SETTINGS = {
    "RDS_SESSION_COOKIE_NAME": os.getenv("RDS_SESSION_COOKIE_NAME", "rds-session-development"),
    "RDS_SESSION_V2_COOKIE_NAME": os.getenv("RDS_SESSION_V2_COOKIE_NAME", "rds-session-v2-development"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", None),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "True").lower() == "true",
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "None"),
    "COOKIE_PATH": "/",
}

GOOGLE_OAUTH = {
    "CLIENT_ID": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    "REDIRECT_URI": os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
    "SCOPES": ["openid", "email", "profile"],
}

GOOGLE_JWT = {
    "ALGORITHM": "HS256",
    "SECRET_KEY": os.getenv("GOOGLE_JWT_SECRET_KEY"),
    "ACCESS_TOKEN_LIFETIME": int(os.getenv("GOOGLE_JWT_ACCESS_LIFETIME", "3600")),
    "REFRESH_TOKEN_LIFETIME": int(os.getenv("GOOGLE_JWT_REFRESH_LIFETIME", "604800")),
}

GOOGLE_COOKIE_SETTINGS = {
    "ACCESS_COOKIE_NAME": os.getenv("GOOGLE_ACCESS_COOKIE_NAME", "ext-access"),
    "REFRESH_COOKIE_NAME": os.getenv("GOOGLE_REFRESH_COOKIE_NAME", "ext-refresh"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", None),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "False").lower() == "true",
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "Lax"),
    "COOKIE_PATH": "/",
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4000")

# RDS Backend Integration
MAIN_APP = {
    "RDS_BACKEND_BASE_URL": os.getenv("RDS_BACKEND_BASE_URL", "http://localhost:3000"),
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
    "/static/",
    "/v1/auth/google/login",
    "/v1/auth/google/callback",
    "/v1/auth/google/logout",
    "/v1/auth/google/status",
    "/v1/auth/google/refresh",
]
