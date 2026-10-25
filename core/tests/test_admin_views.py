from datetime import date

from django.urls import reverse

from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location, Program
from core.tests.base import PlatformTestCase


class AdminConfigurationViewTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_admin_can_create_location_chapter_and_cohort(self):
        self.client.post(
            reverse("program_create"),
            {"name": "Summer School", "duration_months": 12, "is_active": "on"},
        )
        program = Program.objects.get(name="Summer School")
        self.assertEqual(program.duration_months, 12)

        self.client.post(
            reverse("location_create"),
            {"name": "Delhi", "program": program.pk, "is_active": "on"},
        )
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
        self.assertEqual(cohort.end_date, date(2028, 4, 1))
        self.assertEqual(cohort.program, program)

    def test_cohort_accepts_explicit_end_date_and_rejects_earlier_one(self):
        _, chapter, _ = self.create_cohort()
        data = {"name": "Short", "chapter": chapter.pk, "start_date": "2027-04-01", "is_active": "on"}

        bad = self.client.post(reverse("cohort_create"), {**data, "end_date": "2027-03-01"})
        self.assertContains(bad, "must be after the start date")

        self.client.post(reverse("cohort_create"), {**data, "end_date": "2027-10-01"})
        self.assertEqual(Cohort.objects.get(name="Short").end_date, date(2027, 10, 1))

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
            reverse("program_list"),
            reverse("program_create"),
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

    def test_program_with_locations_cannot_be_deleted(self):
        location, _, _ = self.create_cohort()

        response = self.client.post(
            reverse("program_delete", args=[location.program.pk]),
            follow=True,
        )

        self.assertContains(response, "Deactivate it instead")
        self.assertTrue(Program.objects.filter(pk=location.program.pk).exists())

    def test_list_pages_expose_program_filter(self):
        self.create_cohort()
        for name in ("location_list", "chapter_list", "cohort_list", "platform_user_list"):
            with self.subTest(page=name):
                self.assertContains(self.client.get(reverse(name)), "Program")

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

    def test_admin_cannot_provision_user_with_overlong_email(self):
        _, _, cohort = self.create_cohort()
        overlong_email = f"{'a' * 145}@example.com"  # 157 characters

        response = self.client.post(
            reverse("platform_user_create"),
            {
                "first_name": "Test",
                "last_name": "Long",
                "email": overlong_email,
                "is_active": "on",
                "assignments": [f"{cohort.pk}:{CohortMembership.MENTEE}"],
            },
        )
        self.assertContains(response, "Email address cannot exceed 150 characters.")
        self.assertFalse(CustomUser.objects.filter(email=overlong_email).exists())

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


class CohortManageTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        _, _, self.cohort = self.create_cohort()
        self.person = CustomUser.objects.create_user(
            username="p@example.com", email="p@example.com", first_name="Pat"
        )

    def manage_url(self):
        return reverse("cohort_manage", args=[self.cohort.pk])

    def test_manage_page_lists_members_and_is_linked_from_cohort_list(self):
        self.create_member("member@example.com", cohort=self.cohort)
        self.assertContains(self.client.get(self.manage_url()), "member@example.com")
        self.assertContains(self.client.get(reverse("cohort_list")), self.manage_url())

    def test_admin_can_add_member_and_duplicate_is_rejected(self):
        data = {"user": self.person.pk, "role": CohortMembership.MENTOR}
        self.assertRedirects(self.client.post(self.manage_url(), data), self.manage_url())
        self.assertTrue(self.person.is_authorized_user)

        response = self.client.post(self.manage_url(), data)
        self.assertContains(response, "already a Mentor")
        self.assertEqual(self.cohort.memberships.count(), 1)

    def test_toggle_and_remove_membership(self):
        membership = CohortMembership.objects.create(
            user=self.person, cohort=self.cohort, role=CohortMembership.MENTEE
        )
        self.client.post(reverse("cohort_member_toggle", args=[self.cohort.pk, membership.pk]))
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)

        # Adding the same role again reactivates it instead of duplicating.
        self.client.post(self.manage_url(), {"user": self.person.pk, "role": CohortMembership.MENTEE})
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)

        self.client.post(reverse("cohort_member_remove", args=[self.cohort.pk, membership.pk]))
        self.assertFalse(CohortMembership.objects.filter(pk=membership.pk).exists())

    def test_membership_of_another_cohort_cannot_be_changed(self):
        other = Cohort.objects.create(
            name="Other", chapter=self.cohort.chapter, start_date=date(2026, 7, 1)
        )
        membership = CohortMembership.objects.create(
            user=self.person, cohort=other, role=CohortMembership.MENTEE
        )
        response = self.client.post(
            reverse("cohort_member_remove", args=[self.cohort.pk, membership.pk])
        )
        self.assertEqual(response.status_code, 404)


class CohortMemberSelectTests(PlatformTestCase):
    def test_user_options_are_grouped_by_location_link(self):
        self.client.force_login(self.admin)
        _, _, cohort = self.create_cohort()
        linked = self.create_member("linked@example.com", cohort=cohort)
        stranger = CustomUser.objects.create_user(username="s@example.com", email="s@example.com")

        html = self.client.get(reverse("cohort_manage", args=[cohort.pk])).content.decode()

        self.assertIn('data-group="Linked to Kochi"', html)
        self.assertIn("linked@example.com", html)
        self.assertIn('data-group="Other users"', html)
        self.assertLess(html.index("linked@example.com"), html.index("s@example.com"))
        self.assertIn("Already in this cohort: Mentee", html)


class UserAssignmentOptionsTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_only_active_program_location_cohorts_are_offered(self):
        _, _, active = self.create_cohort()
        inactive_program = self.create_program("Retired", 12)
        inactive_program.is_active = False
        inactive_program.save()
        location = Location.objects.create(name="Hidden", program=inactive_program)
        chapter = Chapter.objects.create(name="Hidden Chapter", location=location)
        hidden = Cohort.objects.create(name="Hidden Cohort", chapter=chapter, start_date=date(2026, 1, 1))

        html = self.client.get(reverse("platform_user_create")).content.decode()

        self.assertIn(f'value="{active.pk}:mentee"', html)
        self.assertNotIn(f'value="{hidden.pk}:mentee"', html)
        self.assertIn('<option value="DREAMS">DREAMS</option>', html)

    def test_existing_assignment_stays_listed_when_its_program_is_inactive(self):
        _, _, cohort = self.create_cohort()
        user = self.create_member("kept@example.com", cohort=cohort)
        cohort.chapter.location.program.is_active = False
        cohort.chapter.location.program.save()

        html = self.client.get(reverse("platform_user_edit", args=[user.pk])).content.decode()

        self.assertIn(f'value="{cohort.pk}:mentee" checked', html)
