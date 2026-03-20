from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # First, check if the user is logged in
            if not request.user.is_authenticated:
                raise PermissionDenied("You must be logged in to access this page.")

            # Check if any of the user's roles overlap with allowed_roles
            user_roles = getattr(request.user, 'roles', None) or []
            if user_roles and any(r in allowed_roles for r in user_roles):
                return view_func(request, *args, **kwargs)

            # Fallback: check the active role field
            if hasattr(request.user, "role") and request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("You are not allowed to access this page.")
        return _wrapped_view
    return decorator
