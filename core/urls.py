from django.urls import path
from . import views
from .views import login_view, dashboard_view
from core import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
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
]
