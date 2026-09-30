from datetime import date

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.test import TestCase

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

    def create_member(self, email="member@example.com", role=CohortMembership.MENTEE, cohort=None):
        if cohort is None:
            cohort = Cohort.objects.first() or self.create_cohort()[2]
        user = CustomUser.objects.create_user(username=email, email=email)
        CohortMembership.objects.create(user=user, cohort=cohort, role=role)
        return user
