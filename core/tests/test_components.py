from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse

from core.tests.base import PlatformTestCase


def render(source, **context):
    return Template("{% load ui %}" + source).render(Context(context))


class UiTagTests(SimpleTestCase):
    def test_page_header_without_actions_is_not_split(self):
        html = render('{% page_header title="Locations" eyebrow="Configuration" %}  {% endpage_header %}')
        self.assertInHTML(
            '<section class="page-heading"><div><p class="eyebrow">Configuration</p>'
            "<h1>Locations</h1></div></section>",
            html,
        )

    def test_page_header_with_actions_is_split(self):
        html = render(
            '{% page_header title="Locations" description="Manage." %}'
            '<a class="button" href="/x/">Add</a>{% endpage_header %}'
        )
        self.assertIn("page-heading page-heading--split", html)
        self.assertInHTML(
            '<div class="page-heading-actions"><a class="button" href="/x/">Add</a></div>', html
        )
        self.assertInHTML("<p>Manage.</p>", html)

    def test_page_header_escapes_text_arguments(self):
        html = render("{% page_header title=name %}{% endpage_header %}", name="<b>x</b>")
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)

    def test_status_badge(self):
        self.assertInHTML(
            '<span class="status-badge status-badge--active">Active</span>',
            render("{% status_badge True %}"),
        )
        self.assertInHTML(
            '<span class="status-badge">Disabled</span>',
            render('{% status_badge False off="Disabled" %}'),
        )

    def test_row_actions_with_delete_uses_data_confirm_and_csrf(self):
        html = render(
            '{% row_actions "/edit/" "/delete/" confirm="Delete this?" %}', csrf_token="tok"
        )
        self.assertIn('<td class="table-actions">', html)
        self.assertIn('data-confirm="Delete this?"', html)
        self.assertIn('name="csrfmiddlewaretoken" value="tok"', html)
        self.assertNotIn("onsubmit", html)

    def test_row_actions_edit_only(self):
        html = render('{% row_actions "/edit/" edit_label="Edit access" %}')
        self.assertIn("Edit access", html)
        self.assertNotIn("<form", html)

    def test_data_table_wraps_content(self):
        html = render(
            '{% data_table id="t" empty="Nothing here." %}<thead><tr><th>A</th></tr></thead>{% enddata_table %}'
        )
        self.assertInHTML(
            '<div class="table-card"><table id="t" class="data-table" data-empty-message="Nothing here.">'
            "<thead><tr><th>A</th></tr></thead></table></div>",
            html,
        )

    def test_status_card(self):
        html = render(
            '{% status_card code="404" title="Page Not Found" icon="search" action_url="/" action_label="Home" %}'
            "<p>Gone.</p>{% endstatus_card %}"
        )
        self.assertIn('<div class="status-code">404</div>', html)
        self.assertIn("fi-rr-search", html)
        self.assertInHTML("<p>Gone.</p>", html)


class StandalonePageTests(SimpleTestCase):
    def test_error_pages_render_without_request_context(self):
        for name, text in (("403.html", "403"), ("404.html", "404"), ("500.html", "500")):
            with self.subTest(template=name):
                html = render_to_string(name)
                self.assertIn(f'<div class="status-code">{text}</div>', html)
                self.assertIn("css/pages/status.css", html)


class AssetLoadingTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_datatables_only_on_list_pages(self):
        self.assertNotContains(self.client.get(reverse("admin_dashboard")), "dataTables.min.js")
        self.assertNotContains(self.client.get(reverse("location_create")), "dataTables.min.js")
        for name in ("location_list", "chapter_list", "cohort_list", "platform_user_list"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, "dataTables.min.js")
                self.assertContains(response, "js/components/data-table.js")
                self.assertContains(response, 'class="data-table"')

    def test_templates_have_no_inline_handlers_styles_or_svg(self):
        from pathlib import Path

        from django.conf import settings

        for path in (Path(settings.BASE_DIR) / "templates").rglob("*.html"):
            source = path.read_text()
            with self.subTest(template=str(path)):
                for forbidden in ("<svg", "<style", "onsubmit=", "onclick=", ' style="'):
                    self.assertNotIn(forbidden, source)


class FormRenderingTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_configuration_form_field_groups(self):
        html = self.client.get(reverse("location_create")).content.decode()
        self.assertIn('<h1>Add location</h1>', html)
        self.assertIn('class="form-field form-field--checkbox"', html)
        self.assertIn('class="form-control"', html)
        self.assertIn('href="%s"' % reverse("location_list"), html)

    def test_invalid_post_shows_field_errors(self):
        response = self.client.post(reverse("location_create"), {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span class="field-error">This field is required.</span>', html=True)

    def test_user_form_uses_grid_and_full_width_assignments(self):
        self.create_cohort()
        html = self.client.get(reverse("platform_user_create")).content.decode()
        self.assertIn("form-card form-card--wide", html)
        self.assertIn('<div class="form-grid">', html)
        self.assertIn("form-field form-field--full assignment-field", html)
        self.assertIn('class="assignment-grid"', html)
        self.assertIn("Save user", html)
