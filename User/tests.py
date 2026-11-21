from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = 'TestPass123'
        self.user = CustomUser.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password=self.password,
            role='student',
        )

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse('login'),
            {'email': self.user.email, 'password': self.password},
        )

        self.assertRedirects(response, reverse('document_list'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_login_with_invalid_password(self):
        response = self.client.post(
            reverse('login'),
            {'email': self.user.email, 'password': 'WrongPass123'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email hoặc mật khẩu không đúng.')

    def test_login_with_unknown_email(self):
        response = self.client.post(
            reverse('login'),
            {'email': 'unknown@example.com', 'password': self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email hoặc mật khẩu không đúng.')

    def test_logout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_authenticated_user_can_open_account(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('account'))

        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_is_redirected_from_account(self):
        response = self.client.get(reverse('account'))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("account")}',
        )


class RBACTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='TestPass123',
            role='student',
        )
        self.moderator = CustomUser.objects.create_user(
            username='moderator@example.com',
            email='moderator@example.com',
            password='TestPass123',
            role='moderator',
        )
        self.admin = CustomUser.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='TestPass123',
            role='admin',
        )

    def test_student_cannot_open_moderator_pending_page(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('pending_documents'))

        self.assertRedirects(response, reverse('document_list'))

    def test_moderator_can_open_pending_page(self):
        self.client.force_login(self.moderator)
        response = self.client.get(reverse('pending_documents'))

        self.assertEqual(response.status_code, 200)

    def test_moderator_cannot_open_admin_user_management(self):
        self.client.force_login(self.moderator)
        response = self.client.get(reverse('user_management'))

        self.assertRedirects(response, reverse('document_list'))

    def test_admin_can_open_user_management(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('user_management'))

        self.assertEqual(response.status_code, 200)
