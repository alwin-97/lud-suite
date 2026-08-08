from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.adapters import SocialAccountAdapter
from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location


class PlatformTestCase(TestCase):
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

    def create_cohort(self, *, start_date=date(2026, 6, 1), name="Cohort 2026"):
        location = Location.objects.create(name="Kochi")
        chapter = Chapter.objects.create(name="Central Chapter", location=location)
        cohort = Cohort.objects.create(
            name=name,
            chapter=chapter,
            start_date=start_date,
        )
        return location, chapter, cohort


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


class ConfigurationModelTests(TestCase):
    def test_cohort_end_date_is_three_years_after_start_date(self):
        location = Location.objects.create(name="Thrissur")
        chapter = Chapter.objects.create(name="City Chapter", location=location)

        cohort = Cohort.objects.create(
            name="2026 Group",
            chapter=chapter,
            start_date=date(2026, 8, 15),
        )

        self.assertEqual(cohort.end_date, date(2029, 8, 15))

    def test_leap_day_cohort_uses_february_28_end_date(self):
        location = Location.objects.create(name="Bengaluru")
        chapter = Chapter.objects.create(name="North Chapter", location=location)

        cohort = Cohort.objects.create(
            name="Leap Group",
            chapter=chapter,
            start_date=date(2024, 2, 29),
        )

        self.assertEqual(cohort.end_date, date(2027, 2, 28))

    def test_user_can_hold_multiple_roles_in_the_same_cohort(self):
        location = Location.objects.create(name="Chennai")
        chapter = Chapter.objects.create(name="East Chapter", location=location)
        cohort = Cohort.objects.create(
            name="2026 Group",
            chapter=chapter,
            start_date=date(2026, 1, 1),
        )
        user = CustomUser.objects.create_user(
            username="multi@example.com",
            email="multi@example.com",
        )

        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.COMMUNITY_LEADER,
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTOR,
        )

        self.assertEqual(user.cohort_memberships.count(), 2)
        self.assertTrue(user.is_authorized_user)


class AdminConfigurationViewTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_admin_can_create_location_chapter_and_cohort(self):
        self.client.post(reverse("location_create"), {"name": "Delhi", "is_active": "on"})
        location = Location.objects.get(name="Delhi")

        self.client.post(
            reverse("chapter_create"),
            {"name": "Delhi Central", "location": location.pk, "is_active": "on"},
        )
        chapter = Chapter.objects.get(name="Delhi Central")

        response = self.client.post(
            reverse("cohort_create"),
            {
                "name": "Cohort 2027",
                "chapter": chapter.pk,
                "start_date": "2027-04-01",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("cohort_list"))
        cohort = Cohort.objects.get(name="Cohort 2027")
        self.assertEqual(cohort.end_date, date(2030, 4, 1))

    def test_admin_configuration_pages_render(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="listed@example.com",
            email="listed@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTEE,
        )

        urls = (
            reverse("configuration_home"),
            reverse("location_list"),
            reverse("location_create"),
            reverse("chapter_list"),
            reverse("chapter_create"),
            reverse("cohort_list"),
            reverse("cohort_create"),
            reverse("platform_user_list"),
            reverse("platform_user_create"),
            reverse("platform_user_edit", args=[user.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_location_in_use_cannot_be_deleted(self):
        location, _, _ = self.create_cohort()

        response = self.client.post(
            reverse("location_delete", args=[location.pk]),
            follow=True,
        )

        self.assertContains(response, "Deactivate it instead")
        self.assertTrue(Location.objects.filter(pk=location.pk).exists())

    def test_non_admin_cannot_access_configuration(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="user@example.com",
            email="user@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTEE,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("configuration_home"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_provision_user_with_multiple_roles(self):
        _, _, cohort = self.create_cohort()

        response = self.client.post(
            reverse("platform_user_create"),
            {
                "first_name": "Asha",
                "last_name": "Nair",
                "email": "ASHA@example.com",
                "is_active": "on",
                "assignments": [
                    f"{cohort.pk}:{CohortMembership.COMMUNITY_LEADER}",
                    f"{cohort.pk}:{CohortMembership.MENTOR}",
                ],
            },
        )

        self.assertRedirects(response, reverse("platform_user_list"))
        user = CustomUser.objects.get(email="asha@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(
            set(user.cohort_memberships.values_list("role", flat=True)),
            {CohortMembership.COMMUNITY_LEADER, CohortMembership.MENTOR},
        )
        self.assertTrue(user.is_authorized_user)

    def test_editing_user_replaces_role_assignments(self):
        _, _, cohort = self.create_cohort()
        user = CustomUser.objects.create_user(
            username="person@example.com",
            email="person@example.com",
        )
        CohortMembership.objects.create(
            user=user,
            cohort=cohort,
            role=CohortMembership.MENTEE,
        )

        response = self.client.post(
            reverse("platform_user_edit", args=[user.pk]),
            {
                "first_name": "Person",
                "last_name": "One",
                "email": user.email,
                "is_active": "on",
                "assignments": [f"{cohort.pk}:{CohortMembership.MENTOR}"],
            },
        )

        self.assertRedirects(response, reverse("platform_user_list"))
        self.assertEqual(
            list(user.cohort_memberships.values_list("role", flat=True)),
            [CohortMembership.MENTOR],
        )
