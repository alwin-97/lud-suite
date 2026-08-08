from django.urls import path

from core.views import (
    admin_dashboard_view,
    login_view,
    logout_view,
    role_redirect_view,
)


urlpatterns = [
    path("", login_view, name="login"),
    path("dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("role-redirect/", role_redirect_view, name="role-redirect"),
    path("logout/", logout_view, name="logout"),
]
