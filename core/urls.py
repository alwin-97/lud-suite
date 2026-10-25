from django.urls import include, path

from core.views import auth, configuration, dashboard, reports, tasks_questions, users, workspace


def crud_urls(route, name, list_view, create_view, update_view, delete_view=None, pk_kwarg=None):
    """list / new / <id>/edit / <id>/delete for one resource.

    URL names are <name>_list, <name>_create, <name>_edit, <name>_delete and the
    object id kwarg is <name>_id unless pk_kwarg is given, e.g. location_edit(location_id).
    """
    pk = pk_kwarg or f"{name}_id"
    patterns = [
        path(route, list_view.as_view(), name=f"{name}_list"),
        path(f"{route}new/", create_view.as_view(), name=f"{name}_create"),
        path(f"{route}<int:{pk}>/edit/", update_view.as_view(pk_url_kwarg=pk), name=f"{name}_edit"),
    ]
    if delete_view is not None:
        patterns.append(
            path(f"{route}<int:{pk}>/delete/", delete_view.as_view(pk_url_kwarg=pk), name=f"{name}_delete")
        )
    return patterns


configuration_patterns = [
    path("", configuration.ConfigurationHomeView.as_view(), name="configuration_home"),
    *crud_urls(
        "programs/", "program",
        configuration.ProgramListView, configuration.ProgramCreateView,
        configuration.ProgramUpdateView, configuration.ProgramDeleteView,
    ),
    *crud_urls(
        "locations/", "location",
        configuration.LocationListView, configuration.LocationCreateView,
        configuration.LocationUpdateView, configuration.LocationDeleteView,
    ),
    *crud_urls(
        "chapters/", "chapter",
        configuration.ChapterListView, configuration.ChapterCreateView,
        configuration.ChapterUpdateView, configuration.ChapterDeleteView,
    ),
    *crud_urls(
        "cohorts/", "cohort",
        configuration.CohortListView, configuration.CohortCreateView,
        configuration.CohortUpdateView, configuration.CohortDeleteView,
    ),
    path("cohorts/<int:cohort_id>/manage/", configuration.CohortManageView.as_view(), name="cohort_manage"),
    path(
        "cohorts/<int:cohort_id>/members/<int:membership_id>/toggle/",
        configuration.CohortMemberActionView.as_view(action="toggle"),
        name="cohort_member_toggle",
    ),
    path(
        "cohorts/<int:cohort_id>/members/<int:membership_id>/remove/",
        configuration.CohortMemberActionView.as_view(action="remove"),
        name="cohort_member_remove",
    ),
    path(
        "cohorts/<int:cohort_id>/members/<int:membership_id>/reallocate/",
        configuration.CohortMemberReallocateView.as_view(),
        name="cohort_member_reallocate",
    ),
    path(
        "cohorts/<int:cohort_id>/mentors/allocate/",
        configuration.CohortMentorAllocateView.as_view(),
        name="cohort_mentor_allocate",
    ),
    path(
        "cohorts/<int:cohort_id>/mentors/<int:assignment_id>/remove/",
        configuration.CohortMentorUnassignView.as_view(),
        name="cohort_mentor_unassign",
    ),
    path(
        "cohorts/<int:cohort_id>/timeline/",
        configuration.CohortTimelineView.as_view(),
        name="cohort_timeline",
    ),
    path(
        "cohorts/<int:cohort_id>/activities/new/",
        configuration.CohortActivityCreateView.as_view(),
        name="cohort_activity_create",
    ),
    path(
        "cohorts/<int:cohort_id>/activities/<int:activity_id>/edit/",
        configuration.CohortActivityUpdateView.as_view(),
        name="cohort_activity_edit",
    ),
    path(
        "cohorts/<int:cohort_id>/activities/<int:activity_id>/delete/",
        configuration.CohortActivityDeleteView.as_view(),
        name="cohort_activity_delete",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/new/",
        configuration.CohortTermCreateView.as_view(),
        name="cohort_term_create",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/",
        configuration.CohortTermDetailView.as_view(),
        name="cohort_term_detail",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/edit/",
        configuration.CohortTermUpdateView.as_view(),
        name="cohort_term_edit",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/delete/",
        configuration.CohortTermDeleteView.as_view(),
        name="cohort_term_delete",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/resources/<int:resource_id>/delete/",
        configuration.CohortTermResourceDeleteView.as_view(),
        name="cohort_term_resource_delete",
    ),
    # Term Tasks
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/tasks/new/",
        tasks_questions.CohortTermTaskCreateView.as_view(),
        name="cohort_term_task_create",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/tasks/<int:task_id>/",
        tasks_questions.CohortTermTaskDetailView.as_view(),
        name="cohort_term_task_detail",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/tasks/<int:task_id>/edit/",
        tasks_questions.CohortTermTaskUpdateView.as_view(),
        name="cohort_term_task_edit",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/tasks/<int:task_id>/delete/",
        tasks_questions.CohortTermTaskDeleteView.as_view(),
        name="cohort_term_task_delete",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/tasks/<int:task_id>/submissions/<int:submission_id>/review/",
        tasks_questions.TaskSubmissionReviewView.as_view(),
        name="task_submission_review",
    ),
    # Term Questions
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/questions/new/",
        tasks_questions.CohortTermQuestionCreateView.as_view(),
        name="cohort_term_question_create",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/questions/<int:question_id>/",
        tasks_questions.CohortTermQuestionDetailView.as_view(),
        name="cohort_term_question_detail",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/questions/<int:question_id>/edit/",
        tasks_questions.CohortTermQuestionUpdateView.as_view(),
        name="cohort_term_question_edit",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/questions/<int:question_id>/delete/",
        tasks_questions.CohortTermQuestionDeleteView.as_view(),
        name="cohort_term_question_delete",
    ),
    path(
        "cohorts/<int:cohort_id>/terms/<int:term_id>/questions/<int:question_id>/responses/<int:response_id>/review/",
        tasks_questions.QuestionResponseReviewView.as_view(),
        name="question_response_review",
    ),
    path(
        "permissions/",
        configuration.RolePermissionMatrixView.as_view(),
        name="role_permissions_matrix",
    ),
]

