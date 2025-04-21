import unittest
import os
from unittest.mock import patch
from todo_project.settings.configure import (
    configure_settings_module,
    PRODUCTION_SETTINGS,
    DEFAULT_SETTINGS,
    ENV_VAR_NAME,
    PRODUCTION,
)


class SettingModuleConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {ENV_VAR_NAME: PRODUCTION}, clear=True)
    def test_uses_production_settings_when_env_var_set(self):
        configure_settings_module()
        self.assertEqual(os.getenv("DJANGO_SETTINGS_MODULE"), PRODUCTION_SETTINGS)

    def test_uses_default_settings_when_env_var_not_set(self):
        configure_settings_module()
        self.assertEqual(os.getenv("DJANGO_SETTINGS_MODULE"), DEFAULT_SETTINGS)
