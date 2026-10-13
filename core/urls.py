from django.urls import include, path

from core.views import auth, configuration, dashboard, users, workspace


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
]
