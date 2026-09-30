from django import template

from core.navigation import ADMIN_NAV

register = template.Library()


@register.inclusion_tag("components/shell/sidebar.html", takes_context=True)
def admin_sidebar(context, items=None):
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    current = match.url_name if match else None
    return {"items": [item.resolve(current) for item in (items or ADMIN_NAV)]}
