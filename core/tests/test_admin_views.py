from datetime import date

from django.urls import reverse

from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location
from core.tests.base import PlatformTestCase


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
