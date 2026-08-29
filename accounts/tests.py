from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import SellerRequest

User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )

    def test_user_str(self):
        self.assertEqual(str(self.user), 'testuser')

    def test_user_default_buyer(self):
        self.assertTrue(self.user.is_buyer)
        self.assertFalse(self.user.is_seller)

    def test_user_absolute_url(self):
        self.assertEqual(self.user.get_absolute_url(), reverse('accounts:profile', kwargs={'pk': self.user.pk}))


class SellerRequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='seller1', password='pass1234'
        )
        self.request = SellerRequest.objects.create(
            user=self.user,
            business_name='Test Shop',
            description='Selling electronics',
            phone_number='9841000000',
        )

    def test_seller_request_str(self):
        self.assertIn(self.user.username, str(self.request))
        self.assertIn('PENDING', str(self.request))

    def test_approve(self):
        self.request.approve()
        self.request.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.request.status, 'APPROVED')
        self.assertTrue(self.user.is_seller)

    def test_reject(self):
        self.request.reject(reason='Not suitable')
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, 'REJECTED')
        self.assertEqual(self.request.admin_notes, 'Not suitable')


class RegistrationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:register')

    def test_get_register(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_register_success(self):
        response = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_password_mismatch(self):
        response = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'pass1',
            'password_confirm': 'pass2',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username='existing', password='pass1234')
        response = self.client.post(self.url, {
            'username': 'existing',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'pass1234',
            'password_confirm': 'pass1234',
        })
        self.assertEqual(response.status_code, 200)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='logintest', password='testpass123'
        )

    def test_get_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(self.url, {
            'username': 'logintest',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_failure(self):
        response = self.client.post(self.url, {
            'username': 'logintest',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='logouttest', password='testpass123'
        )
        self.client.login(username='logouttest', password='testpass123')

    def test_logout_redirects_to_home(self):
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')


class AdminLogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='adminlogout', password='testpass123', email='adminlogout@example.com'
        )
        self.client.login(username='adminlogout', password='testpass123')

    def test_admin_logout_redirects_to_home(self):
        response = self.client.post('/admin/logout/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/')


class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='profiletest', password='testpass123'
        )

    def test_profile_view(self):
        response = self.client.get(reverse('accounts:profile', kwargs={'pk': self.user.pk}))
        self.assertEqual(response.status_code, 200)

    def test_profile_edit_requires_login(self):
        response = self.client.get(reverse('accounts:profile_edit'))
        self.assertEqual(response.status_code, 302)

    def test_profile_edit(self):
        self.client.login(username='profiletest', password='testpass123')
        response = self.client.get(reverse('accounts:profile_edit'))
        self.assertEqual(response.status_code, 200)


class BecomeSellerViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='sellertest', password='testpass123'
        )
        self.url = reverse('accounts:become_seller')

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_become_seller_get(self):
        self.client.login(username='sellertest', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_become_seller_post(self):
        self.client.login(username='sellertest', password='testpass123')
        response = self.client.post(self.url, {
            'business_name': 'My Shop',
            'description': 'Selling books',
            'phone_number': '9841000000',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SellerRequest.objects.filter(user=self.user).exists())

    def test_already_seller_redirects(self):
        self.user.is_seller = True
        self.user.save()
        self.client.login(username='sellertest', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_pending_request_shows_status(self):
        SellerRequest.objects.create(
            user=self.user, business_name='Shop', description='desc', phone_number='123'
        )
        self.client.login(username='sellertest', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('pending_request', response.context)
