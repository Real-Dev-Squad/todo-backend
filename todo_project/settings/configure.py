import os
from dotenv import load_dotenv

load_dotenv()

ENV_VAR_NAME = "ENV"
PRODUCTION = "PRODUCTION"
DEVELOPMENT = "DEVELOPMENT"
STAGING = "STAGING"

PRODUCTION_SETTINGS = "todo_project.settings.production"
DEVELOPMENT_SETTINGS = "todo_project.settings.development"
STAGING_SETTINGS = "todo_project.settings.staging"
DEFAULT_SETTINGS = DEVELOPMENT_SETTINGS


def configure_settings_module():
    env = os.getenv(ENV_VAR_NAME, DEVELOPMENT).upper()

    django_settings_module = DEFAULT_SETTINGS

    if env == PRODUCTION:
        django_settings_module = PRODUCTION_SETTINGS
    elif env == STAGING:
        django_settings_module = STAGING_SETTINGS

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", django_settings_module)
