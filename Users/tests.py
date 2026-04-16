from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from datetime import date

User = get_user_model()


class UserModelTests(TestCase):
    """Test User model functionality"""
    
    def setUp(self):
        self.user_data = {
            'email': 'sara@finova.com',
            'username': 'sara_invests',
            'password': 'SecurePass123!',
            'first_name': 'Sara',
            'last_name': 'Investor',
            'date_of_birth': date(1995, 5, 15),
            'gender_identity': 'woman'
        }
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, 'sara@finova.com')
        self.assertEqual(user.username, 'sara_invests')
        self.assertTrue(user.check_password('SecurePass123!'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_verified)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        admin = User.objects.create_superuser(
            email='admin@finova.com',
            username='admin',
            password='AdminPass123!'
        )
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_verified)
    
    def test_user_age_calculation(self):
        """Test age property calculation"""
        user = User.objects.create_user(**self.user_data)
        expected_age = date.today().year - 1995
        
        self.assertIsNotNone(user.age)
        self.assertGreaterEqual(user.age, expected_age - 1)
    
    def test_increment_consensus_score(self):
        """Test consensus score increment"""
        user = User.objects.create_user(**self.user_data)
        initial_score = user.consensus_score
        
        user.increment_consensus_score(10)
        self.assertEqual(user.consensus_score, initial_score + 10)
    
    def test_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Sara Investor')


class UserAPITests(APITestCase):
    """Test User API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('users:register')
        self.user_data = {
            'email': 'newuser@finova.com',
            'username': 'new_investor',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'date_of_birth': '2000-01-01',
            'gender_identity': 'woman',
            'bio': 'Learning to invest!'
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post(self.register_url, self.user_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'newuser@finova.com')
    
    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = self.user_data.copy()
        data['password_confirm'] = 'DifferentPass123!'
        
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_registration_underage(self):
        """Test registration with age < 18"""
        data = self.user_data.copy()
        data['date_of_birth'] = '2010-01-01'
        
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_user_profile_authenticated(self):
        """Test retrieving own profile when authenticated"""
        user = User.objects.create_user(
            email='test@finova.com',
            username='testuser',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=user)
        
        url = reverse('users:user-me')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@finova.com')
    
    def test_update_profile(self):
        """Test updating user profile"""
        user = User.objects.create_user(
            email='test@finova.com',
            username='testuser',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=user)
        
        url = reverse('users:user-update-profile')
        data = {'bio': 'Updated bio'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.bio, 'Updated bio')