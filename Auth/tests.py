from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

from .models import CustomUser, Profile

User = get_user_model()


class CustomUserModelTests(TestCase):
    def test_get_full_name(self):
        """Test that get_full_name() returns the full_name field"""
        user = User.objects.create_user(
            email='test@example.com',
            full_name='Test Full Name',
            password='testpass123!'
        )
        self.assertEqual(user.get_full_name(), 'Test Full Name')

    def test_get_short_name(self):
        """Test that get_short_name() returns first part of full_name"""
        user = User.objects.create_user(
            email='test@example.com',
            full_name='Test Full Name',
            password='testpass123!'
        )
        self.assertEqual(user.get_short_name(), 'Test')

    def test_get_short_name_fallback(self):
        """Test that get_short_name() falls back to email if no full_name"""
        user = User.objects.create_user(
            email='test@example.com',
            full_name='',
            password='testpass123!'
        )
        self.assertEqual(user.get_short_name(), 'test')


class ProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )

    def test_profile_creation(self):
        """Test that profile is created correctly"""
        profile = Profile.objects.create(
            user=self.user,
            bio='Test bio',
            github_link='https://github.com/testuser',
            phone_number='+1234567890'
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.bio, 'Test bio')
        self.assertEqual(profile.github_link, 'https://github.com/testuser')
        self.assertEqual(profile.phone_number, '+1234567890')

    def test_profile_str(self):
        """Test that profile __str__ returns correct string"""
        profile = Profile.objects.create(user=self.user)
        self.assertEqual(str(profile), "Test User's Profile")


class AuthRegistrationTests(TestCase):
    def test_register_user_no_duplicate(self):
        """Test that registering a user doesn't create duplicate users"""
        url = reverse('register')
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 1)
        
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.full_name, 'Test User')
        self.assertTrue(Profile.objects.filter(user=user).exists())


class AuthProfileEditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(email='test@example.com', password='testpass123!')
    
    def test_profile_edit_uses_full_name(self):
        """Test that profile edit form uses full_name field"""
        url = reverse('edit_profile')
        data = {
            'full_name': 'Updated Full Name',
            'email': 'test@example.com',
            'bio': 'Test bio',
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'Updated Full Name')
    
    def test_profile_edit_email_validation(self):
        """Test that email validation works correctly"""
        User.objects.create_user(
            email='other@example.com',
            full_name='Other User',
            password='testpass123!'
        )
        
        url = reverse('edit_profile')
        data = {
            'full_name': 'Test User',
            'email': 'other@example.com',
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'This email is already in use.')

    def test_profile_edit_github_link_validation(self):
        """Test that github_link validation works correctly"""
        url = reverse('edit_profile')
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'github_link': 'https://invalid-url.com',
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'github_link', 'Please enter a valid GitHub URL (https://github.com/username)')

    def test_profile_edit_valid_github_link(self):
        """Test that valid github_link is accepted"""
        url = reverse('edit_profile')
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'github_link': 'https://github.com/testuser',
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.github_link, 'https://github.com/testuser')


class ProfilePhotoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.profile = Profile.objects.create(user=self.user)
        self.client.login(email='test@example.com', password='testpass123!')
    
    def create_test_image(self, size_kb=100):
        """Create a test image file"""
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG', quality=80)
        img_bytes.seek(0)
        return SimpleUploadedFile('test.jpg', img_bytes.read(), content_type='image/jpeg')

    def test_profile_edit_valid_photo(self):
        """Test that valid photo upload works"""
        url = reverse('edit_profile')
        photo = self.create_test_image()
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'photo': photo,
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.photo)

    def test_profile_edit_invalid_photo_type(self):
        """Test that invalid photo type is rejected"""
        url = reverse('edit_profile')
        invalid_file = SimpleUploadedFile('test.txt', b'test content', content_type='text/plain')
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'photo': invalid_file,
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'photo', 'Upload a valid image. The file you uploaded was either not an image or a corrupted image.')

    def test_profile_edit_with_existing_photo(self):
        """Test that editing profile with existing photo doesn't crash clean_photo"""
        photo = self.create_test_image()
        self.profile.photo.save('test.jpg', photo)
        self.profile.save()
        
        url = reverse('edit_profile')
        data = {
            'full_name': 'Updated Name',
            'email': 'test@example.com',
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'Updated Name')
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.photo)

    def test_profile_edit_content_type_validation(self):
        """Test that content_type validation works for uploaded files"""
        url = reverse('edit_profile')
        invalid_file = SimpleUploadedFile('test.pdf', b'%PDF-1.4 test content', content_type='application/pdf')
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'photo': invalid_file,
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'photo', 'Upload a valid image. The file you uploaded was either not an image or a corrupted image.')


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            bio='Test bio',
            github_link='https://github.com/testuser'
        )
        self.client.login(email='test@example.com', password='testpass123!')
    
    def test_profile_view_access(self):
        """Test that profile view is accessible"""
        url = reverse('profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')
        self.assertContains(response, 'Test User')
        self.assertContains(response, 'Test bio')

    def test_profile_view_requires_login(self):
        """Test that profile view requires login"""
        self.client.logout()
        url = reverse('profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'{reverse("login")}?next={url}')