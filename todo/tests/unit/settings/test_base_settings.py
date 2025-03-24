from unittest import TestCase
from django.conf import settings


class BaseSettingsTest(TestCase):
    """Tests for Django project settings configuration"""

    def test_pagination_settings_exist(self):
        """Test that pagination settings are properly configured in Django settings"""
        self.assertIn("DEFAULT_PAGINATION_SETTINGS", settings.REST_FRAMEWORK)
        pagination_settings = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]
        
        # Verify pagination settings keys
        self.assertIn("DEFAULT_PAGE_LIMIT", pagination_settings)
        self.assertIn("MAX_PAGE_LIMIT", pagination_settings)
        
        # Verify pagination settings values are reasonable
        self.assertIsInstance(pagination_settings["DEFAULT_PAGE_LIMIT"], int)
        self.assertIsInstance(pagination_settings["MAX_PAGE_LIMIT"], int)
        
        # Default should be less than or equal to max
        self.assertLessEqual(
            pagination_settings["DEFAULT_PAGE_LIMIT"], 
            pagination_settings["MAX_PAGE_LIMIT"]
        )
        
        # Settings should be positive
        self.assertGreater(pagination_settings["DEFAULT_PAGE_LIMIT"], 0)
        self.assertGreater(pagination_settings["MAX_PAGE_LIMIT"], 0)
        
    def test_default_pagination_values(self):
        """Test that default pagination values match expected defaults"""
        pagination_settings = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]
        
        # Verify default values (if they change, these tests should be updated)
        self.assertEqual(pagination_settings["DEFAULT_PAGE_LIMIT"], 20)
        self.assertEqual(pagination_settings["MAX_PAGE_LIMIT"], 200) 