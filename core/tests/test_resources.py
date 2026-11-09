from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.urls import resolve, reverse

from core.models import Chapter, ChangeHistory, Cohort, CohortMembership, CustomUser, Location, Program, RolePermission, ScopeMembership, ScopeResource
from core.services.resources import ResourceAccess, add_resource, scope_key
from core.tests.base import PlatformTestCase


class ResourceLibraryTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.temp = TemporaryDirectory()
        self.settings_override = override_settings(PRIVATE_RESOURCE_ROOT=Path(self.temp.name))
        self.settings_override.enable()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.settings_override.disable)
        self.client.force_login(self.admin)
        self.location, self.chapter, self.cohort = self.create_cohort()
        self.program = self.location.program
        self.member = self.create_member(cohort=self.cohort)

    def scopes(self):
        return (self.program, self.location, self.chapter, self.cohort)

    def collection(self, scope):
        return reverse("scope_resources", args=[scope._meta.model_name, scope.pk])

    def upload(self, name="guide.pdf", content=b"Test resource content"):
        return SimpleUploadedFile(name, content, content_type="application/octet-stream")

    def test_each_level_accepts_uploads_and_is_available_to_cohort_members(self):
        for scope in self.scopes():
            with self.subTest(scope=scope):
                response = self.client.post(self.collection(scope), {"files": [self.upload()], "title": "Welcome", "description": "Guide"})
                self.assertRedirects(response, self.collection(scope))
                resource = scope.shared_resources.get()
                self.assertEqual(resource.uploaded_by, self.admin)
                self.assertEqual(resource.resource_type, "file")
                self.assertTrue(str(resource.file.path).startswith(self.temp.name))
                self.assertTrue(ChangeHistory.objects.filter(action="upload", entity_type="Resource", entity_id=resource.pk).exists())
        self.client.force_login(self.member)
        for scope in self.scopes():
            self.assertContains(self.client.get(self.collection(scope)), "Welcome")
        response = self.client.get(reverse("resource_library"))
        self.assertEqual(response.context["resource_page"].paginator.count, 4)

    def test_classifies_images_videos_and_other_files(self):
        self.client.post(self.collection(self.program), {"files": [self.upload("photo.png"), self.upload("video.mp4"), self.upload("notes.html")]})
        self.assertEqual(set(self.program.shared_resources.values_list("resource_type", flat=True)), {"image", "video", "file"})
        response = self.client.get(self.collection(self.program))
        self.assertContains(response, "<video ")
        self.assertContains(response, 'loading="lazy"')
        file = self.program.shared_resources.get(resource_type="file")
        response = self.client.get(reverse("resource_file", args=[file.pk]))
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertIn("attachment", response["Content-Disposition"])
        response.close()

    def test_existing_members_cannot_see_other_programs_resources(self):
        other = Program.objects.create(name="Other")
        resource = add_resource(other, self.upload(), self.admin)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.collection(other)).status_code, 403)
        self.assertEqual(self.client.get(reverse("resource_file", args=[resource.pk])).status_code, 403)
        self.assertNotContains(self.client.get(reverse("resource_library")), resource.title)

    def test_parent_members_do_not_automatically_access_child_resources(self):
        parent_user = CustomUser.objects.create_user(username="parent@example.com", email="parent@example.com")
        ScopeMembership.objects.create(user=parent_user, program=self.program, role="community_leader")
        access = ResourceAccess(parent_user)
        self.assertTrue(access.allows(self.program, "create"))
        self.assertFalse(access.allows(self.cohort))
        self.assertFalse(access.allows(self.cohort, "create"))

    def test_upload_permission_stays_at_direct_role_level(self):
        membership = self.member.cohort_memberships.get()
        membership.role = "senior_member"
        membership.save()
        self.client.force_login(self.member)
        response = self.client.post(self.collection(self.cohort), {"files": [self.upload()]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.post(self.collection(self.program), {"files": [self.upload()]}).status_code, 403)
        self.assertEqual(self.client.post(reverse("resource_library"), {"scope": scope_key(self.program), "files": [self.upload()]}).status_code, 200)
        self.assertEqual(self.program.shared_resources.count(), 0)

    def test_mentee_can_read_but_cannot_upload_or_remove(self):
        resource = add_resource(self.cohort, self.upload(), self.admin)
        self.client.force_login(self.member)
        response = self.client.get(self.collection(self.cohort))
        self.assertNotContains(response, '<h2>Add resources</h2>')
        self.assertEqual(self.client.post(self.collection(self.cohort), {"files": [self.upload()]}).status_code, 403)
        self.assertEqual(self.client.post(reverse("resource_remove", args=[resource.pk])).status_code, 403)

    def test_direct_membership_roles_respect_permission_matrix(self):
        ScopeMembership.objects.create(user=self.member, location=self.location, role="mentor")
        rule = RolePermission.objects.create(role="mentor", resource="resources", can_read=True, can_create=True)
        self.assertTrue(ResourceAccess(self.member).allows(self.location, "create"))
        # Remove the separate cohort role to isolate the scoped role's read permission.
        self.member.cohort_memberships.update(is_active=False)
        rule.can_read = False
        rule.save()
        self.assertFalse(ResourceAccess(self.member).allows(self.location))

    def test_leaving_and_rejoining_revokes_and_restores_download_access(self):
        resource = add_resource(self.program, self.upload(), self.admin)
        url = reverse("resource_file", args=[resource.pk])
        self.client.force_login(self.member)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        membership = self.member.cohort_memberships.get()
        membership.is_active = False
        membership.save()
        self.assertEqual(self.client.get(url).status_code, 403)
        membership.is_active = True
        membership.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.program.is_active = False
        self.program.save()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_inactive_account_cannot_access_resources(self):
        resource = add_resource(self.program, self.upload(), self.admin)
        self.member.is_active = False
        self.member.save()
        self.assertFalse(ResourceAccess(self.member).allows(self.program))
        self.client.force_login(self.member)
        self.assertIn(self.client.get(reverse("resource_file", args=[resource.pk])).status_code, (302, 403))

    def test_private_files_are_not_exposed_by_media_urls(self):
        resource = add_resource(self.program, self.upload(), self.admin)
        with self.assertRaises(ValueError):
            _ = resource.file.url
        self.client.logout()
        self.assertEqual(self.client.get(reverse("resource_file", args=[resource.pk])).status_code, 302)
        self.assertEqual(self.client.get("/media/" + resource.file.name).status_code, 404)

    def test_video_ranges_and_head_support(self):
        content = b"0123456789abcdef"
        resource = add_resource(self.cohort, self.upload("clip.mp4", content), self.admin)
        self.client.force_login(self.member)
        url = reverse("resource_file", args=[resource.pk])
        for header, expected, content_range in (("bytes=2-5", b"2345", "bytes 2-5/16"), ("bytes=-3", b"def", "bytes 13-15/16"), ("bytes=13-", b"def", "bytes 13-15/16")):
            with self.subTest(header=header):
                response = self.client.get(url, HTTP_RANGE=header)
                self.assertEqual(response.status_code, 206)
                self.assertEqual(b"".join(response.streaming_content), expected)
                self.assertEqual(response["Content-Range"], content_range)
                self.assertEqual(response["Content-Type"], "video/mp4")
                self.assertEqual(response["Cache-Control"], "private, no-store")
                response.close()
        for header in ("bytes=99-100", "bytes=8-2", "bytes=-0", "bytes=0-1,3-4", "invalid", "bytes=" + "9" * 5000 + "-"):
            self.assertEqual(self.client.get(url, HTTP_RANGE=header).status_code, 416)
        response = self.client.head(url)
        self.assertEqual(response["Content-Length"], "16")
        self.assertEqual(response.content, b"")

    def test_removal_is_soft_and_audited(self):
        resource = add_resource(self.chapter, self.upload(), self.admin)
        response = self.client.post(reverse("resource_remove", args=[resource.pk]), HTTP_X_FORM_DRAWER="true")
        self.assertEqual(response.json()["resource_url"], self.collection(self.chapter))
        resource.refresh_from_db()
        self.assertFalse(resource.is_active)
        self.assertTrue(ChangeHistory.objects.filter(action="remove", entity_id=resource.pk, details__resource_model="scope_resource").exists())
        self.assertEqual(self.client.get(reverse("resource_file", args=[resource.pk])).status_code, 404)

    def test_upload_validation_and_size_limit(self):
        response = self.client.post(self.collection(self.program), {}, HTTP_X_FORM_DRAWER="true")
        self.assertIn("files", response.context["upload_form"].errors)
        with override_settings(RESOURCE_UPLOAD_MAX_BYTES=4):
            response = self.client.post(self.collection(self.program), {"files": [self.upload(content=b"12345")]})
        self.assertIn("files", response.context["upload_form"].errors)
        self.assertEqual(self.program.shared_resources.count(), 0)

    def test_resources_have_exactly_one_scope(self):
        for attrs in ({}, {"program": self.program, "cohort": self.cohort}):
            with self.assertRaises(IntegrityError), transaction.atomic():
                ScopeResource.objects.create(title="Invalid", resource_type="file", file="fake", **attrs)

    def test_drawer_fragment_and_json_upload_keep_library_inside_drawer(self):
        url = self.collection(self.program)
        response = self.client.get(url, HTTP_X_FORM_DRAWER="true")
        self.assertContains(response, 'data-resource-drawer-page')
        self.assertNotContains(response, '<!doctype html>')
        self.assertContains(response, f'action="{url}"')
        response = self.client.post(url, {"files": [self.upload()]}, HTTP_X_FORM_DRAWER="true")
        self.assertEqual(response.json(), {"saved": True, "resource_url": url})
        response = self.client.get(url, HTTP_X_FORM_DRAWER="true")
        self.assertContains(response, 'guide')
        self.assertContains(response, 'Resources added successfully.')

    def test_list_actions_and_creation_forms_offer_uploads(self):
        for scope in self.scopes():
            kind = scope._meta.model_name
            response = self.client.get(reverse(f"{kind}_list"))
            self.assertContains(response, self.collection(scope))
            self.assertContains(response, 'Upload / Resources')
            response = self.client.get(reverse(f"{kind}_create"), HTTP_X_FORM_DRAWER="true")
            self.assertContains(response, 'name="resource_files"')

    def test_attachments_can_be_added_during_creation_at_each_level(self):
        cases = (
            ("program", Program, {"name": "Files program"}),
            ("location", Location, {"name": "Files location", "program": self.program.pk}),
            ("chapter", Chapter, {"name": "Files chapter", "location": self.location.pk}),
            ("cohort", Cohort, {"name": "Files cohort", "chapter": self.chapter.pk, "start_date": "2027-01-01"}),
        )
        for kind, model, data in cases:
            response = self.client.post(reverse(f"{kind}_create"), {**data, "resource_files": [self.upload("photo.png"), self.upload("clip.mp4")]}, HTTP_X_FORM_DRAWER="true")
            self.assertEqual(response.json(), {"saved": True})
            self.assertEqual(model.objects.get(name=data["name"]).shared_resources.count(), 2)

    def test_file_route_does_not_get_caught_by_scope_route(self):
        self.assertEqual(resolve(reverse("resource_file", args=[1])).url_name, "resource_file")
        self.assertEqual(self.client.get("/resources/unknown/1/").status_code, 404)

    def test_pagination_and_filters_use_library_urls_in_drawer(self):
        for i in range(14):
            add_resource(self.program, self.upload(f"Guide-{i:02}.txt"), self.admin)
        url = self.collection(self.program)
        response = self.client.get(url, {"q": "Guide", "kind": "file"}, HTTP_X_FORM_DRAWER="true")
        self.assertEqual(len(response.context["resource_page"]), 12)
        self.assertContains(response, f'{url}?q=Guide&amp;kind=file&amp;page=2#shared-resources')
        response = self.client.get(url, {"q": "Guide", "kind": "file", "page": 2}, HTTP_X_FORM_DRAWER="true")
        self.assertEqual(len(response.context["resource_page"]), 2)
        self.assertNotContains(response, '<!doctype html>')

    def test_additional_files_during_edit_do_not_replace_existing_files(self):
        original = add_resource(self.program, self.upload(), self.admin)
        response = self.client.post(reverse("program_edit", args=[self.program.pk]), {
            "name": self.program.name, "is_active": "on", "resource_files": [self.upload("extra.png")],
        }, HTTP_X_FORM_DRAWER="true")
        self.assertEqual(response.json(), {"saved": True})
        self.assertEqual(self.program.shared_resources.count(), 2)
        original.refresh_from_db()
        self.assertTrue(original.is_active)

    def test_invalid_attachment_prevents_resource_and_parent_creation(self):
        with override_settings(RESOURCE_UPLOAD_MAX_BYTES=4):
            response = self.client.post(reverse("program_create"), {
                "name": "Too large", "resource_files": [self.upload(content=b"12345")],
            }, HTTP_X_FORM_DRAWER="true")
        self.assertIn("resource_files", response.context["form"].errors)
        self.assertFalse(Program.objects.filter(name="Too large").exists())

    def test_member_drawer_does_not_expose_admin_navigation(self):
        self.client.force_login(self.member)
        response = self.client.get(self.collection(self.cohort), HTTP_X_FORM_DRAWER="true")
        self.assertContains(response, 'data-resource-drawer-page')
        self.assertNotContains(response, 'class="admin-sidebar"')
        self.assertNotContains(response, 'Add more files')
