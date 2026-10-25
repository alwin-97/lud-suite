from types import SimpleNamespace
from unittest.mock import Mock

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse

from core.adapters import SocialAccountAdapter
from core.models import CohortMembership, CustomUser
from core.permissions import check_access
from core.tests.base import PlatformTestCase


class AdminAuthenticationTests(PlatformTestCase):
    def test_login_page_makes_google_the_primary_option(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, "Recommended sign-in")
        self.assertContains(response, "Signin with Username &amp; Password")

        html = response.content.decode()
        self.assertLess(html.index("Continue with Google"), html.index("login-form"))

    def test_login_page_works_before_google_is_configured(self):
        self.google_app.delete()

        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Continue with Google")
        self.assertContains(response, "Google sign-in has not been configured yet")

    def test_admin_can_sign_in_with_password(self):
        response = self.client.post(
            reverse("login"),
            {"email": "admin@example.com", "password": "testpass123"},
        )

        self.assertRedirects(response, reverse("admin_dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)

    def test_invalid_credentials_reopen_password_fallback(self):
        response = self.client.post(
            reverse("login"),
            {"email": "admin@example.com", "password": "incorrect"},
            follow=True,
        )

        self.assertContains(response, "Invalid email or password.")
        self.assertEqual(response.request["QUERY_STRING"], "method=password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('admin_dashboard')}",
        )

    def test_provisioned_user_reaches_workspace(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="leader@example.com",
            email="leader@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.COMMUNITY_LEADER,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("role-redirect"))

        self.assertRedirects(response, reverse("workspace_home"))

    def test_platform_user_cannot_use_password_fallback(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="mentor@example.com",
            email="mentor@example.com",
            password="testpass123",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTOR,
        )

        response = self.client.post(
            reverse("login"),
            {"email": user.email, "password": "testpass123"},
            follow=True,
        )

        self.assertContains(response, "must sign in with Google")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unprovisioned_user_is_not_authorized(self):
        user = CustomUser.objects.create_user(
            username="unknown@example.com",
            email="unknown@example.com",
        )

        self.assertFalse(user.is_authorized_user)

    def test_inactive_location_revokes_user_access(self):
        location, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="inactive-location@example.com",
            email="inactive-location@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTEE,
        )
        location.is_active = False
        location.save(update_fields=["is_active"])

        self.assertFalse(user.is_authorized_user)

    def test_google_adapter_accepts_only_provisioned_email(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="mentee@example.com",
            email="mentee@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTEE,
        )
        sociallogin = SimpleNamespace(
            is_existing=False,
            account=SimpleNamespace(extra_data={"email": user.email}),
            user=SimpleNamespace(email=user.email),
            connect=Mock(),
        )

        SocialAccountAdapter().pre_social_login(RequestFactory().get("/"), sociallogin)

        sociallogin.connect.assert_called_once()

        unknown_login = SimpleNamespace(
            is_existing=False,
            account=SimpleNamespace(extra_data={"email": "unknown@example.com"}),
            user=SimpleNamespace(email="unknown@example.com"),
            connect=Mock(),
        )
        with self.assertRaises(PermissionDenied):
            SocialAccountAdapter().pre_social_login(
                RequestFactory().get("/"),
                unknown_login,
            )

    def test_role_check_access_with_required_roles(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="mentor@example.com",
            email="mentor@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTOR,
        )
        request = RequestFactory().get("/")
        request.user = user

        # Allowed when holding the required role
        self.assertIsNone(
            check_access(request, required_roles=[CohortMembership.MENTOR])
        )
        # Denied when not holding the required role
        with self.assertRaises(PermissionDenied):
            check_access(request, required_roles=[CohortMembership.COMMUNITY_LEADER])
