from datetime import date

from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location, Program


class ConfigurationModelTests(TestCase):
    def setUp(self):
        self.program, _ = Program.objects.get_or_create(
            name="DREAMS", defaults={"duration_months": 36}
        )

    def make_cohort(self, program, start_date, location_name="Pune"):
        location = Location.objects.create(name=location_name, program=program)
        chapter = Chapter.objects.create(name="Chapter", location=location)
        return Cohort.objects.create(name="Group", chapter=chapter, start_date=start_date)

    def test_cohort_end_date_follows_program_duration(self):
        short = Program.objects.create(name="Short Course", duration_months=6)

        cohort = self.make_cohort(short, date(2026, 8, 31))

        self.assertEqual(cohort.end_date, date(2027, 2, 28))

    def test_explicit_end_date_is_kept_when_program_duration_changes(self):
        calculated = self.make_cohort(self.program, date(2026, 8, 15), "Pune")
        custom = self.make_cohort(self.program, date(2026, 8, 15), "Goa")
        custom.end_date = date(2027, 1, 31)
        custom.save()

        self.program.duration_months = 24
        self.program.save()

        calculated.refresh_from_db()
        custom.refresh_from_db()
        self.assertEqual(calculated.end_date, date(2028, 8, 15))
        self.assertEqual(custom.end_date, date(2027, 1, 31))

    def test_changing_program_duration_recalculates_cohort_end_dates(self):
        cohort = self.make_cohort(self.program, date(2026, 8, 15))

        self.program.duration_months = 24
        self.program.save()

        cohort.refresh_from_db()
        self.assertEqual(cohort.end_date, date(2028, 8, 15))

    def test_location_names_are_unique_per_program_only(self):
        other = Program.objects.create(name="Other")
        Location.objects.create(name="Lavasa", program=self.program)
        Location.objects.create(name="Lavasa", program=other)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Location.objects.create(name="Lavasa", program=self.program)

    def test_membership_in_inactive_program_is_not_authorized(self):
        cohort = self.make_cohort(self.program, date(2026, 1, 1))
        user = CustomUser.objects.create_user(username="m@example.com", email="m@example.com")
        CohortMembership.objects.create(user=user, cohort=cohort, role=CohortMembership.MENTEE)
        self.assertTrue(user.is_authorized_user)

        self.program.is_active = False
        self.program.save()

        self.assertFalse(user.is_authorized_user)
    def test_cohort_end_date_is_three_years_after_start_date(self):
        location = Location.objects.create(name="Thrissur", program=self.program)
        chapter = Chapter.objects.create(name="City Chapter", location=location)

        cohort = Cohort.objects.create(
            name="2026 Group",
            chapter=chapter,
            start_date=date(2026, 8, 15),
        )

        self.assertEqual(cohort.end_date, date(2029, 8, 15))

    def test_leap_day_cohort_uses_february_28_end_date(self):
        location = Location.objects.create(name="Bengaluru", program=self.program)
        chapter = Chapter.objects.create(name="North Chapter", location=location)

        cohort = Cohort.objects.create(
            name="Leap Group",
            chapter=chapter,
            start_date=date(2024, 2, 29),
        )

        self.assertEqual(cohort.end_date, date(2027, 2, 28))

    def test_user_can_hold_multiple_roles_in_the_same_cohort(self):
        location = Location.objects.create(name="Chennai", program=self.program)
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
