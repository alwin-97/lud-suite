from core.views.common import role_layout_context


def role_shell(request):
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return {}
    return role_layout_context(user)
