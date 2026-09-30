from datetime import date

from django.test import TestCase

from core.models import Chapter, Cohort, CohortMembership, CustomUser, Location


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
