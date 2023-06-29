"""
Tests for models.
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models


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

    def test_new_user_email_normalised(self):
        """
        Tests that a new user's email address is normalised successfully.
        """
        sample_emails = [['test1@EXAMPLE.com', 'test1@example.com'],
                         ['Test2@Example.com', 'Test2@example.com'],
                         ['test3@EXAMPLE.com', 'test3@example.com'],
                         ['TEST4@EXAMPLE.com', 'TEST4@example.com'],
                         ['test5@example.COM', 'test5@example.com'],
                         ['test6@example.com', 'test6@example.com']]

        for email, expected_email in sample_emails:
            user = get_user_model().objects.create_user(email=email, password='wongy')
            self.assertEqual(user.email, expected_email)

    def test_new_user_without_email_raises_error(self):
        """
        Tests that creating a user without supplying an email address raises ValueError
        """
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', password='wongy')

    def test_create_superuser(self):
        """
        Test that a superuser can be correctly created
        """
        user = get_user_model().objects.create_superuser(email='andor@ferrix.com', password='wongy')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """
        Test creating a recipe is successful
        """
        user = get_user_model().objects.create_user(email='test@example.com', password='test123')
        recipe = models.Recipe.objects.create(
            user=user,
            title='Sample Recipe',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sample recipe description'
        )
        self.assertEqual(str(recipe), recipe.title)
