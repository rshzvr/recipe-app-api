"""
Tests for the user API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    """
    Create and return a new user
    """
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """
    Test public features of the user API
    """
    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """
        Test that creating a user is successful
        """
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Silly Sally'
        }
        # assert the user is correctly created
        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # make sure the created user has the same password as the payload
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))

        # Ensure the pw field is not returned as part of the response
        self.assertNotIn('password', response.data)

    def test_user_with_email_exists_error(self):
        """
        Test an error is returned if a user with the same email exists
        """
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Silly Sally'
        }
        create_user(**payload)
        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """
        Test an error is returned if a password is less htna 5 chars
        """
        payload = {
            'email': 'test@example.com',
            'password': 'test',
            'name': 'Silly Sally'
        }
        # assert the user is correctly created
        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(email=payload['email']).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """
        Test generates token for valid credentials
        """
        user_details = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Silly Sally'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': user_details['password'],

        }
        response = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """
        Test returns error if invalid credentials provided
        """
        user_details = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Silly Sally'
        }
        create_user(**user_details)

        payload = {
            'email': user_details['email'],
            'password': 'badpass',

        }
        response = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """
        Test that posting a blank password returns an error
        """
        payload = {'email': 'test@example.com', 'password': ''}
        response = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """
        Test auth is required for users
        """
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """
    Test API requests that require authentication
    """
    def setUp(self):
        self.user = create_user(email='test@example.com',
                                password='testpass123',
                                name='Silly Sally')
        self.client = APIClient()
        # Any request made with this client will use the specified user from now on
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """
        Test retrieving profle for logged in user
        """
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'name': self.user.name,
                                         'email': self.user.email})

    def test_post_me_not_allowed(self):
        """
        Test POST is not allowed for the me endpoint
        """
        response = self.client.post(ME_URL, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """
        Test updating the user profile for the authenticated user
        """
        payload = {'name': 'Updated Sally', 'password': 'newpass123'}

        response = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
