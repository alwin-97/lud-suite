import re

from django.test import SimpleTestCase
from django.urls import reverse

from core.navigation import ADMIN_NAV, NavItem
from core.tests.base import PlatformTestCase


class NavItemTests(SimpleTestCase):
    def test_every_nav_url_name_reverses(self):
        def walk(items):
            for item in items:
                yield item
                yield from walk(item.children)

        for item in walk(ADMIN_NAV):
            with self.subTest(item=item.label):
                reverse(item.url_name)

    def test_group_is_active_when_child_matches_prefix(self):
        group = NavItem("Configuration", "configuration_home", children=(
            NavItem("Locations", "location_list", match_prefix="location_"),
        ))
        resolved = group.resolve("location_edit")
        self.assertTrue(resolved["active"])
        self.assertTrue(resolved["children"][0]["active"])
        self.assertFalse(group.resolve("admin_dashboard")["active"])


class SidebarRenderTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def active_labels(self, url):
        html = self.client.get(url).content.decode()
        return re.findall(r'class="sidebar-(?:link|sublink)[^"]*\bactive\b[^"]*"[^>]*>(?:\s*<span[^>]*>.*?</span>\s*<span class="sidebar-label">)?([^<]+)<', html, re.S), html

    def test_edit_page_opens_configuration_and_marks_locations(self):
        location, _, _ = self.create_cohort()
        labels, html = self.active_labels(reverse("location_edit", args=[location.pk]))
        self.assertIn('class="sidebar-group open"', html)
        self.assertEqual([label.strip() for label in labels], ["Configuration", "Locations"])

    def test_dashboard_marks_only_dashboard(self):
        labels, html = self.active_labels(reverse("admin_dashboard"))
        self.assertEqual([label.strip() for label in labels], ["Dashboard"])
        self.assertNotIn('class="sidebar-group open"', html)

    def test_users_pages_mark_users(self):
        labels, _ = self.active_labels(reverse("platform_user_create"))
        self.assertEqual([label.strip() for label in labels], ["Users"])
