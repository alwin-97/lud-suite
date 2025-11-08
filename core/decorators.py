from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # First, check if the user is logged in
            if not request.user.is_authenticated:
                return HttpResponseForbidden("You must be logged in to access this page.")

            # Then, check if the user has a role and if it's allowed
            if hasattr(request.user, "role") and request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("You are not allowed to access this page.")
        return _wrapped_view
    return decorator
