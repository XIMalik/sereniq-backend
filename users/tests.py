from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model"""

    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password': 'testpass123'
        }

    def test_create_user(self):
        """Test creating a user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, self.user_data['email'])
        self.assertTrue(user.check_password(self.user_data['password']))
        self.assertEqual(user.role, 'team_member')
        self.assertTrue(user.is_active)

    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123',
            name='Admin User'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, 'admin')

    def test_user_str(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), self.user_data['email'])


class UserAPITest(APITestCase):
    """Test User API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/users/register/'
        self.login_url = '/api/users/login/'
        self.profile_url = '/api/users/profile/'

    def test_register_user(self):
        """Test user registration"""
        data = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'phone_number': '+1234567890',
            'password': 'newpass123',
            'role': 'team_member'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], data['email'])

    def test_register_user_invalid_email(self):
        """Test registration with invalid email"""
        data = {
            'email': 'invalid-email',
            'name': 'Test User',
            'password': 'testpass123'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_user(self):
        """Test user login"""
        # Create user first
        user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='testpass123'
        )
        
        # Login
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'email': 'wrong@example.com',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_profile(self):
        """Test getting user profile"""
        # Create user and token
        user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='testpass123'
        )
        token = Token.objects.create(user=user)
        
        # Get profile
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)

    def test_get_profile_unauthenticated(self):
        """Test getting profile without authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserPermissionsTest(APITestCase):
    """Test user permissions"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            name='Admin User',
            password='admin123',
            role='admin'
        )
        self.staff = User.objects.create_user(
            email='staff@example.com',
            name='Staff User',
            password='staff123',
            role='staff'
        )
        self.user = User.objects.create_user(
            email='user@example.com',
            name='Regular User',
            password='user123',
            role='team_member'
        )

    def test_admin_can_list_users(self):
        """Test admin can list all users"""
        token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_list_users(self):
        """Test regular user cannot list all users"""
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
