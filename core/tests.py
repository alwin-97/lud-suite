import csv
from io import BytesIO, StringIO
from datetime import timedelta

import openpyxl
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from .forms import DiaryEntryForm, MenteeAssessmentForm, ReflectiveReportForm
from .models import (
    Activity,
    AssessmentRating,
    ApprovalLog,
    CustomUser,
    DomainIndicator,
    Mentee,
    MenteeAssessment,
    MentorMenteeAssignment,
    MoodCategory,
    RatingDomain,
    RatingScaleDefinition,
    SessionType,
    ReflectiveReport,
    DiaryEntry,
    WorkSchedule,
    WorkScheduleAssignment,
    VolunteerTranscript,
    ProfileArtifact,
    RepositoryAsset,
    EvidenceAttachment,
    Programme,
    Location,
    AcademicCycle,
    Notification,
    VolunteerReportingAssignment,
)


class AdminConfigViewTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpass123",
            role="admin",
        )

    def test_rating_scales_config_page_is_available(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin_config_list", args=["rating-scale-definitions"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rating Scales")


class PermissionDeniedRedirectTests(TestCase):
    def setUp(self):
        self.mentor = CustomUser.objects.create_user(
            username="mentor-403@example.com",
            email="mentor-403@example.com",
            password="testpass123",
            role="mentor",
        )

    def test_authenticated_user_is_redirected_to_dashboard_on_forbidden_page(self):
        self.client.force_login(self.mentor)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_anonymous_user_still_sees_403_page(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Access Denied", status_code=403)


class UserRoleManagerTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username="admin-roles@example.com",
            email="admin-roles@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            role="admin",
            roles=["admin", "mentor"],
        )

    def test_admin_user_is_listed_in_role_manager(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("user_role_manager"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin-roles@example.com")
        self.assertContains(response, 'value="admin"', html=False)


class SharedLayoutSidebarTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username="sidebar-admin@example.com",
            email="sidebar-admin@example.com",
            password="testpass123",
            role="admin",
            roles=["admin", "mentor"],
        )
        self.volunteer = CustomUser.objects.create_user(
            username="sidebar-vol@example.com",
            email="sidebar-vol@example.com",
            password="testpass123",
            role="volunteer",
            roles=["volunteer"],
        )
        self.multi_role_mentor = CustomUser.objects.create_user(
            username="sidebar-multi-mentor@example.com",
            email="sidebar-multi-mentor@example.com",
            password="testpass123",
            role="mentor",
            roles=["mentor", "endorser"],
        )

    def test_admin_profile_uses_admin_sidebar_links(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin_dashboard"))
        self.assertContains(response, reverse("user_role_manager"))
        self.assertContains(response, reverse("repository"))
        self.assertContains(response, 'value="mentor"', html=False)
        self.assertNotContains(response, "Switch to Mentor")

    def test_admin_mentee_directory_uses_admin_shell(self):
        mentee_user = CustomUser.objects.create_user(
            username="admin-shell-mentee@example.com",
            email="admin-shell-mentee@example.com",
            password="testpass123",
            role="mentee",
            roles=["mentee"],
        )
        Mentee.objects.create(user=mentee_user, full_name="Admin Shell Mentee", current_year=1)
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("mentor_mentee_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("admin_dashboard"))
        self.assertContains(response, "Mentee Directory")
        self.assertNotContains(response, reverse("dashboard"))

    def test_volunteer_profile_uses_volunteer_sidebar_links(self):
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("work_diary"))
        self.assertContains(response, reverse("reflective_report"))
        self.assertContains(response, reverse("transcript"))

    def test_mentor_profile_route_redirects_to_shared_profile(self):
        mentor = CustomUser.objects.create_user(
            username="shared-mentor@example.com",
            email="shared-mentor@example.com",
            password="testpass123",
            role="mentor",
            roles=["mentor"],
        )
        self.client.force_login(mentor)

        response = self.client.get(reverse("mentor_profile"))

        self.assertRedirects(response, reverse("profile"), fetch_redirect_response=False)

    def test_endorser_profile_routes_redirect_to_shared_profile_flow(self):
        endorser = CustomUser.objects.create_user(
            username="shared-endorser@example.com",
            email="shared-endorser@example.com",
            password="testpass123",
            role="endorser",
            roles=["endorser"],
        )
        self.client.force_login(endorser)

        profile_response = self.client.get(reverse("endorser_profile"))
        edit_response = self.client.get(reverse("endorser_edit_profile"))

        self.assertRedirects(profile_response, reverse("profile"), fetch_redirect_response=False)
        self.assertRedirects(edit_response, reverse("profile_edit"), fetch_redirect_response=False)

    def test_non_admin_multi_role_user_does_not_see_role_switcher(self):
        self.client.force_login(self.multi_role_mentor)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("switch_role"))
        self.assertNotContains(response, "fa-repeat")


class RoleSwitchTests(TestCase):
    def setUp(self):
        self.super_admin = CustomUser.objects.create_user(
            username="switch-admin@example.com",
            email="switch-admin@example.com",
            password="testpass123",
            role="admin",
            roles=["admin", "mentor"],
            is_superuser=True,
            is_staff=True,
        )
        self.admin_single_role = CustomUser.objects.create_user(
            username="switch-admin-single@example.com",
            email="switch-admin-single@example.com",
            password="testpass123",
            role="admin",
            roles=["admin"],
        )
        self.multi_role_mentor = CustomUser.objects.create_user(
            username="switch-mentor@example.com",
            email="switch-mentor@example.com",
            password="testpass123",
            role="mentor",
            roles=["mentor", "endorser"],
        )

    def test_superuser_can_switch_active_role_from_header_dropdown(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(reverse("switch_role"), {"role": "mentor"}, follow=True)

        self.assertRedirects(response, reverse("dashboard"))
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.role, "mentor")
        self.assertIn("admin", self.super_admin.roles)
        self.assertIn("mentor", self.super_admin.roles)

    def test_multi_role_admin_sees_role_switcher_on_admin_dashboard(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("switch_role"))
        self.assertContains(response, 'value="mentor"', html=False)

    def test_admin_with_single_role_does_not_see_role_switcher(self):
        self.client.force_login(self.admin_single_role)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("switch_role"))

    def test_non_admin_cannot_switch_roles_even_if_multiple_roles_are_assigned(self):
        self.client.force_login(self.multi_role_mentor)

        response = self.client.post(reverse("switch_role"), {"role": "endorser"}, follow=True)

        self.assertRedirects(response, reverse("dashboard"))
        self.multi_role_mentor.refresh_from_db()
        self.assertEqual(self.multi_role_mentor.role, "mentor")
        self.assertContains(response, "Role switching is available only for admins with multiple assigned roles.")


class WorkspaceWorkflowTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username="workspace-admin@example.com",
            email="workspace-admin@example.com",
            password="testpass123",
            role="admin",
            roles=["admin"],
        )
        self.volunteer = CustomUser.objects.create_user(
            username="workspace-vol@example.com",
            email="workspace-vol@example.com",
            password="testpass123",
            first_name="Workspace",
            last_name="Volunteer",
            role="volunteer",
            roles=["volunteer"],
        )
        self.mentor = CustomUser.objects.create_user(
            username="workspace-mentor@example.com",
            email="workspace-mentor@example.com",
            password="testpass123",
            role="mentor",
            roles=["mentor"],
        )
        self.endorser = CustomUser.objects.create_user(
            username="workspace-endorser@example.com",
            email="workspace-endorser@example.com",
            password="testpass123",
            role="endorser",
            roles=["endorser"],
        )
        self.mentee_user = CustomUser.objects.create_user(
            username="workspace-mentee@example.com",
            email="workspace-mentee@example.com",
            password="testpass123",
            role="mentee",
            roles=["mentee"],
        )
        self.programme = Programme.objects.create(name="Workspace Programme", code="WSP")
        self.location = Location.objects.create(name="Workspace Location", code="WSLOC")
        VolunteerReportingAssignment.objects.create(
            volunteer=self.volunteer,
            programme=self.programme,
            location=self.location,
            endorser=self.endorser,
            assigned_by=self.admin_user,
        )
        ReflectiveReport.objects.create(
            user=self.volunteer,
            programme=self.programme,
            location=self.location,
            activity_name="Approved Reflection",
            duration=2,
            date=timezone.now().date(),
            learnings="Learned to facilitate and document work.",
            status="Approved",
        )
        DiaryEntry.objects.create(
            volunteer=self.volunteer,
            date=timezone.now().date(),
            duration=3,
            location=self.location,
            linked_activity="Reviewed Diary Activity",
            narrative_entry="Supported programme delivery and follow-up.",
            review_status="Approved",
        )

    def test_role_redirect_supports_workspace_roles(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("role-redirect"))
        self.assertRedirects(response, reverse("admin_dashboard"), fetch_redirect_response=False)

        self.client.force_login(self.volunteer)
        response = self.client.get(reverse("role-redirect"))
        self.assertRedirects(response, reverse("volunteer_dashboard"), fetch_redirect_response=False)

        self.client.force_login(self.mentor)
        response = self.client.get(reverse("role-redirect"))
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

        self.client.force_login(self.endorser)
        response = self.client.get(reverse("role-redirect"))
        self.assertRedirects(response, reverse("endorser_dashboard"), fetch_redirect_response=False)

    def test_volunteer_dashboard_shows_reporting_assignment_and_history_links(self):
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("volunteer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.programme.name)
        self.assertContains(response, self.location.name)
        self.assertContains(response, reverse("work_diary_list"))
        self.assertContains(response, reverse("reflective_report_list"))

    def test_shared_volunteer_pages_include_page_header_and_breadcrumb(self):
        self.client.force_login(self.volunteer)

        for url_name, heading in [
            ("repository", "Shared Data Repository"),
            ("transcript", "Generated Transcripts"),
            ("reflective_report", "Reflective Reports"),
            ("work_diary", "Work Diary"),
        ]:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, reverse("volunteer_dashboard"))
            self.assertContains(response, heading)

    def test_endorser_dashboard_uses_notification_center_link(self):
        self.client.force_login(self.endorser)

        response = self.client.get(reverse("endorser_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("notification"))
        self.assertContains(response, reverse("approval_dashboard"))
        self.assertNotContains(response, reverse("manage_assignment"))

    def test_volunteer_can_generate_transcript_draft_from_approved_records(self):
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("generate_transcript"),
            {"template_choice": "Volunteer Service Summary"},
            follow=True,
        )

        self.assertRedirects(response, reverse("transcript"))
        transcript = VolunteerTranscript.objects.get(volunteer=self.volunteer)
        self.assertEqual(transcript.approval_status, "Pending Review")
        self.assertIn("contributed", transcript.generated_summary)
        self.assertTrue(Notification.objects.filter(target_group="mentor").exists())
        self.assertTrue(Notification.objects.filter(target_group="endorser").exists())

    def test_mentor_can_approve_transcript_and_generate_export(self):
        transcript = VolunteerTranscript.objects.create(
            volunteer=self.volunteer,
            template_choice="Leadership Transcript",
            generated_summary="Draft summary",
            approval_status="Pending Review",
        )
        self.client.force_login(self.mentor)

        response = self.client.post(
            reverse("review_transcript", args=[transcript.id]),
            {"action": "approve", "comments": "Looks good."},
            follow=True,
        )

        self.assertRedirects(response, reverse("transcript"))
        transcript.refresh_from_db()
        self.assertEqual(transcript.approval_status, "Approved")
        self.assertEqual(transcript.reviewer_notes, "Looks good.")
        self.assertTrue(transcript.export_file)
        self.assertTrue(
            ApprovalLog.objects.filter(record_type="transcript", record_id=transcript.id, decision="approved").exists()
        )
        self.assertTrue(Notification.objects.filter(target_group="admin", subject="Transcript ready for export").exists())
        self.assertTrue(Notification.objects.filter(target_group="volunteer", subject="Transcript approved").exists())

    def test_admin_cannot_review_transcript_but_can_view_and_export(self):
        transcript = VolunteerTranscript.objects.create(
            volunteer=self.volunteer,
            template_choice="Leadership Transcript",
            generated_summary="Draft summary",
            approval_status="Approved",
        )
        transcript.export_file.save(
            "transcript_test.txt",
            SimpleUploadedFile("transcript_test.txt", b"approved transcript"),
            save=True,
        )
        self.client.force_login(self.admin_user)

        post_response = self.client.post(
            reverse("review_transcript", args=[transcript.id]),
            {"action": "approve", "comments": "Final approval."},
            follow=True,
        )
        self.assertRedirects(post_response, reverse("admin_dashboard"))
        transcript.refresh_from_db()
        self.assertEqual(transcript.approval_status, "Approved")
        self.assertEqual(transcript.reviewer_notes, "")
        self.assertTrue(transcript.export_file)

        get_response = self.client.get(reverse("transcript"))

        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, self.volunteer.get_full_name() or self.volunteer.username)
        self.assertContains(get_response, "Download Transcript")
        self.assertNotContains(get_response, reverse("review_transcript", args=[transcript.id]))

    def test_admin_can_open_bulk_upload_workspace(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("bulk_upload_mentees"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload")

    def test_non_volunteer_is_redirected_from_volunteer_submission_pages(self):
        self.client.force_login(self.mentor)

        diary_response = self.client.get(reverse("work_diary"))
        report_response = self.client.get(reverse("reflective_report"))

        self.assertEqual(diary_response.status_code, 302)
        self.assertRedirects(diary_response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(report_response.status_code, 302)
        self.assertRedirects(report_response, reverse("dashboard"), fetch_redirect_response=False)

    def test_repository_upload_saves_asset_without_record_link_fields(self):
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("repository"),
            {
                "title": "Session Evidence",
                "category": "Evidence",
                "role_visibility": "volunteer",
                "tags": "session proof",
                "file_upload": SimpleUploadedFile("evidence.txt", b"proof"),
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("repository"))
        asset = RepositoryAsset.objects.get(title="Session Evidence")
        self.assertEqual(asset.uploaded_by, self.volunteer)
        self.assertFalse(EvidenceAttachment.objects.filter(asset=asset).exists())

    def test_admin_can_view_all_repository_assets_and_toggle_status(self):
        active_asset = RepositoryAsset.objects.create(
            title="Mentor Only Asset",
            category="Guides",
            uploaded_by=self.volunteer,
            role_visibility="mentor",
        )
        inactive_asset = RepositoryAsset.objects.create(
            title="Hidden Volunteer Asset",
            category="Evidence",
            uploaded_by=self.volunteer,
            role_visibility="volunteer",
            is_active=False,
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("repository"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, active_asset.title)
        self.assertContains(response, inactive_asset.title)
        self.assertContains(response, reverse("toggle_repository_asset_status", args=[active_asset.id]))

        toggle_response = self.client.post(
            reverse("toggle_repository_asset_status", args=[active_asset.id]),
            follow=True,
        )

        self.assertRedirects(toggle_response, reverse("repository"))
        active_asset.refresh_from_db()
        self.assertFalse(active_asset.is_active)

    def test_non_admin_repository_hides_inactive_assets(self):
        RepositoryAsset.objects.create(
            title="Disabled Volunteer Asset",
            category="Evidence",
            uploaded_by=self.volunteer,
            role_visibility="volunteer",
            is_active=False,
        )
        RepositoryAsset.objects.create(
            title="Visible Volunteer Asset",
            category="Evidence",
            uploaded_by=self.volunteer,
            role_visibility="volunteer",
            is_active=True,
        )
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse("repository"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Volunteer Asset")
        self.assertNotContains(response, "Disabled Volunteer Asset")

    def test_reflective_report_form_hides_backend_managed_identity_and_status_fields(self):
        form = ReflectiveReportForm(user=self.volunteer)

        self.assertNotIn("reporter_name", form.fields)
        self.assertNotIn("reporter_email", form.fields)
        self.assertNotIn("reporter_identifier", form.fields)
        self.assertNotIn("reporter_class_role", form.fields)
        self.assertNotIn("status", form.fields)

    def test_reflective_report_post_sets_backend_identity_and_submit_status(self):
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("reflective_report"),
            {
                "activity_name": "Volunteer Reflection",
                "duration": "2.5",
                "date": timezone.now().date().isoformat(),
                "learnings": "Learned through field work.",
                "feedback": "Positive session.",
                "suggestions": "More time for reflection.",
                "submit_action": "submit",
                "reporter_name": "Spoofed Name",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("reflective_report"))
        report = ReflectiveReport.objects.get(activity_name="Volunteer Reflection")
        self.assertEqual(report.status, "Submitted")
        self.assertEqual(report.reporter_name, self.volunteer.get_full_name())
        self.assertEqual(report.reporter_email, self.volunteer.email)
        self.assertEqual(report.reporter_identifier, self.volunteer.username)
        self.assertEqual(report.reporter_class_role, self.volunteer.get_role_display())
        self.assertEqual(report.programme, self.programme)
        self.assertEqual(report.location, self.location)
        self.assertEqual(report.endorser, self.endorser)

    def test_reflective_report_requires_admin_reporting_assignment(self):
        VolunteerReportingAssignment.objects.filter(volunteer=self.volunteer).delete()
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("reflective_report"),
            {
                "activity_name": "Unmapped Reflection",
                "duration": "1.5",
                "date": timezone.now().date().isoformat(),
                "learnings": "Test learnings",
                "feedback": "Test feedback",
                "submit_action": "submit",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("reflective_report"))
        self.assertFalse(ReflectiveReport.objects.filter(activity_name="Unmapped Reflection").exists())
        self.assertContains(response, "Admin must assign your programme, location, and endorser")

    def test_work_diary_form_hides_backend_managed_location_and_status_fields(self):
        form = DiaryEntryForm(user=self.volunteer)

        self.assertNotIn("location", form.fields)
        self.assertNotIn("review_status", form.fields)

    def test_work_diary_post_sets_backend_location_and_submit_status(self):
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("work_diary"),
            {
                "date": timezone.now().date().isoformat(),
                "duration": "1.75",
                "linked_activity": "Mapped Field Visit",
                "narrative_entry": "Completed assigned field work and recorded outcomes.",
                "submit_action": "submit",
                "location": "",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("work_diary"))
        entry = DiaryEntry.objects.get(linked_activity="Mapped Field Visit")
        self.assertEqual(entry.review_status, "Submitted")
        self.assertEqual(entry.location, self.location)

    def test_work_diary_requires_admin_reporting_assignment(self):
        VolunteerReportingAssignment.objects.filter(volunteer=self.volunteer).delete()
        self.client.force_login(self.volunteer)

        response = self.client.post(
            reverse("work_diary"),
            {
                "date": timezone.now().date().isoformat(),
                "duration": "1.0",
                "linked_activity": "Unmapped Diary",
                "narrative_entry": "Should not save without assignment.",
                "submit_action": "submit",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("work_diary"))
        self.assertFalse(DiaryEntry.objects.filter(linked_activity="Unmapped Diary").exists())
        self.assertContains(response, "Admin must assign your reporting location")

    def test_work_diary_form_page_shows_only_latest_five_entries(self):
        DiaryEntry.objects.filter(volunteer=self.volunteer).delete()
        for index in range(6):
            DiaryEntry.objects.create(
                volunteer=self.volunteer,
                date=timezone.now().date(),
                duration=1 + index,
                location=self.location,
                linked_activity=f"Diary Entry {index}",
                narrative_entry=f"Narrative {index}",
                review_status="Draft",
            )

        self.client.force_login(self.volunteer)
        response = self.client.get(reverse("work_diary"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diary Entry 5")
        self.assertContains(response, "Diary Entry 1")
        self.assertNotContains(response, "Diary Entry 0")
        self.assertContains(response, reverse("work_diary_list"))

    def test_work_diary_list_page_shows_full_entry_history(self):
        DiaryEntry.objects.filter(volunteer=self.volunteer).delete()
        for index in range(6):
            DiaryEntry.objects.create(
                volunteer=self.volunteer,
                date=timezone.now().date(),
                duration=1 + index,
                location=self.location,
                linked_activity=f"All Diary Entry {index}",
                narrative_entry=f"Narrative {index}",
                review_status="Draft",
            )

        self.client.force_login(self.volunteer)
        response = self.client.get(reverse("work_diary_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All Diary Entry 5")
        self.assertContains(response, "All Diary Entry 0")
        self.assertContains(response, reverse("work_diary"))

    def test_reflective_report_form_page_shows_only_latest_five_reports(self):
        ReflectiveReport.objects.filter(user=self.volunteer).delete()
        for index in range(6):
            ReflectiveReport.objects.create(
                user=self.volunteer,
                programme=self.programme,
                location=self.location,
                endorser=self.endorser,
                activity_name=f"Report Entry {index}",
                duration=1 + index,
                date=timezone.now().date(),
                learnings=f"Learnings {index}",
                feedback=f"Feedback {index}",
                status="Draft",
            )

        self.client.force_login(self.volunteer)
        response = self.client.get(reverse("reflective_report"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Entry 5")
        self.assertContains(response, "Report Entry 1")
        self.assertNotContains(response, "Report Entry 0")
        self.assertContains(response, reverse("reflective_report_list"))

    def test_reflective_report_list_page_shows_full_report_history(self):
        ReflectiveReport.objects.filter(user=self.volunteer).delete()
        for index in range(6):
            ReflectiveReport.objects.create(
                user=self.volunteer,
                programme=self.programme,
                location=self.location,
                endorser=self.endorser,
                activity_name=f"All Report Entry {index}",
                duration=1 + index,
                date=timezone.now().date(),
                learnings=f"Learnings {index}",
                feedback=f"Feedback {index}",
                status="Draft",
            )

        self.client.force_login(self.volunteer)
        response = self.client.get(reverse("reflective_report_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All Report Entry 5")
        self.assertContains(response, "All Report Entry 0")
        self.assertContains(response, reverse("reflective_report"))

    def test_endorser_can_create_work_item_for_mentor_and_volunteer(self):
        self.client.force_login(self.endorser)

        response = self.client.post(
            reverse("manage_work_items"),
            {
                "assignees": [str(self.mentor.id), str(self.volunteer.id)],
                "role": "Field Follow-up",
                "due_date": timezone.now().date().isoformat(),
                "description": "Complete the assigned follow-up work and document the result.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("manage_work_items"))
        schedule = WorkSchedule.objects.get(role="Field Follow-up")
        self.assertEqual(schedule.endorser, self.endorser)
        self.assertEqual(schedule.mentors.count(), 2)
        self.assertTrue(schedule.mentors.filter(id=self.mentor.id).exists())
        self.assertTrue(schedule.mentors.filter(id=self.volunteer.id).exists())
        self.assertEqual(schedule.assignments.count(), 2)

    def test_endorser_can_edit_existing_work_item_and_assignment_scope(self):
        schedule = WorkSchedule.objects.create(
            endorser=self.endorser,
            role="Original Item",
            due_date=timezone.now().date(),
            description="Original description",
        )
        schedule.mentors.set([self.mentor, self.volunteer])
        WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.mentor)
        WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.volunteer)
        self.client.force_login(self.endorser)

        response = self.client.post(
            reverse("manage_work_items"),
            {
                "schedule_id": str(schedule.id),
                "assignees": [str(self.volunteer.id)],
                "role": "Updated Item",
                "due_date": timezone.now().date().isoformat(),
                "description": "Updated description",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("manage_work_items"))
        schedule.refresh_from_db()
        self.assertEqual(schedule.role, "Updated Item")
        self.assertEqual(schedule.mentors.count(), 1)
        self.assertTrue(schedule.mentors.filter(id=self.volunteer.id).exists())
        self.assertFalse(schedule.assignments.filter(assignee=self.mentor).exists())

    def test_mentor_and_volunteer_can_view_assigned_work_items(self):
        schedule = WorkSchedule.objects.create(
            endorser=self.endorser,
            role="Shared Work Item",
            due_date=timezone.now().date(),
            description="Track assigned tasks",
        )
        schedule.mentors.set([self.mentor, self.volunteer])
        WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.mentor)
        WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.volunteer)

        self.client.force_login(self.mentor)
        mentor_response = self.client.get(reverse("assigned_work_items"))
        self.assertEqual(mentor_response.status_code, 200)
        self.assertContains(mentor_response, "Shared Work Item")

        self.client.force_login(self.volunteer)
        volunteer_response = self.client.get(reverse("assigned_work_items"))
        self.assertEqual(volunteer_response.status_code, 200)
        self.assertContains(volunteer_response, "Shared Work Item")

    def test_assignee_can_update_work_item_status(self):
        schedule = WorkSchedule.objects.create(
            endorser=self.endorser,
            role="Status Update Item",
            due_date=timezone.now().date(),
            description="Complete and update status",
        )
        schedule.mentors.set([self.mentor])
        assignment = WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.mentor)
        self.client.force_login(self.mentor)

        response = self.client.post(
            reverse("update_work_item_status", args=[assignment.id]),
            {
                "status": WorkScheduleAssignment.Status.COMPLETED,
                "progress_note": "Finished the assigned work.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("assigned_work_items"))
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, WorkScheduleAssignment.Status.COMPLETED)
        self.assertEqual(assignment.progress_note, "Finished the assigned work.")

    def test_admin_can_create_work_items_for_non_admin_users(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("manage_work_items"),
            {
                "assignees": [str(self.endorser.id), str(self.mentee_user.id)],
                "role": "Admin Oversight Task",
                "due_date": timezone.now().date().isoformat(),
                "description": "Complete the requested follow-up and share status updates.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("manage_work_items"))
        schedule = WorkSchedule.objects.get(role="Admin Oversight Task")
        self.assertEqual(schedule.endorser, self.admin_user)
        self.assertEqual(schedule.assignments.count(), 2)
        self.assertTrue(schedule.assignments.filter(assignee=self.endorser).exists())
        self.assertTrue(schedule.assignments.filter(assignee=self.mentee_user).exists())

    def test_endorser_and_mentee_can_view_admin_assigned_work_items(self):
        schedule = WorkSchedule.objects.create(
            endorser=self.admin_user,
            role="Cross Role Work Item",
            due_date=timezone.now().date(),
            description="Shared task from admin.",
        )
        schedule.mentors.set([self.endorser, self.mentee_user])
        WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.endorser)
        WorkScheduleAssignment.objects.create(work_schedule=schedule, assignee=self.mentee_user)

        self.client.force_login(self.endorser)
        endorser_response = self.client.get(reverse("assigned_work_items"))
        self.assertEqual(endorser_response.status_code, 200)
        self.assertContains(endorser_response, "Cross Role Work Item")

        self.client.force_login(self.mentee_user)
        mentee_response = self.client.get(reverse("assigned_work_items"))
        self.assertEqual(mentee_response.status_code, 200)
        self.assertContains(mentee_response, "Cross Role Work Item")


class DipAnalyticsTests(TestCase):
    def setUp(self):
        self.mentor = CustomUser.objects.create_user(
            username="dip-mentor@example.com",
            email="dip-mentor@example.com",
            password="testpass123",
            role="mentor",
            roles=["mentor"],
        )

    def test_dip_yclp_view_exposes_live_analytics(self):
        today = timezone.now().date()
        Activity.objects.create(
            user=self.mentor,
            date=today,
            duration="1.50",
            activity="YCLP-Class",
            learnings="Current month class",
        )
        Activity.objects.create(
            user=self.mentor,
            date=today - timedelta(days=35),
            duration="2.00",
            activity="DREAMS Summer Camp",
            learnings="Camp work",
        )
        Activity.objects.create(
            user=self.mentor,
            date=today - timedelta(days=70),
            duration="0.75",
            activity="DREAMS Follow-Up",
            learnings="Follow-up work",
        )

        self.client.force_login(self.mentor)
        response = self.client.get(reverse("dip_yclp"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Activity Breakdown")
        self.assertContains(response, "Six-Month Trend")
        analytics = response.context["analytics"]
        self.assertEqual(analytics["total_entries"], 3)
        self.assertEqual(analytics["total_hours"], 4.25)
        self.assertEqual(analytics["hours_this_month"], 1.5)
        self.assertEqual(analytics["activity_type_count"], 3)
        self.assertIn("YCLP-Class", analytics["activity_breakdown"]["labels"])
        self.assertEqual(len(analytics["monthly_trend"]["labels"]), 6)

    def test_new_activity_response_returns_updated_analytics(self):
        self.client.force_login(self.mentor)
        today = timezone.now().date()

        response = self.client.post(
            reverse("new_activity"),
            {
                "date": today.isoformat(),
                "duration": "1.25",
                "activity": "YCLP-Class",
                "learnings": "Session learnings",
                "feedback": "Good session",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["analytics"]["total_entries"], 1)
        self.assertEqual(payload["analytics"]["total_hours"], 1.25)
        self.assertEqual(payload["analytics"]["hours_this_month"], 1.25)
        self.assertEqual(payload["analytics"]["activity_breakdown"]["labels"], ["YCLP-Class"])


class MenteeAssessmentFormTests(TestCase):
    def test_mood_fields_use_configured_categories(self):
        MoodCategory.objects.create(name="Motivated", sort_order=1)
        MoodCategory.objects.create(name="Stressed", sort_order=2)

        form = MenteeAssessmentForm()

        self.assertEqual(
            list(form.fields["beginning_mood"].choices),
            [("", "Select"), ("Motivated", "Motivated"), ("Stressed", "Stressed")],
        )
        self.assertEqual(
            list(form.fields["end_mood"].choices),
            [("", "Select"), ("Motivated", "Motivated"), ("Stressed", "Stressed")],
        )


class MentorAssessmentViewTests(TestCase):
    def setUp(self):
        self.mentor = CustomUser.objects.create_user(
            username="mentor@example.com",
            email="mentor@example.com",
            password="testpass123",
            role="mentor",
        )
        self.mentee_user = CustomUser.objects.create_user(
            username="mentee@example.com",
            email="mentee@example.com",
            password="testpass123",
            role="mentee",
        )
        self.mentee = Mentee.objects.create(
            user=self.mentee_user,
            full_name="Mentee Example",
            current_year=1,
        )
        MentorMenteeAssignment.objects.create(
            mentor=self.mentor,
            mentee=self.mentee,
            start_date=timezone.now().date(),
            is_active=True,
        )
        self.domain = RatingDomain.objects.create(year=1, name="Leadership", source="tracker", sort_order=1)
        DomainIndicator.objects.create(domain=self.domain, description="Participates consistently", sort_order=1)
        RatingScaleDefinition.objects.create(domain=self.domain, score=5, description="Excellent leadership")

    def test_assessment_form_shows_indicator_and_scale_guidance(self):
        self.client.force_login(self.mentor)

        response = self.client.get(reverse("mentor_assessment_create", args=[self.mentee.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participates consistently")
        self.assertContains(response, "Excellent leadership")


class ProgressExportTests(TestCase):
    def setUp(self):
        self.mentor = CustomUser.objects.create_user(
            username="mentor-export@example.com",
            email="mentor-export@example.com",
            password="testpass123",
            role="mentor",
        )
        self.mentee_user = CustomUser.objects.create_user(
            username="mentee-export@example.com",
            email="mentee-export@example.com",
            password="testpass123",
            role="mentee",
        )
        self.mentee = Mentee.objects.create(
            user=self.mentee_user,
            full_name="Export Mentee",
            current_year=1,
        )
        MentorMenteeAssignment.objects.create(
            mentor=self.mentor,
            mentee=self.mentee,
            start_date=timezone.now().date(),
            is_active=True,
        )
        session_type = SessionType.objects.create(name="Summer Camp")
        self.domain = RatingDomain.objects.create(year=1, name="Communication", source="tracker", sort_order=1)
        assessment = MenteeAssessment.objects.create(
            mentee=self.mentee,
            mentor=self.mentor,
            year=1,
            session_type=session_type,
            date=timezone.now().date(),
            theme_topic="Storytelling",
            beginning_mood="Motivated",
            end_mood="Motivated",
            mentor_remarks="Strong session",
            action_plan="Keep practicing",
        )
        AssessmentRating.objects.create(assessment=assessment, domain=self.domain, value=4)

    def test_export_includes_domain_columns_and_scores(self):
        self.client.force_login(self.mentor)

        response = self.client.get(reverse("export_mentee_progress", args=[self.mentee.id]))

        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        assessment_header = next(row for row in rows if row and row[0] == "Date")
        assessment_row = next(row for row in rows if row and row[0] == str(timezone.now().date()))

        self.assertIn("Year 1 - Communication", assessment_header)
        self.assertEqual(assessment_row[-1], "4")


class AdminExportRouteTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username="admin-export@example.com",
            email="admin-export@example.com",
            password="testpass123",
            role="admin",
        )
        self.volunteer = CustomUser.objects.create_user(
            username="vol-export@example.com",
            email="vol-export@example.com",
            password="testpass123",
            role="volunteer",
        )
        self.programme = Programme.objects.create(name="Export Programme", code="EXP01")
        self.location = Location.objects.create(name="Export Location", code="EXPLOC")
        ReflectiveReport.objects.create(
            user=self.volunteer,
            programme=self.programme,
            location=self.location,
            activity_name="Reflection Activity",
            duration=2.5,
            date=timezone.now().date(),
            learnings="Key learnings",
            feedback="Useful feedback",
            status="Submitted",
        )
        DiaryEntry.objects.create(
            volunteer=self.volunteer,
            date=timezone.now().date(),
            duration=3.0,
            location=self.location,
            linked_activity="Volunteer Shift",
            narrative_entry="Worked on volunteer tasks.",
            review_status="Approved",
        )

    def test_named_export_routes_resolve_to_core_views(self):
        reflective_match = resolve(reverse("export_reflective_reports"))
        diaries_match = resolve(reverse("export_work_diaries"))

        self.assertEqual(reflective_match.func.__name__, "export_reflective_reports_excel")
        self.assertEqual(reflective_match.func.__module__, "core.views.admin")
        self.assertEqual(diaries_match.func.__name__, "export_work_diaries_excel")
        self.assertEqual(diaries_match.func.__module__, "core.views.admin")

    def test_admin_can_download_reflective_reports_export(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("export_reflective_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        workbook = openpyxl.load_workbook(filename=BytesIO(response.content))
        worksheet = workbook.active
        self.assertEqual(worksheet.title, "Reflective Reports")
        self.assertEqual(worksheet["A2"].value, self.volunteer.get_full_name() or self.volunteer.username)
        self.assertEqual(worksheet["E2"].value, "Reflection Activity")

    def test_admin_can_download_work_diaries_export(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("export_work_diaries"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        workbook = openpyxl.load_workbook(filename=BytesIO(response.content))
        worksheet = workbook.active
        self.assertEqual(worksheet.title, "Work Diaries")
        self.assertEqual(worksheet["A2"].value, self.volunteer.get_full_name() or self.volunteer.username)
        self.assertEqual(worksheet["E2"].value, "Volunteer Shift")


class SRSModelsTests(TestCase):
    def setUp(self):
        self.volunteer = CustomUser.objects.create_user(
            username="vol@example.com", email="vol@example.com",
            password="pass", role="volunteer"
        )
        self.academic_cycle = AcademicCycle.objects.create(
            year_label="2026-2027", start_date=timezone.now().date(), end_date=timezone.now().date()
        )
        self.programme = Programme.objects.create(name="DIP", code="DIP01")
        self.location = Location.objects.create(name="Main Campus", code="MC")

    def test_reflective_report_creation(self):
        report = ReflectiveReport.objects.create(
            user=self.volunteer,
            programme=self.programme,
            location=self.location,
            activity_name="Leadership Workshop",
            duration=2.5,
            date=timezone.now().date(),
            learnings="Learned a lot."
        )
        self.assertEqual(report.status, 'Draft')
        self.assertEqual(ReflectiveReport.objects.count(), 1)

    def test_diary_entry_creation(self):
        entry = DiaryEntry.objects.create(
            volunteer=self.volunteer,
            date=timezone.now().date(),
            duration=4.0,
            location=self.location,
            linked_activity="Community Clean Up",
            narrative_entry="Cleaned the park."
        )
        self.assertEqual(entry.review_status, 'Draft')
        self.assertEqual(DiaryEntry.objects.count(), 1)

    def test_volunteer_transcript_creation(self):
        transcript = VolunteerTranscript.objects.create(
            volunteer=self.volunteer,
            template_choice="Standard Template",
            generated_summary="A very good volunteer."
        )
        self.assertEqual(transcript.approval_status, 'Draft')

    def test_profile_artifact_creation(self):
        artifact = ProfileArtifact.objects.create(
            user=self.volunteer,
            title="First Aid Certificate",
            is_public=True
        )
        self.assertEqual(ProfileArtifact.objects.count(), 1)

    def test_repository_asset_creation(self):
        asset = RepositoryAsset.objects.create(
            title="Training Guide",
            category="Training",
            uploaded_by=self.volunteer,
            role_visibility="all"
        )
        self.assertEqual(RepositoryAsset.objects.count(), 1)

    def test_evidence_attachment_creation(self):
        asset = RepositoryAsset.objects.create(
            title="Session Photo",
            category="Evidence",
            uploaded_by=self.volunteer,
            role_visibility="leadership"
        )
        attachment = EvidenceAttachment.objects.create(
            asset=asset,
            linked_model="MenteeAssessment",
            linked_id=1,
            uploaded_by=self.volunteer
        )
        self.assertEqual(EvidenceAttachment.objects.count(), 1)

