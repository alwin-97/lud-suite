import csv
from io import StringIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import MenteeAssessmentForm
from .models import (
    AssessmentRating,
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
    VolunteerTranscript,
    ProfileArtifact,
    RepositoryAsset,
    EvidenceAttachment,
    Programme,
    Location,
    AcademicCycle,
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
        self.assertEqual(entry.review_status, 'Pending')
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

