from django.urls import path
from . import views
from django.contrib.auth import views as auth_views



urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dip-yclp/', views.dip_yclp_view, name='dip_yclp'),
    path('dip-mentee/', views.dip_mentee_view, name='dip_mentee'),
    path('profile/', views.profile_view, name='profile'),
    path('work-diary/', views.work_diary_view, name='work_diary'),
    path('repository/', views.repository_view, name='repository'),
    path('notification/', views.notification_view, name='notification'),
    path('transcript/', views.transcript_view, name='transcript'),
    path('settings/', views.settings_view, name='settings'),
    path('new-activity/', views.new_activity, name='new_activity'),
    path('my-activities/', views.my_activities_view, name='my-activities'),
    path("role-redirect/", views.role_redirect_view, name="role-redirect"),
    path("admin-dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("manage-user/", views.manage_user_view, name="manage_user"),
    path("add-user/", views.add_user_view, name="add_user"),
    path("edit-user/<int:user_id>/", views.edit_user_view, name="edit_user"),
    path("delete-user/<int:user_id>/", views.delete_user_view, name="delete_user"),
    path('manage-assignment/', views.manage_assignment, name='manage_assignment'),
    path('user/<int:user_id>/view/', views.view_user, name='view_user'),
    path('users/<int:user_id>/export/', views.export_user_activities_excel, name='export_user_activities'),
    path('users/bulk-upload/', views.bulk_upload_users_view, name='bulk_upload_users'),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path('endorser-dashboard/', views.endorser_dashboard, name='endorser_dashboard'),
    path('endorser/work-schedule/', views.endorser_work_schedule, name='endorser_work_schedule'),
    path('endorser/profile/', views.endorser_profile, name='endorser_profile'),
    path('endorser/profile/edit/', views.endorser_edit_profile, name='endorser_edit_profile'),
    path('download-user-template/', views.download_user_template, name='download_user_template'),
    path('get-assigned-mentors/', views.get_assigned_mentors, name='get_assigned_mentors'),
    path('assign-mentors/', views.assign_mentors, name='assign_mentors'),
    path('unassign-mentor/', views.unassign_mentor, name='unassign_mentor'),
]
