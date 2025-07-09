import unittest
import os
from unittest.mock import patch
from todo_project.settings.configure import configure_settings_module


class SettingModuleConfigTests(unittest.TestCase):
    def test_uses_consolidated_settings(self):
        """Test that the consolidated settings module is used regardless of environment."""
        configure_settings_module()
        self.assertEqual(os.getenv("DJANGO_SETTINGS_MODULE"), "todo_project.settings.settings")

    def test_configure_settings_module_function_exists(self):
        """Test that the configure_settings_module function exists and is callable."""
        self.assertTrue(callable(configure_settings_module))
