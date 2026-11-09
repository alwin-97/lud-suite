from django.urls import reverse
from django.db import IntegrityError, transaction

from core.models import Chapter, ChangeHistory, Cohort, CohortMembership, CustomUser, Location, Program, ScopeMembership
from core.tests.base import PlatformTestCase


class ResourceMembershipTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.location, self.chapter, self.cohort = self.create_cohort()
        self.person = CustomUser.objects.create_user(username="existing@example.com", email="existing@example.com")

    def resources(self):
        return (
            ("program", Program, {"name": "New program"}),
            ("location", Location, {"name": "New location", "program": self.location.program_id}),
            ("chapter", Chapter, {"name": "New chapter", "location": self.location.pk}),
            ("cohort", Cohort, {"name": "New cohort", "chapter": self.chapter.pk, "start_date": "2027-01-01"}),
        )

    def member_data(self, **kwargs):
        return {"members_present": "1", "members-role": CohortMembership.MENTEE, **kwargs}

    def test_create_each_resource_with_existing_and_new_people(self):
        for name, model, fields in self.resources():
            with self.subTest(resource=name):
                data = {**fields, "is_active": "on", **self.member_data(**{
                    "members-users": [self.person.pk],
                    "members-new_people": f"{name}@example.com, Asha, Nair",
                })}
                response = self.client.post(reverse(f"{name}_create"), data, HTTP_X_FORM_DRAWER="true")
                self.assertEqual(response.json(), {"saved": True})
                scope = model.objects.get(name=fields["name"])
                self.assertEqual(scope.memberships.count(), 2)
                new_user = CustomUser.objects.get(email=f"{name}@example.com")
                self.assertFalse(new_user.has_usable_password())
                self.assertEqual(new_user.first_name, "Asha")
                self.assertTrue(new_user.is_authorized_user)
                history = ChangeHistory.objects.filter(entity_type="Member", details__scope_type=name, details__scope_id=scope.pk)
                self.assertEqual(history.count(), 2)
                self.assertTrue(all(change.actor == self.admin for change in history))
                edit = self.client.get(reverse(f"{name}_edit", args=[scope.pk]), HTTP_X_FORM_DRAWER="true")
                self.assertContains(edit, "existing@example.com")
                self.assertContains(edit, "Recent membership changes")

    def test_leave_and_rejoin_preserves_same_row_for_all_resources(self):
        for name, model, fields in self.resources():
            data = {**fields, "is_active": "on", **self.member_data(**{"members-users": [self.person.pk]})}
            self.client.post(reverse(f"{name}_create"), data)
            scope = model.objects.get(name=fields["name"])
            membership = scope.memberships.get(user=self.person)
            url = reverse(f"{name}_edit", args=[scope.pk])
            # Leaving retains both the row and join date.
            joined = membership.created_at
            update = {**fields, "is_active": "on", **self.member_data()}
            self.client.post(url, update)
            membership.refresh_from_db()
            self.assertFalse(membership.is_active)
            self.client.post(url, {**update, "members-users": [self.person.pk]})
            membership.refresh_from_db()
            self.assertTrue(membership.is_active)
            self.assertEqual(membership.created_at, joined)
            self.assertEqual(scope.memberships.count(), 1)
            actions = list(ChangeHistory.objects.filter(entity_type="Member", details__scope_type=name,
                                                       details__scope_id=scope.pk).order_by("created_at").values_list("action", flat=True))
            self.assertEqual(actions, ["allocate", "deactivate", "activate"])

    def test_invalid_new_people_saves_neither_resource_nor_users(self):
        for text in ("invalid-email", "new@example.com\nNEW@example.com", "existing@example.com", "new@example.com, " + "x" * 151):
            with self.subTest(text=text):
                response = self.client.post(reverse("program_create"), {
                    "name": "Invalid", **self.member_data(**{"members-new_people": text}),
                }, HTTP_X_FORM_DRAWER="true")
                self.assertEqual(response.status_code, 200)
                self.assertIn("new_people", response.context["members_form"].errors)
                self.assertFalse(Program.objects.filter(name="Invalid").exists())
                self.assertFalse(CustomUser.objects.filter(email="new@example.com").exists())

    def test_invalid_resource_retains_member_input(self):
        response = self.client.post(reverse("cohort_create"), self.member_data(**{
            "members-users": [self.person.pk], "members-new_people": "new@example.com, New, Person",
        }), HTTP_X_FORM_DRAWER="true")
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "new@example.com, New, Person")
        self.assertFalse(CustomUser.objects.filter(email="new@example.com").exists())

    def test_inactive_accounts_require_explicit_reactivation(self):
        self.person.is_active = False
        self.person.save()
        url = reverse("program_create")
        data = {"name": "Inactive member", "is_active": "on", **self.member_data(**{"members-users": [self.person.pk]})}
        self.client.post(url, data)
        self.person.refresh_from_db()
        self.assertFalse(self.person.is_authorized_user)
        program = Program.objects.get(name="Inactive member")
        self.client.post(reverse("program_edit", args=[program.pk]), {**data, "members-reactivate_accounts": "on"})
        self.person.refresh_from_db()
        self.assertTrue(self.person.is_active)
        self.assertTrue(self.person.is_authorized_user)
        self.assertTrue(ChangeHistory.objects.filter(entity_type="User", action="activate", entity_id=self.person.pk).exists())

    def test_cannot_change_another_resources_membership(self):
        membership = ScopeMembership.objects.create(user=self.person, program=self.location.program, role="mentee")
        response = self.client.post(reverse("location_edit", args=[self.location.pk]), {
            "name": self.location.name, "program": self.location.program_id,
            **self.member_data(**{"members-active_memberships": [membership.pk]}),
        })
        self.assertIn("active_memberships", response.context["members_form"].errors)
        membership.refresh_from_db()
        self.assertTrue(membership.is_active)

    def test_membership_needs_exactly_one_scope(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScopeMembership.objects.create(user=self.person, role="mentee")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScopeMembership.objects.create(user=self.person, role="mentee", program=self.location.program, location=self.location)

    def test_parent_membership_does_not_grant_cohort_permissions(self):
        from core.permissions import has_role_permission
        ScopeMembership.objects.create(user=self.person, program=self.location.program, role="community_leader")
        self.assertTrue(self.person.is_authorized_user)
        self.assertFalse(has_role_permission(self.person, "members", "create", cohort=self.cohort))
        self.client.force_login(self.person)
        self.assertEqual(self.client.get(reverse("program_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("workspace_home")).status_code, 200)

    def test_user_account_changes_are_audited_without_losing_memberships(self):
        membership = CohortMembership.objects.create(user=self.person, cohort=self.cohort, role="mentee")
        data = {"first_name": "Updated", "last_name": "Name", "email": self.person.email,
                "assignments": [f"{self.cohort.pk}:mentee"]}
        url = reverse("platform_user_edit", args=[self.person.pk])
        self.client.post(url, data)
        self.person.refresh_from_db()
        membership.refresh_from_db()
        self.assertFalse(self.person.is_active)
        self.assertTrue(membership.is_active)
        event = ChangeHistory.objects.filter(entity_type="User", action="deactivate", entity_id=self.person.pk).first()
        self.assertEqual(event.details["changes"]["is_active"], {"before": True, "after": False})
        self.client.post(url, {**data, "is_active": "on"})
        self.person.refresh_from_db()
        self.assertTrue(self.person.is_authorized_user)
        self.assertEqual(self.person.cohort_memberships.get().pk, membership.pk)

    def test_inactive_membership_is_not_reactivated_by_saving_user_details(self):
        membership = CohortMembership.objects.create(user=self.person, cohort=self.cohort, role="mentee", is_active=False)
        url = reverse("platform_user_edit", args=[self.person.pk])
        response = self.client.get(url)
        self.assertEqual(response.context["form"].initial["assignments"], [])
        self.client.post(url, {"first_name": "New", "email": self.person.email, "is_active": "on"})
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)

    def test_parent_deactivation_blocks_scope_only_access(self):
        ScopeMembership.objects.create(user=self.person, chapter=self.chapter, role="mentee")
        self.assertTrue(self.person.is_authorized_user)
        for scope in (self.location.program, self.location, self.chapter):
            scope.is_active = False
            scope.save()
            self.assertFalse(self.person.is_authorized_user)
            scope.is_active = True
            scope.save()
            self.assertTrue(self.person.is_authorized_user)

    def test_user_history_stays_linked_after_email_changes(self):
        self.client.post(reverse("program_create"), {
            "name": "History program", "is_active": "on",
            **self.member_data(**{"members-users": [self.person.pk]}),
        })
        self.client.post(reverse("platform_user_edit", args=[self.person.pk]), {
            "email": "changed@example.com", "first_name": "Updated", "is_active": "on",
        })
        response = self.client.get(reverse("audit_log"), {"user": self.person.pk})
        self.assertContains(response, f'name="user" value="{self.person.pk}"')
        self.assertContains(response, "History program")
        self.assertContains(response, "changed@example.com")
        self.assertTrue(all(change.details.get("user_id") == self.person.pk or
                            (change.entity_type == "User" and change.entity_id == self.person.pk)
                            for change in response.context["history_entries"]))
