"""
Tests for recipe APIs
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """
    Create and return a recipe detail URL
    """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """
    Create and return a default recipe
    """
    defaults = {
        'title': 'sample title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Description',
        'link': 'http://example.com/recipe.pdf'
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):
    """
    Test unauthenticated API requests
    """
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test auth is required to call API
        """
        response = self.client.get(RECIPES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """
    Test authenticated API Requests
    """
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """
        Test retrieving a list of recipes
        """
        create_recipe(user=self.user)
        create_recipe(user=self.user)
        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        # what does the serializer do to the data?
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """
        Test list of recipes is limited to the authenticated user
        """
        other_user = get_user_model().objects.create_user(
            'other@example.com',
            'testpass124'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.filter(user=self.user)
        # what does the serializer do to the data?
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_recipe_detail(self):
        """

        """
        recipe = create_recipe(self.user)
        url = detail_url(recipe.id)
        response = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        """
        Test creating a recipe
        """
        payload = {'title': 'sample recipe',
                   'time_minutes': 30,
                   'price': Decimal('5.99')}
        response = self.client.post(RECIPES_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_create_recipe_with_new_tags(self):
        """
        Test creating a recipe with new tags
        """
        payload = {'title': 'thai prawn curry',
                   'time_minutes': 30,
                   'price': Decimal('2.50'),
                   'tags': [{'name': 'thai'}, {'name': 'dinner'}]}
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """
        Test that creating a recipe with an existing tag does not duplicate the tag
        """
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """
        Test creating tag when updating a recipe
        """
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        # update the tag in the existing recipe
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        # calling tags.all() makes a new query, so no need to refresh from DB
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """
        Assign an existing tag when updating a recipe
        """
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)
        self.assertIn(tag, recipe.tags.all())

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        # update the tag in the existing recipe
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # calling tags.all() makes a new query, so no need to refresh from DB
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """
        Test that tags can be deleted from a recipe successfully.
        """
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)
        self.assertIn(tag, recipe.tags.all())

        payload = {'tags': []}
        url = detail_url(recipe.id)
        # update the tag in the existing recipe
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(tag, recipe.tags.all())

    def test_create_recipe_with_new_ingredients(self):
        """
        Test creating a recipe with new ingredients
        """
        payload = {'title': 'cauliflower tacos',
                   'time_minutes': 30,
                   'price': Decimal('2.50'),
                   'tags': [{'name': 'Mexican'}, {'name': 'Dinner'}],
                   'ingredients': [{'name': 'Cauliflower'}, {'name': 'Tortillas'}]}
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """
        Test that creating a recipe with an existing ingredient does not duplicate the ingredient
        """
        ingredient_beans = Ingredient.objects.create(user=self.user, name='Black Beans')
        payload = {
            'title': 'Refried Beans',
            'time_minutes': 20,
            'price': Decimal('2.50'),
            'ingredients': [{'name': 'Black Beans'}, {'name': 'Paprika'}]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_beans, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """
        Test creating ingredient when updating a recipe
        """
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{'name': 'Cucumber'}]}
        url = detail_url(recipe.id)
        # update the ingredient in the existing recipe
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Cucumber')
        # calling ingredients.all() makes a new query, so no need to refresh from DB
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """
        Assign an existing ingredient when updating a recipe
        """
        ingredient = Ingredient.objects.create(user=self.user, name='Lamb Mince')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)
        self.assertIn(ingredient, recipe.ingredients.all())

        ingredient_beef = Ingredient.objects.create(user=self.user, name='Beef Mince')
        payload = {'ingredients': [{'name': 'Beef Mince'}]}
        url = detail_url(recipe.id)
        # update the ingredient in the existing recipe
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # calling ingredients.all() makes a new query, so no need to refresh from DB
        self.assertIn(ingredient_beef, recipe.ingredients.all())
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredientss(self):
        """
        Test that tags can be deleted from a recipe successfully.
        """
        ingredient = Ingredient.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)
        self.assertIn(ingredient, recipe.ingredients.all())

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        # update the ingredient in the existing recipe
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_filter_by_tags(self):
        """
        Test filtering recipes by tags
        """
        r1 = create_recipe(user=self.user, title='thai curry')
        r2 = create_recipe(user=self.user, title='aubergine with tahini')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Vegetarian')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='fish and chips')

        params = {'tags': f'{tag1.id}, {tag2.id}'}
        response = self.client.get(RECIPES_URL, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, response.data)
        self.assertIn(s2.data, response.data)
        self.assertNotIn(s3.data, response.data)

    def test_filter_by_ingredients(self):
        """
        Test filtering recipes by tags
        """
        r1 = create_recipe(user=self.user, title='Bolognese')
        r2 = create_recipe(user=self.user, title='Lentil Curry')
        ing1 = Ingredient.objects.create(user=self.user, name='Tomato Paste')
        ing2 = Ingredient.objects.create(user=self.user, name='Lentils')
        r1.ingredients.add(ing1)
        r2.ingredients.add(ing2)
        r3 = create_recipe(user=self.user, title='fish and chips')

        params = {'ingredients': f'{ing1.id}, {ing2.id}'}
        response = self.client.get(RECIPES_URL, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, response.data)
        self.assertIn(s2.data, response.data)
        self.assertNotIn(s3.data, response.data)
