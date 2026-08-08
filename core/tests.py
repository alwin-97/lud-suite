from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.test import TestCase
from django.urls import reverse

from core.models import CustomUser


class AdminAuthenticationTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="platform-admin",
            email="admin@example.com",
            password="testpass123",
            role=CustomUser.ADMIN,
        )
        google_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="test-client-id",
            secret="test-secret",
        )
        google_app.sites.add(Site.objects.get_current())
        self.google_app = google_app

    def test_login_page_is_available(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to your account")
        self.assertContains(response, "Continue with Google")

    def test_login_page_works_before_google_is_configured(self):
        self.google_app.delete()

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Continue with Google")

    def test_admin_can_sign_in_with_email(self):
        response = self.client.post(
            reverse("login"),
            {"email": "admin@example.com", "password": "testpass123"},
        )

        self.assertRedirects(response, reverse("admin_dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)

    def test_invalid_credentials_are_rejected(self):
        response = self.client.post(
            reverse("login"),
            {"email": "admin@example.com", "password": "incorrect"},
            follow=True,
        )

        self.assertContains(response, "Invalid email or password.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('admin_dashboard')}",
        )

    def test_admin_lands_on_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Foundation ready")

    def test_non_admin_is_denied_dashboard_access(self):
        non_admin = CustomUser.objects.create_user(
            username="legacy-user",
            email="user@example.com",
            password="testpass123",
            role="mentor",
        )
        self.client.force_login(non_admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_non_admin_credentials_are_rejected(self):
        CustomUser.objects.create_user(
            username="legacy-login",
            email="legacy@example.com",
            password="testpass123",
            role="mentor",
        )

        response = self.client.post(
            reverse("login"),
            {"email": "legacy@example.com", "password": "testpass123"},
            follow=True,
        )

        self.assertContains(response, "restricted to administrators")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_ends_the_session(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
