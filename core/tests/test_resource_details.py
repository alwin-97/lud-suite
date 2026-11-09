from django.urls import reverse

from core.models import ChangeHistory, CustomUser, Program, Term, log_change
from core.services.memberships import add_membership
from core.tests.base import PlatformTestCase


class ConfigurationDetailTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.location, self.chapter, self.cohort = self.create_cohort()
        self.program = self.location.program

    def resources(self):
        return (("program", self.program), ("location", self.location),
                ("chapter", self.chapter), ("cohort", self.cohort))

    def test_detail_pages_and_view_links(self):
        for kind, obj in self.resources():
            with self.subTest(kind=kind):
                url = reverse(f"{kind}_detail", args=[obj.pk])
                self.assertContains(self.client.get(reverse(f"{kind}_list")), url)
                response = self.client.get(url)
                self.assertContains(response, obj.name)
                self.assertContains(response, "Audit logs and changes")
                self.assertContains(response, reverse(f"{kind}_edit", args=[obj.pk]))
                self.assertEqual(response.context["resource"], obj)
                self.assertEqual(self.client.get(reverse(f"{kind}_detail", args=[999999])).status_code, 404)

    def test_details_require_administrator(self):
        self.client.logout()
        for kind, obj in self.resources():
            self.assertEqual(self.client.get(reverse(f"{kind}_detail", args=[obj.pk])).status_code, 302)
        member = self.create_member(cohort=self.cohort)
        self.client.force_login(member)
        for kind, obj in self.resources():
            self.assertEqual(self.client.get(reverse(f"{kind}_detail", args=[obj.pk])).status_code, 403)

    def test_hierarchy_members_and_cohort_curriculum_are_visible(self):
        person = CustomUser.objects.create_user(username="person@example.com", email="person@example.com")
        add_membership(self.program, person, "mentor", self.admin)
        cohort_member = add_membership(self.cohort, person, "mentee", self.admin)
        cohort_member.is_active = False
        cohort_member.save()
        term = Term.objects.create(cohort=self.cohort, name="Discovery", sequence=1)
        program_response = self.client.get(reverse("program_detail", args=[self.program.pk]))
        self.assertEqual(len(program_response.context["members"]), 2)
        self.assertContains(program_response, "Left / inactive")
        for kind, obj in self.resources()[1:]:
            self.assertContains(program_response, reverse(f"{kind}_detail", args=[obj.pk]))
        response = self.client.get(reverse("cohort_detail", args=[self.cohort.pk]))
        self.assertContains(response, reverse("cohort_term_detail", args=[self.cohort.pk, term.pk]))
        self.assertContains(response, "Discovery")
        self.assertNotContains(response, f"Program · {self.program.name}</a></td>")

    def test_audit_is_scoped_by_id_and_includes_descendant_activity(self):
        log_change(self.admin, "update", "Program", self.program.name, "Program change",
                   entity_id=self.program.pk)
        log_change(self.admin, "update", "Term", "Discovery", "Descendant term change", cohort=self.cohort)
        other = Program.objects.create(name="Other")
        log_change(self.admin, "update", "Program", self.program.name, "Unrelated same-name log", entity_id=other.pk)
        for kind, obj in self.resources():
            response = self.client.get(reverse(f"{kind}_detail", args=[obj.pk]))
            self.assertContains(response, "Descendant term change")
            self.assertNotContains(response, "Unrelated same-name log")
        self.assertContains(self.client.get(reverse("program_detail", args=[self.program.pk])), "Program change")

    def test_configuration_updates_record_before_and_after_values(self):
        self.client.post(reverse("cohort_edit", args=[self.cohort.pk]), {
            "name": "Renamed", "chapter": self.chapter.pk, "start_date": "2026-06-01",
            "end_date": "2027-06-01", "description": "New description", "is_active": "on",
        })
        event = ChangeHistory.objects.filter(entity_type="Cohort", entity_id=self.cohort.pk, action="update").latest("pk")
        self.assertEqual(event.details["changes"]["name"], {"before": "Cohort 2026", "after": "Renamed"})
        self.assertEqual(event.details["changes"]["end_date"]["after"], "2027-06-01")
        self.assertEqual(event.details["scope_ids"]["program"], self.program.pk)
        response = self.client.get(reverse("cohort_detail", args=[self.cohort.pk]))
        self.assertContains(response, "Before")
        self.assertContains(response, "New description")

    def test_move_is_visible_in_old_and_new_parent_history(self):
        other = Program.objects.create(name="New parent")
        self.client.post(reverse("location_edit", args=[self.location.pk]), {
            "name": self.location.name, "program": other.pk, "is_active": "on",
        })
        event = ChangeHistory.objects.filter(entity_type="Location", entity_id=self.location.pk).latest("pk")
        self.assertEqual(event.details["changes"]["program"], {"before": self.program.pk, "after": other.pk})
        for parent in (self.program, other):
            response = self.client.get(reverse("program_detail", args=[parent.pk]))
            self.assertIn(event, response.context["history_page"].object_list)

    def test_cohort_deletion_retains_history_in_parent_detail(self):
        event = log_change(self.admin, "update", "Term", "Discovery", "Preserved activity history", cohort=self.cohort)
        cohort_id = self.cohort.pk
        self.client.post(reverse("cohort_delete", args=[cohort_id]))
        event.refresh_from_db()
        self.assertIsNone(event.cohort_id)
        for kind, obj in self.resources()[:3]:
            self.assertContains(self.client.get(reverse(f"{kind}_detail", args=[obj.pk])), "Preserved activity history")
        deletion = ChangeHistory.objects.get(entity_type="Cohort", entity_id=cohort_id, action="delete")
        self.assertEqual(deletion.details["scope_ids"]["program"], self.program.pk)

    def test_audit_pagination_and_filters(self):
        ChangeHistory.objects.bulk_create([
            ChangeHistory(actor=self.admin, action="update", entity_type="Program", entity_id=self.program.pk,
                          entity_name=self.program.name, description=f"Matching change {index}")
            for index in range(30)
        ])
        url = reverse("program_detail", args=[self.program.pk])
        response = self.client.get(url, {"q": "Matching", "action": "update"})
        self.assertEqual(response.context["history_page"].paginator.count, 30)
        self.assertEqual(len(response.context["history_page"]), 25)
        self.assertContains(response, "page=2")
        self.assertContains(response, "q=Matching")
        response = self.client.get(url, {"q": "Matching", "action": "update", "page": 2})
        self.assertEqual(len(response.context["history_page"]), 5)
        self.assertEqual(self.client.get(url, {"action": "create"}).context["history_page"].paginator.count, 0)

    def test_audit_content_is_escaped(self):
        log_change(self.admin, "update", "Program", "<script>bad()</script>", "<img src=x onerror=bad()>",
                   entity_id=self.program.pk, details={"changes": {"name": {"before": "old", "after": "<script>bad()</script>"}}})
        response = self.client.get(reverse("program_detail", args=[self.program.pk]))
        self.assertNotContains(response, "<script>bad()</script>")
        self.assertContains(response, "&lt;script&gt;bad()&lt;/script&gt;")

    def test_existing_audit_records_receive_scope_identifiers(self):
        from importlib import import_module
        from django.apps import apps
        from django.db import connection
        entry = ChangeHistory.objects.create(actor=self.admin, action="update", entity_type="Term",
                                             entity_name="Legacy term", description="Legacy history", cohort=self.cohort)
        migration = import_module("core.migrations.0033_preserve_cohort_audit_history")
        migration.retain_scope_identifiers(apps, connection.schema_editor())
        entry.refresh_from_db()
        self.assertEqual(entry.details["scope_ids"], {"cohort": self.cohort.pk, "chapter": self.chapter.pk,
                                                     "location": self.location.pk, "program": self.program.pk})
        self.cohort.delete()
        entry.refresh_from_db()
        self.assertIsNone(entry.cohort_id)
        self.assertContains(self.client.get(reverse("program_detail", args=[self.program.pk])), "Legacy history")

    def test_members_and_structure_paginate_independently(self):
        from core.models import Location, ScopeMembership
        people = CustomUser.objects.bulk_create([
            CustomUser(username=f"person-{i:02}@example.com", email=f"person-{i:02}@example.com") for i in range(12)
        ])
        ScopeMembership.objects.bulk_create([ScopeMembership(user=user, program=self.program, role="mentee") for user in people])
        Location.objects.bulk_create([Location(name=f"Location {i:02}", program=self.program) for i in range(12)])
        url = reverse("program_detail", args=[self.program.pk])
        response = self.client.get(url, {"members_page": 2, "locations_page": 2, "q": "Name", "action": "update"})
        self.assertEqual(response.context["members_page"].paginator.count, 12)
        self.assertEqual(len(response.context["members_page"]), 2)
        section = next(section for section in response.context["related_sections"] if section["title"] == "Locations")
        self.assertEqual(section["rows"].number, 2)
        self.assertEqual(section["rows"].paginator.count, 13)
        self.assertContains(response, 'name="members_page" value="2"')
        self.assertContains(response, 'name="locations_page" value="2"')
        self.assertContains(response, 'aria-label="Members pagination"')
        self.assertContains(response, "Showing 11–12 of 12")
        self.assertContains(response, "q=Name")
        self.assertNotContains(response, "person-00@example.com")
        self.assertContains(response, "person-11@example.com")

    def test_cohort_sections_and_nested_resources_paginate(self):
        from core.models import CohortActivity, MentorAssignment, TermResource, TermTask, TermQuestion
        terms = [Term.objects.create(cohort=self.cohort, name=f"Term {i}", sequence=i) for i in range(1, 7)]
        term = terms[0]
        people = CustomUser.objects.bulk_create([
            CustomUser(username=f"mentor-{i}@example.com", email=f"mentor-{i}@example.com") for i in range(12)
        ])
        CohortActivity.objects.bulk_create([CohortActivity(cohort=self.cohort, term=term, title=f"Activity {i:02}") for i in range(12)])
        MentorAssignment.objects.bulk_create([MentorAssignment(cohort=self.cohort, mentor=people[0], mentee=user) for user in people[1:]])
        TermResource.objects.bulk_create([TermResource(term=term, title=f"Resource {i:02}", resource_type="link", url="https://example.com") for i in range(12)])
        TermTask.objects.bulk_create([TermTask(term=term, title=f"Task {i:02}") for i in range(12)])
        TermQuestion.objects.bulk_create([TermQuestion(term=term, title=f"Question {i:02}", prompt="Example") for i in range(12)])
        url = reverse("cohort_detail", args=[self.cohort.pk])
        response = self.client.get(url, {"terms_page": 2, "activities_page": 2, "pairings_page": 2})
        self.assertEqual(len(response.context["terms"]), 1)
        self.assertEqual(len(response.context["activities"]), 2)
        self.assertEqual(len(response.context["pairings"]), 1)
        params = {f"term_{term.pk}_{name}_page": 2 for name in ("resources", "tasks", "questions")}
        response = self.client.get(url, params)
        first = list(response.context["terms"])[0]
        for name in ("resources", "tasks", "questions"):
            self.assertEqual(len(getattr(first, f"{name}_page")), 2)
        self.assertTrue(first.extra_content_open)
        self.assertContains(response, " open>")

    def test_invalid_pagination_values_and_empty_sections_are_safe(self):
        response = self.client.get(reverse("cohort_detail", args=[self.cohort.pk]), {
            "members_page": "bad", "terms_page": -5, "activities_page": 999, "pairings_page": "NaN", "page": "bad",
        })
        self.assertEqual(response.status_code, 200)
        for name in ("members_page", "terms", "activities", "pairings", "history_page"):
            self.assertEqual(response.context[name].number, 1)
        self.assertNotContains(response, 'aria-label="Members pagination"')