user_patterns = crud_urls(
    "", "platform_user",
    users.PlatformUserListView, users.PlatformUserCreateView, users.PlatformUserUpdateView,
    pk_kwarg="user_id",
)

urlpatterns = [
    path("", auth.login_view, name="login"),
    path("dashboard/", dashboard.AdminDashboardView.as_view(), name="admin_dashboard"),
    path("workspace/", workspace.workspace_home_view, name="workspace_home"),
    path("role-redirect/", auth.role_redirect_view, name="role-redirect"),
    path("logout/", auth.logout_view, name="logout"),
    path("admin/configuration/", include(configuration_patterns)),
    path("admin/users/", include(user_patterns)),
    path("admin/users/<int:user_id>/activity-report/", reports.UserActivityReportDetailView.as_view(), name="user_activity_report"),
    path("admin/users/<int:user_id>/activity-report/new/", reports.UserActivityReportCreateView.as_view(), name="user_activity_report_create"),
    path("admin/users/<int:user_id>/activity-report/<int:report_id>/edit/", reports.UserActivityReportUpdateView.as_view(), name="user_activity_report_edit"),
    path("admin/users/<int:user_id>/activity-report/<int:report_id>/delete/", reports.UserActivityReportDeleteView.as_view(), name="user_activity_report_delete"),
    path("admin/users/<int:user_id>/activity-report/<int:report_id>/review/", reports.UserActivityReportReviewView.as_view(), name="user_activity_report_review"),
    path("admin/audit-log/", configuration.AuditTrailReviewView.as_view(), name="audit_log"),
]
