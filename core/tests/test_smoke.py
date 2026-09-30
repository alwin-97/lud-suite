from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import reverse

from core.models import CustomUser
from core.tests.base import PlatformTestCase


class AdminAccessSmokeTests(PlatformTestCase):
    """Every admin page: admin 200, provisioned non-admin 403, anonymous -> login."""

    def admin_urls(self):
        location, chapter, cohort = self.create_cohort()
        member = self.create_member()
        return [
            reverse("admin_dashboard"),
            reverse("configuration_home"),
            reverse("location_list"),
            reverse("location_create"),
            reverse("location_edit", args=[location.pk]),
            reverse("chapter_list"),
            reverse("chapter_create"),
            reverse("chapter_edit", args=[chapter.pk]),
            reverse("cohort_list"),
            reverse("cohort_create"),
            reverse("cohort_edit", args=[cohort.pk]),
            reverse("platform_user_list"),
            reverse("platform_user_create"),
            reverse("platform_user_edit", args=[member.pk]),
        ]

    def test_admin_pages_by_role(self):
        urls = self.admin_urls()
        member = CustomUser.objects.get(email="member@example.com")

        for url in urls:
            with self.subTest(role="anonymous", url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(reverse("login")))

        self.client.force_login(member)
        for url in urls:
            with self.subTest(role="member", url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.admin)
        for url in urls:
            with self.subTest(role="admin", url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_delete_views_reject_get(self):
        location, chapter, cohort = self.create_cohort()
        self.client.force_login(self.admin)
        for name, pk in (
            ("location_delete", location.pk),
            ("chapter_delete", chapter.pk),
            ("cohort_delete", cohort.pk),
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 405)

    def test_admin_accounts_cannot_be_edited_as_platform_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("platform_user_edit", args=[self.admin.pk]))
        self.assertEqual(response.status_code, 404)


class TemplateCompileTests(SimpleTestCase):
    def test_every_template_compiles(self):
        root = Path(settings.BASE_DIR) / "templates"
        for path in sorted(root.rglob("*.html")):
            name = path.relative_to(root).as_posix()
            with self.subTest(template=name):
                get_template(name)
