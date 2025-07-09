import os
from dotenv import load_dotenv

load_dotenv()

# Set the Django settings module to use the consolidated settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "todo_project.settings.settings")

def configure_settings_module():
    """
    Configure Django settings module to use the consolidated settings file.
    All environment-specific configuration is now handled through environment variables.
    """
    # The settings module is already set above, this function is kept for backward compatibility
    pass
