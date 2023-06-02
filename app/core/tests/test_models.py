"""
Tests for models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):
    """
    Test Models.
    """
    def test_create_user_with_email_successful(self):
        """
        Tests that creating a user with an email address is successful.
        """
        email = 'wongungurra@evhc.com'
        password = 'wongy'
        user = get_user_model().objects.create_user(email=email, password=password)

        self.assertEqual(user.email, email)
        # can't check the pw string directly as it's stored as a hash
        self.assertTrue(user.check_password(password))
