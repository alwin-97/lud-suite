from django.urls import path

from core import views


urlpatterns = [
    path("", views.login_view, name="login"),
    path("dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("workspace/", views.workspace_home_view, name="workspace_home"),
    path("role-redirect/", views.role_redirect_view, name="role-redirect"),
    path("logout/", views.logout_view, name="logout"),
    path("admin/configuration/", views.configuration_home_view, name="configuration_home"),
    path("admin/configuration/locations/", views.location_list_view, name="location_list"),
    path("admin/configuration/locations/new/", views.location_create_view, name="location_create"),
    path("admin/configuration/locations/<int:location_id>/edit/", views.location_edit_view, name="location_edit"),
    path("admin/configuration/locations/<int:location_id>/delete/", views.location_delete_view, name="location_delete"),
    path("admin/configuration/chapters/", views.chapter_list_view, name="chapter_list"),
    path("admin/configuration/chapters/new/", views.chapter_create_view, name="chapter_create"),
    path("admin/configuration/chapters/<int:chapter_id>/edit/", views.chapter_edit_view, name="chapter_edit"),
    path("admin/configuration/chapters/<int:chapter_id>/delete/", views.chapter_delete_view, name="chapter_delete"),
    path("admin/configuration/cohorts/", views.cohort_list_view, name="cohort_list"),
    path("admin/configuration/cohorts/new/", views.cohort_create_view, name="cohort_create"),
    path("admin/configuration/cohorts/<int:cohort_id>/edit/", views.cohort_edit_view, name="cohort_edit"),
    path("admin/configuration/cohorts/<int:cohort_id>/delete/", views.cohort_delete_view, name="cohort_delete"),
    path("admin/users/", views.platform_user_list_view, name="platform_user_list"),
    path("admin/users/new/", views.platform_user_create_view, name="platform_user_create"),
    path("admin/users/<int:user_id>/edit/", views.platform_user_edit_view, name="platform_user_edit"),
]
