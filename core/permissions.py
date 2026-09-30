"""The single access rule for views: function views use @admin_required,
class-based views use AdminRequiredMixin / RoleRequiredMixin."""
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def check_access(request, *, admin_only=False, required_roles=()):
    """Return a login redirect for anonymous users, raise PermissionDenied when
    the user lacks access, or return None when the request may proceed."""
    user = request.user
    if not user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if admin_only and not user.is_platform_admin:
        raise PermissionDenied
    if required_roles and not set(required_roles) & set(user.active_role_codes):
        raise PermissionDenied
    return None


class RoleRequiredMixin:
    """Grant access when the user holds any of required_roles in an active cohort."""

    admin_only = False
    required_roles = ()

    def dispatch(self, request, *args, **kwargs):
        denied = check_access(
            request,
            admin_only=self.admin_only,
            required_roles=self.required_roles,
        )
        if denied is not None:
            return denied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    admin_only = True
