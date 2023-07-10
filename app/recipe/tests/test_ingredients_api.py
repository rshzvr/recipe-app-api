from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """
    Create and return an ingredient detail URL
    """
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='testpass123'):
    """
    Create and return a new user
    """
    return get_user_model().objects.create_user(email, password)


class PublicIngredientsAPITests(TestCase):
    """
    Test unauthenticated API requests
    """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test auth is required for retrieving tags
        """
        response = self.client.get(INGREDIENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsAPITests(TestCase):
    """
    Test authenticated API requests
    """
    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """
        Test retrieving a list of ingredients
        """
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Vanilla')

        response = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tags_limited_to_user(self):
        """
        Test list of ingredients is limited to authenticated user
        """
        user2 = create_user(email='user2@example.com')
        Ingredient.objects.create(user=user2, name='Strawberry')
        ingredent = Ingredient.objects.create(user=self.user, name='Tahini')

        response = self.client.get(INGREDIENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ingredent.name)
        self.assertEqual(response.data[0]['id'], ingredent.id)

    def test_update_ingredent(self):
        """"
        Test updating a ingredent
        """
        ingredent = Ingredient.objects.create(user=self.user, name='Prawn')

        payload = {'name': 'Shrimp'}
        url = detail_url(ingredent.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ingredent.refresh_from_db()
        self.assertEqual(ingredent.name, payload['name'])

    def test_delete_ingredent(self):
        """
        Test deleting a ingredent
        """
        ingredent = Ingredient.objects.create(user=self.user, name='Bread')
        url = detail_url(ingredent.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        ingredents = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredents.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """
        Test listing ingredients by those assigned to recipes
        """
        ing1 = Ingredient.objects.create(user=self.user, name='Apple')
        ing2 = Ingredient.objects.create(user=self.user, name='Turkey')
        recipe = Recipe.objects.create(
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50'),
            user=self.user
        )
        recipe.ingredients.add(ing1)
        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)
        self.assertIn(s1.data, response.data)
        self.assertNotIn(s2.data, response.data)

    def test_filtered_ingredients_unique(self):
        """
        Test filtered ingredients returns a unique list
        """
        ing = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Lentils')
        recipe1 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=60,
            price=Decimal('7.00'),
            user=self.user
        )
        recipe2 = Recipe.objects.create(
            title='Fried Eggs',
            time_minutes=10,
            price=Decimal('3.00'),
            user=self.user
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(len(response.data), 1)
