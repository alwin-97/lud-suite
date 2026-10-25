from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.models import (
    ChangeHistory,
    Cohort,
    CohortActivity,
    CohortMembership,
    CustomUser,
    Term,
    TermResource,
)
from core.tests.base import PlatformTestCase


class TermAndResourceTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        _, _, self.cohort = self.create_cohort()

    def test_create_term_with_documents_images_and_links(self):
        doc_file = SimpleUploadedFile(
            "syllabus.pdf",
            b"%PDF-1.4 test document content",
            content_type="application/pdf",
        )
        img_file = SimpleUploadedFile(
            "schedule.png",
            b"\x89PNG\r\n\x1a\n test image content",
            content_type="image/png",
        )

        response = self.client.post(
            reverse("cohort_term_create", args=[self.cohort.pk]),
            {
                "name": "Term 1: Foundations",
                "sequence": 1,
                "start_date": "2026-06-01",
                "end_date": "2026-11-30",
                "description": "Introduction to youth leadership and community engagement.",
                "is_active": "on",
                "upload_files": [doc_file, img_file],
                "links": "Curriculum Portal | https://curriculum.letusdream.org\nhttps://drive.google.com/sample",
            },
        )

        term = Term.objects.get(cohort=self.cohort, name="Term 1: Foundations")
        self.assertRedirects(
            response, reverse("cohort_term_detail", args=[self.cohort.pk, term.pk])
        )
        self.assertEqual(term.sequence, 1)
        self.assertEqual(term.start_date, date(2026, 6, 1))
        self.assertEqual(term.end_date, date(2026, 11, 30))

        # Verify created resources
        resources = term.resources.all()
        self.assertEqual(resources.count(), 4)

        # Check document
        doc = resources.filter(resource_type=TermResource.DOCUMENT).first()
        self.assertIsNotNone(doc)
        self.assertTrue(doc.is_document)
        self.assertFalse(doc.is_image)
        self.assertIn("syllabus", doc.file.name)

        # Check image
        img = resources.filter(resource_type=TermResource.IMAGE).first()
        self.assertIsNotNone(img)
        self.assertTrue(img.is_image)
        self.assertFalse(img.is_document)
        self.assertIn("schedule", img.file.name)

        # Check links
        links = list(resources.filter(resource_type=TermResource.LINK).order_by("title"))
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].title, "Curriculum Portal")
        self.assertEqual(links[0].url, "https://curriculum.letusdream.org")
        self.assertEqual(links[1].url, "https://drive.google.com/sample")

    def test_term_detail_page_renders_and_allows_adding_individual_resource(self):
        term = Term.objects.create(
            cohort=self.cohort,
            name="Term 2",
            sequence=2,
            start_date=date(2026, 12, 1),
            end_date=date(2027, 5, 31),
        )

        detail_url = reverse("cohort_term_detail", args=[self.cohort.pk, term.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Term 2")

        post_response = self.client.post(
            detail_url,
            {
                "title": "Reference Guide",
                "resource_type": TermResource.LINK,
                "url": "https://guide.letusdream.org",
            },
        )
        self.assertRedirects(post_response, detail_url)
        self.assertTrue(term.resources.filter(title="Reference Guide").exists())

    def test_term_delete_removes_term_and_resources(self):
        term = Term.objects.create(cohort=self.cohort, name="Term to Delete", sequence=3)
        TermResource.objects.create(
            term=term,
            title="Link to Delete",
            resource_type=TermResource.LINK,
            url="https://example.com",
        )

        response = self.client.post(
            reverse("cohort_term_delete", args=[self.cohort.pk, term.pk])
        )
        self.assertRedirects(response, reverse("cohort_manage", args=[self.cohort.pk]))
        self.assertFalse(Term.objects.filter(pk=term.pk).exists())
        self.assertFalse(TermResource.objects.filter(title="Link to Delete").exists())

    def test_delete_individual_resource(self):
        term = Term.objects.create(cohort=self.cohort, name="Term 1", sequence=1)
        res = TermResource.objects.create(
            term=term,
            title="To Remove",
            resource_type=TermResource.LINK,
            url="https://example.com/remove",
        )

        response = self.client.post(
            reverse(
                "cohort_term_resource_delete",
                args=[self.cohort.pk, term.pk, res.pk],
            )
        )
        self.assertRedirects(
            response, reverse("cohort_term_detail", args=[self.cohort.pk, term.pk])
        )
        self.assertFalse(TermResource.objects.filter(pk=res.pk).exists())

    def test_workspace_displays_cohort_terms_to_authorized_user(self):
        user = CustomUser.objects.create_user(
            username="member@example.com", email="member@example.com"
        )
        CohortMembership.objects.create(
            user=user,
            cohort=self.cohort,
            role=CohortMembership.MENTEE,
        )
        term = Term.objects.create(
            cohort=self.cohort,
            name="Term 1: Kickoff",
            sequence=1,
            description="Welcome term for all mentees.",
        )
        TermResource.objects.create(
            term=term,
            title="Welcome Packet",
            resource_type=TermResource.LINK,
            url="https://example.com/welcome",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("workspace_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Term 1: Kickoff")
        self.assertContains(response, "Welcome Packet")
        self.assertContains(response, "https://example.com/welcome")

    def test_allocate_and_reallocate_senior_member_with_history(self):
        user = CustomUser.objects.create_user(
            username="senior@example.com", email="senior@example.com", first_name="Sam"
        )
        # 1. Allocate as Mentee initially
        alloc_response = self.client.post(
            reverse("cohort_manage", args=[self.cohort.pk]),
            {"user": user.pk, "role": CohortMembership.MENTEE},
        )
        self.assertRedirects(alloc_response, reverse("cohort_manage", args=[self.cohort.pk]))
        membership = CohortMembership.objects.get(user=user, cohort=self.cohort)
        self.assertEqual(membership.role, CohortMembership.MENTEE)

        # Verify allocation logged
        alloc_log = ChangeHistory.objects.filter(
            action=ChangeHistory.Action.ALLOCATE, entity_name__contains="senior@example.com"
        ).first()
        self.assertIsNotNone(alloc_log)

        # 2. Reallocate role within cohort: Mentee -> Senior Member
        realloc_url = reverse("cohort_member_reallocate", args=[self.cohort.pk, membership.pk])
        realloc_response = self.client.post(
            realloc_url,
            {"role": CohortMembership.SENIOR_MEMBER, "target_cohort": self.cohort.pk},
        )
        self.assertRedirects(realloc_response, reverse("cohort_manage", args=[self.cohort.pk]))
        membership.refresh_from_db()
        self.assertEqual(membership.role, CohortMembership.SENIOR_MEMBER)

        # Verify reallocation logged
        realloc_log = ChangeHistory.objects.filter(
            action=ChangeHistory.Action.REALLOCATE, entity_name__contains="Senior Member"
        ).first()
        self.assertIsNotNone(realloc_log)

        # 3. Reallocate to another cohort
        _, _, other_cohort = self.create_cohort(name="Cohort 2027")
        move_response = self.client.post(
            reverse("cohort_member_reallocate", args=[self.cohort.pk, membership.pk]),
            {"role": CohortMembership.SENIOR_MEMBER, "target_cohort": other_cohort.pk},
        )
        self.assertRedirects(move_response, reverse("cohort_manage", args=[self.cohort.pk]))
        self.assertFalse(CohortMembership.objects.filter(user=user, cohort=self.cohort).exists())
        self.assertTrue(CohortMembership.objects.filter(user=user, cohort=other_cohort, role=CohortMembership.SENIOR_MEMBER).exists())

    def test_activity_timeline_planning_across_multiple_terms(self):
        term1 = Term.objects.create(cohort=self.cohort, name="Term 1: Discovery", sequence=1)
        term2 = Term.objects.create(cohort=self.cohort, name="Term 2: Mentorship", sequence=2)

        # Plan activity for Term 1
        response1 = self.client.post(
            reverse("cohort_activity_create", args=[self.cohort.pk]),
            {
                "term": term1.pk,
                "title": "Orientation & Team Building",
                "target_audience": CohortActivity.TargetAudience.ALL,
                "status": CohortActivity.Status.COMPLETED,
                "start_date": "2026-06-01",
                "end_date": "2026-06-15",
                "sequence": 1,
                "description": "Kickoff sessions for all cohorts.",
            },
        )
        self.assertRedirects(response1, reverse("cohort_timeline", args=[self.cohort.pk]))

        # Plan activity for Term 2 specifically for Senior Members & Mentors
        response2 = self.client.post(
            reverse("cohort_activity_create", args=[self.cohort.pk]),
            {
                "term": term2.pk,
                "title": "Senior Member Review & Mentorship Check-in",
                "target_audience": CohortActivity.TargetAudience.SENIOR_MEMBERS,
                "status": CohortActivity.Status.IN_PROGRESS,
                "start_date": "2026-12-01",
                "end_date": "2026-12-15",
                "sequence": 1,
                "description": "Mid-term review by senior members.",
            },
        )
        self.assertRedirects(response2, reverse("cohort_timeline", args=[self.cohort.pk]))

        # View complete cohort timeline
        timeline_response = self.client.get(reverse("cohort_timeline", args=[self.cohort.pk]))
        self.assertEqual(timeline_response.status_code, 200)
        self.assertContains(timeline_response, "Orientation &amp; Team Building")
        self.assertContains(timeline_response, "Senior Member Review")
        self.assertContains(timeline_response, "50%")  # 1 completed out of 2 total = 50%

    def test_audit_trail_review_page(self):
        # Trigger an action
        Term.objects.create(cohort=self.cohort, name="Audited Term", sequence=10)
        from core.models import log_change
        log_change(
            actor=self.admin,
            action=ChangeHistory.Action.CREATE,
            entity_type="Term",
            entity_name="Audited Term",
            cohort=self.cohort,
            description="Created test audited term.",
        )

        audit_url = reverse("audit_log")
        response = self.client.get(audit_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audited Term")
        self.assertContains(response, "Created test audited term.")

        # Test filtering by action
        filter_response = self.client.get(f"{audit_url}?action=create")
        self.assertEqual(filter_response.status_code, 200)
        self.assertContains(filter_response, "Audited Term")


class RolePermissionMatrixAndRBACTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        _, _, self.cohort = self.create_cohort()
        self.leader = CustomUser.objects.create_user(
            username="leader@example.com", email="leader@example.com", first_name="Leader"
        )
        CohortMembership.objects.create(
            user=self.leader, cohort=self.cohort, role=CohortMembership.COMMUNITY_LEADER
        )

        self.senior = CustomUser.objects.create_user(
            username="senior@example.com", email="senior@example.com", first_name="Senior"
        )
        CohortMembership.objects.create(
            user=self.senior, cohort=self.cohort, role=CohortMembership.SENIOR_MEMBER
        )

        self.mentee = CustomUser.objects.create_user(
            username="mentee@example.com", email="mentee@example.com", first_name="Mentee"
        )
        CohortMembership.objects.create(
            user=self.mentee, cohort=self.cohort, role=CohortMembership.MENTEE
        )

    def test_permissions_matrix_view_accessible_by_admin_only(self):
        url = reverse("role_permissions_matrix")

        # Mentee cannot access matrix
        self.client.force_login(self.mentee)
        res_mentee = self.client.get(url)
        self.assertEqual(res_mentee.status_code, 403)

        # Admin can access matrix
        self.client.force_login(self.admin)
        res_admin = self.client.get(url)
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, "Role Permissions Matrix")
        self.assertContains(res_admin, "Community Leader")
        self.assertContains(res_admin, "Senior Member")
        self.assertContains(res_admin, "Mentor")
        self.assertContains(res_admin, "Mentee")

    def test_save_permissions_matrix_and_reset_defaults(self):
        self.client.force_login(self.admin)
        url = reverse("role_permissions_matrix")

        # 1. Save custom permissions (give mentee activity create permission)
        post_data = {
            "perm_mentee_activities_create": "on",
            "perm_mentee_activities_read": "on",
            "perm_community_leader_terms_read": "on",
        }
        save_res = self.client.post(url, post_data)
        self.assertRedirects(save_res, url)

        from core.models import RolePermission
        mentee_act_perm = RolePermission.objects.get(role="mentee", resource="activities")
        self.assertTrue(mentee_act_perm.can_create)
        self.assertTrue(mentee_act_perm.can_read)
        self.assertFalse(mentee_act_perm.can_delete)

        # Verify audit history logged the matrix save
        perm_log = ChangeHistory.objects.filter(entity_type="RolePermission").first()
        self.assertIsNotNone(perm_log)

        # 2. Reset to system defaults
        reset_res = self.client.post(url, {"action": "reset_defaults"})
        self.assertRedirects(reset_res, url)
        self.assertEqual(RolePermission.objects.count(), 0)

    def test_default_permissions_enforce_crud_boundaries(self):
        term = Term.objects.create(cohort=self.cohort, name="Term 1", sequence=1)

        # Community leader CAN create activity
        self.client.force_login(self.leader)
        create_act_res = self.client.post(
            reverse("cohort_activity_create", args=[self.cohort.pk]),
            {
                "term": term.pk,
                "title": "Leader Scheduled Session",
                "target_audience": CohortActivity.TargetAudience.ALL,
                "status": CohortActivity.Status.PLANNED,
                "sequence": 1,
            },
        )
        self.assertRedirects(create_act_res, reverse("cohort_timeline", args=[self.cohort.pk]))
        self.assertTrue(CohortActivity.objects.filter(title="Leader Scheduled Session").exists())

        # Mentee CANNOT create activity (403)
        self.client.force_login(self.mentee)
        mentee_act_res = self.client.post(
            reverse("cohort_activity_create", args=[self.cohort.pk]),
            {
                "term": term.pk,
                "title": "Mentee Illegal Activity",
                "target_audience": CohortActivity.TargetAudience.ALL,
                "status": CohortActivity.Status.PLANNED,
                "sequence": 2,
            },
        )
        self.assertEqual(mentee_act_res.status_code, 403)
        self.assertFalse(CohortActivity.objects.filter(title="Mentee Illegal Activity").exists())

        # Mentee CANNOT delete term (403)
        mentee_del_res = self.client.post(
            reverse("cohort_term_delete", args=[self.cohort.pk, term.pk])
        )
        self.assertEqual(mentee_del_res.status_code, 403)
        self.assertTrue(Term.objects.filter(pk=term.pk).exists())

    def test_senior_member_can_upload_resource_but_cannot_delete_term(self):
        term = Term.objects.create(cohort=self.cohort, name="Senior Term", sequence=1)
        self.client.force_login(self.senior)

        # Senior member CAN add a resource (link/document)
        add_res = self.client.post(
            reverse("cohort_term_detail", args=[self.cohort.pk, term.pk]),
            {
                "title": "Senior Study Guide",
                "resource_type": TermResource.LINK,
                "url": "https://study.letusdream.org",
            },
        )
        self.assertRedirects(add_res, reverse("cohort_term_detail", args=[self.cohort.pk, term.pk]))
        self.assertTrue(TermResource.objects.filter(title="Senior Study Guide").exists())

        # Senior member CANNOT delete the term (403)
        del_res = self.client.post(
            reverse("cohort_term_delete", args=[self.cohort.pk, term.pk])
        )
        self.assertEqual(del_res.status_code, 403)
        self.assertTrue(Term.objects.filter(pk=term.pk).exists())

    def test_db_role_permission_overrides_grant_and_revoke_access(self):
        from core.models import RolePermission
        term = Term.objects.create(cohort=self.cohort, name="Override Term", sequence=1)

        # 1. Grant: Normally mentee cannot create activity. Grant can_create=True via DB override.
        RolePermission.objects.create(
            role=CohortMembership.MENTEE,
            resource=RolePermission.Resource.ACTIVITIES,
            can_create=True,
            can_read=True,
            can_update=False,
            can_delete=False,
        )
        self.client.force_login(self.mentee)
        mentee_res = self.client.post(
            reverse("cohort_activity_create", args=[self.cohort.pk]),
            {
                "term": term.pk,
                "title": "Mentee Granted Activity",
                "target_audience": CohortActivity.TargetAudience.MENTEES,
                "status": CohortActivity.Status.PLANNED,
                "sequence": 1,
            },
        )
        self.assertRedirects(mentee_res, reverse("cohort_timeline", args=[self.cohort.pk]))
        self.assertTrue(CohortActivity.objects.filter(title="Mentee Granted Activity").exists())

        # 2. Revoke: Normally community leader can delete term. Revoke can_delete=False via DB override.
        RolePermission.objects.create(
            role=CohortMembership.COMMUNITY_LEADER,
            resource=RolePermission.Resource.TERMS,
            can_create=True,
            can_read=True,
            can_update=True,
            can_delete=False,
        )
        self.client.force_login(self.leader)
        leader_del_res = self.client.post(
            reverse("cohort_term_delete", args=[self.cohort.pk, term.pk])
        )
        self.assertEqual(leader_del_res.status_code, 403)
        self.assertTrue(Term.objects.filter(pk=term.pk).exists())

    def test_has_perm_template_tag_behavior(self):
        from django.template import Context, Template
        from core.models import RolePermission

        template = Template(
            "{% load ui %}"
            "{% has_perm 'terms' 'create' cohort as can_create_term %}"
            "{% has_perm 'terms' 'delete' cohort as can_delete_term %}"
            "{% if can_create_term %}CAN_CREATE{% else %}NO_CREATE{% endif %}|"
            "{% if can_delete_term %}CAN_DELETE{% else %}NO_DELETE{% endif %}"
        )

        # Leader: can create, can delete
        rendered_leader = template.render(Context({"user": self.leader, "cohort": self.cohort}))
        self.assertEqual(rendered_leader, "CAN_CREATE|CAN_DELETE")

        # Mentee: cannot create, cannot delete
        rendered_mentee = template.render(Context({"user": self.mentee, "cohort": self.cohort}))
        self.assertEqual(rendered_mentee, "NO_CREATE|NO_DELETE")


class UserActivityReportTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        _, _, self.cohort = self.create_cohort()
        self.leader = CustomUser.objects.create_user(
            username="leader@example.com", email="leader@example.com", first_name="Leader"
        )
        CohortMembership.objects.create(
            user=self.leader, cohort=self.cohort, role=CohortMembership.COMMUNITY_LEADER
        )

        self.mentee = CustomUser.objects.create_user(
            username="mentee@example.com", email="mentee@example.com", first_name="Alex"
        )
        CohortMembership.objects.create(
            user=self.mentee, cohort=self.cohort, role=CohortMembership.MENTEE
        )

        self.term = Term.objects.create(
            cohort=self.cohort, name="Term 1: Foundations", sequence=1
        )
        self.activity = CohortActivity.objects.create(
            cohort=self.cohort,
            term=self.term,
            title="Community Leadership Workshop",
            target_audience=CohortActivity.TargetAudience.ALL,
            status=CohortActivity.Status.COMPLETED,
            sequence=1,
        )

    def test_user_activity_report_detail_view_renders_metrics_and_activities(self):
        from core.models import UserActivityReport
        report = UserActivityReport.objects.create(
            user=self.mentee,
            cohort=self.cohort,
            term=self.term,
            activity=self.activity,
            title="Workshop Milestone Report",
            hours_spent=6.5,
            status=UserActivityReport.Status.SUBMITTED,
            summary="Completed team leadership session and group deliverable.",
            reflections="Learned collaboration strategies.",
            challenges="Tight schedule.",
            next_steps="Draft follow-up questions.",
        )

        self.client.force_login(self.admin)
        url = reverse("user_activity_report", args=[self.mentee.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Workshop Milestone Report")
        self.assertContains(response, "Completed team leadership session")
        self.assertContains(response, "6.5 hrs")
        self.assertContains(response, "100%")  # completed milestone rate
        self.assertContains(response, "Community Leadership Workshop")

    def test_prepare_activity_report_create_view(self):
        from core.models import UserActivityReport
        self.client.force_login(self.admin)
        url = reverse("user_activity_report_create", args=[self.mentee.pk])

        post_data = {
            "cohort": self.cohort.pk,
            "term": self.term.pk,
            "activity": self.activity.pk,
            "title": "Initial Term Activity Review",
            "report_date": "2026-06-20",
            "hours_spent": "5.0",
            "progress_status": "completed",
            "status": "submitted",
            "summary": "Attended all orientation modules and delivered report.",
            "reflections": "Gained broad understanding of LUD values.",
            "challenges": "None encountered.",
            "next_steps": "Begin Term 2 preparations.",
        }

        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse("user_activity_report", args=[self.mentee.pk]))

        report = UserActivityReport.objects.filter(
            user=self.mentee, title="Initial Term Activity Review"
        ).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.hours_spent, 5.0)
        self.assertEqual(report.progress_status, "completed")
        self.assertEqual(report.cohort, self.cohort)
        self.assertEqual(report.term, self.term)

        # Check audit history
        audit_entry = ChangeHistory.objects.filter(
            action=ChangeHistory.Action.CREATE, entity_name__contains="Initial Term Activity Review"
        ).first()
        self.assertIsNotNone(audit_entry)

    def test_user_can_prepare_own_activity_report_from_workspace(self):
        from core.models import UserActivityReport
        self.client.force_login(self.mentee)

        # Visit workspace dashboard
        dash_response = self.client.get(reverse("workspace_home"))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, "My Activity Reports")

        # Prepare self report
        url = reverse("user_activity_report_create", args=[self.mentee.pk])
        post_data = {
            "cohort": self.cohort.pk,
            "term": self.term.pk,
            "title": "Self Submitted Milestone Report",
            "report_date": "2026-07-01",
            "hours_spent": "3.5",
            "progress_status": "in_progress",
            "status": "submitted",
            "summary": "Organized study circle with fellow mentees.",
            "reflections": "Peer learning improved comprehension.",
            "challenges": "Finding common meeting times.",
            "next_steps": "Schedule bi-weekly sync.",
        }
        res = self.client.post(url, post_data)
        self.assertEqual(res.status_code, 302)

        self.assertTrue(
            UserActivityReport.objects.filter(
                user=self.mentee, title="Self Submitted Milestone Report"
            ).exists()
        )

    def test_leader_review_and_approval_of_activity_report(self):
        from core.models import UserActivityReport
        report = UserActivityReport.objects.create(
            user=self.mentee,
            cohort=self.cohort,
            term=self.term,
            title="Needs Leader Review",
            hours_spent=4.0,
            status=UserActivityReport.Status.SUBMITTED,
            summary="Completed community engagement task.",
        )

        # Leader logs in and reviews the report
        self.client.force_login(self.leader)
        review_url = reverse(
            "user_activity_report_review", args=[self.mentee.pk, report.pk]
        )
        response = self.client.post(
            review_url,
            {
                "status": UserActivityReport.Status.APPROVED,
                "feedback": "Outstanding work and initiative demonstrated! Approved without reservations.",
            },
        )
        self.assertRedirects(response, reverse("user_activity_report", args=[self.mentee.pk]))

        report.refresh_from_db()
        self.assertEqual(report.status, UserActivityReport.Status.APPROVED)
        self.assertEqual(report.reviewed_by, self.leader)
        self.assertIn("Outstanding work", report.feedback)

    def test_unrelated_user_cannot_view_or_edit_another_user_report(self):
        # Create an unrelated user in a separate cohort
        _, _, other_cohort = self.create_cohort(name="Separate Cohort")
        other_user = CustomUser.objects.create_user(
            username="other@example.com", email="other@example.com"
        )
        CohortMembership.objects.create(
            user=other_user, cohort=other_cohort, role=CohortMembership.MENTEE
        )

        from core.models import UserActivityReport
        report = UserActivityReport.objects.create(
            user=self.mentee,
            cohort=self.cohort,
            term=self.term,
            title="Confidential Progress Report",
            hours_spent=2.0,
            status=UserActivityReport.Status.SUBMITTED,
            summary="Internal notes.",
        )

        # Other user tries to access report -> 403 Forbidden
        self.client.force_login(other_user)
        res_view = self.client.get(reverse("user_activity_report", args=[self.mentee.pk]))
        self.assertEqual(res_view.status_code, 403)

        res_edit = self.client.get(
            reverse("user_activity_report_edit", args=[self.mentee.pk, report.pk])
        )
        self.assertEqual(res_edit.status_code, 403)


class TermTaskAndQuestionTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        _, _, self.cohort = self.create_cohort()
        self.leader = CustomUser.objects.create_user(
            username="task_leader@example.com", email="task_leader@example.com", first_name="TaskLeader"
        )
        CohortMembership.objects.create(
            user=self.leader, cohort=self.cohort, role=CohortMembership.COMMUNITY_LEADER
        )

        self.mentor = CustomUser.objects.create_user(
            username="task_mentor@example.com", email="task_mentor@example.com", first_name="TaskMentor"
        )
        CohortMembership.objects.create(
            user=self.mentor, cohort=self.cohort, role=CohortMembership.MENTOR
        )

        self.mentee = CustomUser.objects.create_user(
            username="task_mentee@example.com", email="task_mentee@example.com", first_name="TaskMentee"
        )
        CohortMembership.objects.create(
            user=self.mentee, cohort=self.cohort, role=CohortMembership.MENTEE
        )

        self.term = Term.objects.create(
            cohort=self.cohort, name="Term 1: Core Fundamentals", sequence=1
        )

    def test_term_form_instantiation_without_clearable_file_error(self):
        from core.forms import TermForm
        # This must instantiate smoothly without throwing ValueError
        form = TermForm(cohort=self.cohort)
        self.assertIn("upload_files", form.fields)
        self.assertIn("links", form.fields)

    def test_create_term_task_and_view_detail(self):
        from core.models import TermTask
        self.client.force_login(self.leader)

        url = reverse("cohort_term_task_create", args=[self.cohort.pk, self.term.pk])
        post_data = {
            "title": "Module 1 Research Project",
            "description": "Submit a full research paper with dataset and presentation slides.",
            "target_audience": "mentees",
            "due_date": "2026-07-15",
            "points": 100,
            "allow_text": True,
            "allow_file": True,
            "allow_url": True,
            "allow_image": True,
            "sequence": 1,
            "is_active": True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        task = TermTask.objects.filter(term=self.term, title="Module 1 Research Project").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.points, 100)
        self.assertEqual(task.allowed_types_display, "Text, File, URL, Image")

        # View detail page
        detail_url = reverse(
            "cohort_term_task_detail", args=[self.cohort.pk, self.term.pk, task.pk]
        )
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Module 1 Research Project")
        self.assertContains(detail_res, "Text, File, URL, Image")

    def test_participant_submits_task_with_text_and_url(self):
        from core.models import TermTask, TaskSubmission
        task = TermTask.objects.create(
            term=self.term,
            title="Milestone Presentation",
            description="Submit links and summaries.",
            allow_text=True,
            allow_url=True,
            allow_file=False,
            allow_image=False,
            points=50,
        )

        self.client.force_login(self.mentee)
        detail_url = reverse(
            "cohort_term_task_detail", args=[self.cohort.pk, self.term.pk, task.pk]
        )

        post_data = {
            "text_response": "Here is the summary of our community initiative and findings.",
            "url_submission": "https://github.com/example/community-project",
        }
        res = self.client.post(detail_url, post_data)
        self.assertRedirects(res, detail_url)

        submission = TaskSubmission.objects.filter(task=task, user=self.mentee).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.status, TaskSubmission.Status.SUBMITTED)
        self.assertIn("Here is the summary", submission.text_response)
        self.assertEqual(submission.url_submission, "https://github.com/example/community-project")

    def test_participant_submits_task_with_file_and_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.models import TermTask, TaskSubmission

        task = TermTask.objects.create(
            term=self.term,
            title="Design Diagrams Task",
            description="Upload architectural blueprints and diagram images.",
            allow_text=True,
            allow_file=True,
            allow_image=True,
            points=100,
        )

        self.client.force_login(self.mentee)
        detail_url = reverse(
            "cohort_term_task_detail", args=[self.cohort.pk, self.term.pk, task.pk]
        )

        test_doc = SimpleUploadedFile("spec.pdf", b"%PDF-1.4 test document content", content_type="application/pdf")
        test_img = SimpleUploadedFile("diagram.png", b"\x89PNG\r\n\x1a\n test image content", content_type="image/png")

        post_data = {
            "text_response": "Attached design specification and architecture diagram.",
            "file_submission": test_doc,
            "image_submission": test_img,
        }
        res = self.client.post(detail_url, post_data)
        self.assertRedirects(res, detail_url)

        sub = TaskSubmission.objects.filter(task=task, user=self.mentee).first()
        self.assertIsNotNone(sub)
        self.assertTrue(sub.file_submission.name.endswith(".pdf"))
        self.assertTrue(sub.image_submission.name.endswith(".png"))

    def test_mentor_reviews_and_scores_task_submission(self):
        from core.models import TermTask, TaskSubmission

        task = TermTask.objects.create(
            term=self.term,
            title="Final Project Milestone",
            description="Capstone milestone.",
            points=100,
        )
        sub = TaskSubmission.objects.create(
            task=task,
            user=self.mentee,
            text_response="Completed deliverables.",
            status=TaskSubmission.Status.SUBMITTED,
        )

        self.client.force_login(self.mentor)
        review_url = reverse(
            "task_submission_review",
            args=[self.cohort.pk, self.term.pk, task.pk, sub.pk],
        )

        post_data = {
            "status": "approved",
            "score": "95.5",
            "feedback": "Outstanding execution and thorough documentation!",
        }
        res = self.client.post(review_url, post_data)
        self.assertRedirects(
            res,
            reverse("cohort_term_task_detail", args=[self.cohort.pk, self.term.pk, task.pk]),
        )

        sub.refresh_from_db()
        self.assertEqual(sub.status, TaskSubmission.Status.APPROVED)
        self.assertEqual(float(sub.score), 95.5)
        self.assertEqual(sub.reviewed_by, self.mentor)
        self.assertIn("Outstanding execution", sub.feedback)

    def test_create_term_question_and_participant_response(self):
        from core.models import TermQuestion, QuestionResponse

        self.client.force_login(self.leader)
        create_url = reverse("cohort_term_question_create", args=[self.cohort.pk, self.term.pk])

        post_data = {
            "title": "Leadership Reflection Question",
            "prompt": "How did your mentoring sessions influence your project trajectory this term?",
            "help_text": "Give 2-3 specific examples.",
            "target_audience": "all",
            "due_date": "2026-08-01",
            "is_required": True,
            "allow_text": True,
            "allow_file": True,
            "allow_url": True,
            "allow_image": True,
            "sequence": 1,
            "is_active": True,
        }
        res = self.client.post(create_url, post_data)
        self.assertEqual(res.status_code, 302)

        question = TermQuestion.objects.filter(term=self.term, title="Leadership Reflection Question").first()
        self.assertIsNotNone(question)
        self.assertTrue(question.is_required)

        # Mentee logs in and answers
        self.client.force_login(self.mentee)
        q_url = reverse(
            "cohort_term_question_detail", args=[self.cohort.pk, self.term.pk, question.pk]
        )
        answer_data = {
            "text_response": "My mentor helped streamline our research hypothesis and data model.",
        }
        ans_res = self.client.post(q_url, answer_data)
        self.assertRedirects(ans_res, q_url)

        resp_obj = QuestionResponse.objects.filter(question=question, user=self.mentee).first()
        self.assertIsNotNone(resp_obj)
        self.assertEqual(resp_obj.status, QuestionResponse.Status.SUBMITTED)
        self.assertIn("streamline our research hypothesis", resp_obj.text_response)

    def test_mentor_reviews_question_response(self):
        from core.models import TermQuestion, QuestionResponse

        question = TermQuestion.objects.create(
            term=self.term,
            title="Weekly Assessment",
            prompt="Weekly progress summary.",
        )
        resp_obj = QuestionResponse.objects.create(
            question=question,
            user=self.mentee,
            text_response="Met all weekly benchmarks.",
            status=QuestionResponse.Status.SUBMITTED,
        )

        self.client.force_login(self.mentor)
        review_url = reverse(
            "question_response_review",
            args=[self.cohort.pk, self.term.pk, question.pk, resp_obj.pk],
        )

        review_data = {
            "status": "reviewed",
            "feedback": "Great focus this week, keep it up!",
        }
        res = self.client.post(review_url, review_data)
        self.assertRedirects(
            res,
            reverse("cohort_term_question_detail", args=[self.cohort.pk, self.term.pk, question.pk]),
        )

        resp_obj.refresh_from_db()
        self.assertEqual(resp_obj.status, QuestionResponse.Status.REVIEWED)
        self.assertEqual(resp_obj.reviewed_by, self.mentor)
        self.assertIn("Great focus this week", resp_obj.feedback)

    def test_mentee_cannot_create_or_delete_tasks(self):
        from core.models import TermTask
        task = TermTask.objects.create(
            term=self.term,
            title="Protected Task",
            description="Only admins and leaders can edit.",
        )

        self.client.force_login(self.mentee)

        # Mentee cannot create a task
        create_res = self.client.post(
            reverse("cohort_term_task_create", args=[self.cohort.pk, self.term.pk]),
            {"title": "Unauthorized Task", "description": "Should fail", "allow_text": True},
        )
        self.assertEqual(create_res.status_code, 403)

        # Mentee cannot delete task
        delete_res = self.client.post(
            reverse("cohort_term_task_delete", args=[self.cohort.pk, self.term.pk, task.pk])
        )
        self.assertEqual(delete_res.status_code, 403)
        self.assertTrue(TermTask.objects.filter(pk=task.pk).exists())


class MentorAndSeniorMentorScopeTests(PlatformTestCase):
    def setUp(self):
        super().setUp()
        _, _, self.cohort = self.create_cohort()
        self.term = Term.objects.create(
            cohort=self.cohort, name="Term 1: Discovery", sequence=1
        )

        # Leader
        self.leader = CustomUser.objects.create_user(
            username="scoped_leader@example.com", email="scoped_leader@example.com", first_name="Leader"
        )
        CohortMembership.objects.create(
            user=self.leader, cohort=self.cohort, role=CohortMembership.COMMUNITY_LEADER
        )

        # Senior Mentor
        self.senior_mentor = CustomUser.objects.create_user(
            username="senior_mentor@example.com", email="senior_mentor@example.com", first_name="SeniorMentor"
        )
        CohortMembership.objects.create(
            user=self.senior_mentor, cohort=self.cohort, role=CohortMembership.SENIOR_MEMBER
        )

        # Mentor A and Mentee A
        self.mentor_a = CustomUser.objects.create_user(
            username="mentor_a@example.com", email="mentor_a@example.com", first_name="MentorA"
        )
        CohortMembership.objects.create(
            user=self.mentor_a, cohort=self.cohort, role=CohortMembership.MENTOR
        )
        self.mentee_a = CustomUser.objects.create_user(
            username="mentee_a@example.com", email="mentee_a@example.com", first_name="MenteeA"
        )
        CohortMembership.objects.create(
            user=self.mentee_a, cohort=self.cohort, role=CohortMembership.MENTEE
        )

        # Mentor B and Mentee B
        self.mentor_b = CustomUser.objects.create_user(
            username="mentor_b@example.com", email="mentor_b@example.com", first_name="MentorB"
        )
        CohortMembership.objects.create(
            user=self.mentor_b, cohort=self.cohort, role=CohortMembership.MENTOR
        )
        self.mentee_b = CustomUser.objects.create_user(
            username="mentee_b@example.com", email="mentee_b@example.com", first_name="MenteeB"
        )
        CohortMembership.objects.create(
            user=self.mentee_b, cohort=self.cohort, role=CohortMembership.MENTEE
        )

        # Allocate Mentor A -> Mentee A, Mentor B -> Mentee B
        from core.models import MentorAssignment
        MentorAssignment.objects.create(
            cohort=self.cohort, mentor=self.mentor_a, mentee=self.mentee_a, assigned_by=self.leader
        )
        MentorAssignment.objects.create(
            cohort=self.cohort, mentor=self.mentor_b, mentee=self.mentee_b, assigned_by=self.leader
        )

        # Outside Cohort and Out-of-scope Mentee
        _, _, self.other_cohort = self.create_cohort(name="External Cohort")
        self.outside_mentee = CustomUser.objects.create_user(
            username="outside_mentee@example.com", email="outside_mentee@example.com", first_name="Outside"
        )
        CohortMembership.objects.create(
            user=self.outside_mentee, cohort=self.other_cohort, role=CohortMembership.MENTEE
        )

    def test_mentor_can_only_see_their_mentee_data(self):
        # Mentor A views Mentee A -> Allowed
        self.client.force_login(self.mentor_a)
        res_mentee_a = self.client.get(reverse("user_activity_report", args=[self.mentee_a.pk]))
        self.assertEqual(res_mentee_a.status_code, 200)

        # Mentor A views Mentee B (assigned to Mentor B) -> 403 Forbidden
        res_mentee_b = self.client.get(reverse("user_activity_report", args=[self.mentee_b.pk]))
        self.assertEqual(res_mentee_b.status_code, 403)

        # Mentor A views Mentor B -> 403 Forbidden
        res_mentor_b = self.client.get(reverse("user_activity_report", args=[self.mentor_b.pk]))
        self.assertEqual(res_mentor_b.status_code, 403)

    def test_senior_mentor_sees_all_mentees_and_mentors_in_scope(self):
        self.client.force_login(self.senior_mentor)

        # Senior mentor can view Mentee A
        res_mentee_a = self.client.get(reverse("user_activity_report", args=[self.mentee_a.pk]))
        self.assertEqual(res_mentee_a.status_code, 200)

        # Senior mentor can view Mentee B
        res_mentee_b = self.client.get(reverse("user_activity_report", args=[self.mentee_b.pk]))
        self.assertEqual(res_mentee_b.status_code, 200)

        # Senior mentor can view Mentor A
        res_mentor_a = self.client.get(reverse("user_activity_report", args=[self.mentor_a.pk]))
        self.assertEqual(res_mentor_a.status_code, 200)

        # Senior mentor can view Mentor B
        res_mentor_b = self.client.get(reverse("user_activity_report", args=[self.mentor_b.pk]))
        self.assertEqual(res_mentor_b.status_code, 200)

        # Outside of scope -> 403 Forbidden
        res_outside = self.client.get(reverse("user_activity_report", args=[self.outside_mentee.pk]))
        self.assertEqual(res_outside.status_code, 403)

    def test_mentor_task_submissions_scoping(self):
        from core.models import TermTask, TaskSubmission

        task = TermTask.objects.create(
            term=self.term,
            title="Scoped Assignment",
            description="Milestone submission.",
            points=100,
        )
        sub_a = TaskSubmission.objects.create(
            task=task,
            user=self.mentee_a,
            text_response="Mentee A work.",
            status=TaskSubmission.Status.SUBMITTED,
        )
        sub_b = TaskSubmission.objects.create(
            task=task,
            user=self.mentee_b,
            text_response="Mentee B work.",
            status=TaskSubmission.Status.SUBMITTED,
        )

        # Mentor A visits task detail: should see Mentee A's submission, but NOT Mentee B's
        self.client.force_login(self.mentor_a)
        url = reverse("cohort_term_task_detail", args=[self.cohort.pk, self.term.pk, task.pk])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "MenteeA")
        self.assertNotContains(res, "MenteeB")

        # Mentor A tries to review Mentee B's submission -> 403 Forbidden
        review_b_url = reverse(
            "task_submission_review",
            args=[self.cohort.pk, self.term.pk, task.pk, sub_b.pk],
        )
        review_res = self.client.post(
            review_b_url,
            {"status": "approved", "score": "90", "feedback": "Attempted by wrong mentor"},
        )
        self.assertEqual(review_res.status_code, 403)

        # Mentor A reviews Mentee A's submission -> Success
        review_a_url = reverse(
            "task_submission_review",
            args=[self.cohort.pk, self.term.pk, task.pk, sub_a.pk],
        )
        review_res_a = self.client.post(
            review_a_url,
            {"status": "approved", "score": "98", "feedback": "Well done Mentee A!"},
        )
        self.assertEqual(review_res_a.status_code, 302)
        sub_a.refresh_from_db()
        self.assertEqual(sub_a.status, TaskSubmission.Status.APPROVED)
        self.assertEqual(float(sub_a.score), 98.0)

        # Senior Mentor visits task detail: sees BOTH Mentee A and Mentee B
        self.client.force_login(self.senior_mentor)
        senior_res = self.client.get(url)
        self.assertEqual(senior_res.status_code, 200)
        self.assertContains(senior_res, "MenteeA")
        self.assertContains(senior_res, "MenteeB")

        # Senior Mentor reviews Mentee B's submission -> Success
        senior_review_b = self.client.post(
            review_b_url,
            {"status": "reviewed", "score": "88", "feedback": "Approved by Senior Mentor"},
        )
        self.assertEqual(senior_review_b.status_code, 302)
        sub_b.refresh_from_db()
        self.assertEqual(sub_b.status, TaskSubmission.Status.REVIEWED)
        self.assertEqual(sub_b.reviewed_by, self.senior_mentor)

    def test_allocate_and_unassign_mentor_flow(self):
        from core.models import MentorAssignment

        self.client.force_login(self.leader)

        # Allocate Mentor A to Mentee B as co-mentor
        alloc_url = reverse("cohort_mentor_allocate", args=[self.cohort.pk])
        post_data = {
            "mentor": self.mentor_a.pk,
            "mentee": self.mentee_b.pk,
            "notes": "Co-mentorship for technical research.",
        }
        res = self.client.post(alloc_url, post_data)
        self.assertRedirects(res, reverse("cohort_manage", args=[self.cohort.pk]))

        assignment = MentorAssignment.objects.filter(
            cohort=self.cohort, mentor=self.mentor_a, mentee=self.mentee_b
        ).first()
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.notes, "Co-mentorship for technical research.")

        # Unassign pairing
        unassign_url = reverse(
            "cohort_mentor_unassign", args=[self.cohort.pk, assignment.pk]
        )
        del_res = self.client.post(unassign_url)
        self.assertRedirects(del_res, reverse("cohort_manage", args=[self.cohort.pk]))
        self.assertFalse(
            MentorAssignment.objects.filter(pk=assignment.pk).exists()
        )

    def test_workspace_view_for_mentor_and_senior_mentor(self):
        # Mentor A visits workspace -> sees "My Mentees" with Mentee A
        self.client.force_login(self.mentor_a)
        ws_res_a = self.client.get(reverse("workspace_home"))
        self.assertEqual(ws_res_a.status_code, 200)
        self.assertContains(ws_res_a, "My Mentees")
        self.assertContains(ws_res_a, "MenteeA")
        self.assertNotContains(ws_res_a, "MenteeB")

        # Senior mentor visits workspace -> sees "Senior Mentorship Scope" with both mentors & mentees
        self.client.force_login(self.senior_mentor)
        ws_res_senior = self.client.get(reverse("workspace_home"))
        self.assertEqual(ws_res_senior.status_code, 200)
        self.assertContains(ws_res_senior, "Senior Mentorship Scope")
        self.assertContains(ws_res_senior, "Mentors in Scope")
        self.assertContains(ws_res_senior, "Mentees in Scope")
        self.assertContains(ws_res_senior, "MentorA")
        self.assertContains(ws_res_senior, "MentorB")
        self.assertContains(ws_res_senior, "MenteeA")
        self.assertContains(ws_res_senior, "MenteeB")





