from functools import wraps

from core.permissions import check_access


def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        denied = check_access(request, admin_only=True)
        if denied is not None:
            return denied
        return view_func(request, *args, **kwargs)

    return wrapped_view
