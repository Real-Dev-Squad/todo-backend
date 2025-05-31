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
DEBUG = True

ALLOWED_HOSTS = []

# MongoDB Connection Settings
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME")

# Application definition
INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "todo",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "todo.middlewares.jwt_auth.JWTAuthenticationMiddleware",
]

ROOT_URLCONF = "todo_project.urls"

WSGI_APPLICATION = "todo_project.wsgi.application"

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

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

# JWT Verification Settings
JWT_AUTH = {
    "ALGORITHM": "RS256",
    "PUBLIC_KEY": os.getenv("RDS_PUBLIC_KEY"),
}

# Cookie Settings
JWT_COOKIE_SETTINGS = {
    "RDS_SESSION_COOKIE_NAME": os.getenv("RDS_SESSION_COOKIE_NAME", "rds-session-development"),
    "RDS_SESSION_V2_COOKIE_NAME": os.getenv("RDS_SESSION_V2_COOKIE_NAME", "rds-session-v2-development"),
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", None),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "False").lower() == "true",
    "COOKIE_HTTPONLY": True,
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "None"),
    "COOKIE_PATH": "/",
}

# RDS Backend Integration
MAIN_APP = {
    "RDS_BACKEND_BASE_URL": os.getenv("RDS_BACKEND_BASE_URL", "http://localhost:3000"),
}

PUBLIC_PATHS = [
    "/favicon.ico",
    "/api/v1/health",
    # "/api/docs",
    "/static/",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
