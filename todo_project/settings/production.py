from .base import *  # noqa: F403
import os

DEBUG = False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

SPECTACULAR_SETTINGS.update({
    "SWAGGER_UI_SETTINGS": {
        "url": "/todo/api/schema",
    },
})