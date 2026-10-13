"""Sidebar navigation, declared once and rendered by {% admin_sidebar %}.

Active state is decided by URL name (never by request.path): an item is active
when the current url_name equals its url_name or starts with match_prefix.
A group is open when it or any child is active.
"""
from dataclasses import dataclass, field

from django.urls import reverse


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    icon: str = ""  # Flaticon UIcons regular-rounded name, e.g. "apps" -> fi-rr-apps
    match_prefix: str = ""
    children: tuple = field(default_factory=tuple)

    def is_active(self, current):
        if not current:
            return False
        if current == self.url_name:
            return True
        return bool(self.match_prefix) and current.startswith(self.match_prefix)

    def resolve(self, current):
        children = [child.resolve(current) for child in self.children]
        active = self.is_active(current) or any(child["active"] for child in children)
        return {
            "label": self.label,
            "url": reverse(self.url_name),
            "icon": self.icon,
            "active": active,
            "children": children,
        }


ADMIN_NAV = (
    NavItem("Dashboard", "admin_dashboard", icon="apps"),
    NavItem(
        "Configuration",
        "configuration_home",
        icon="settings-sliders",
        children=(
            NavItem("Programs", "program_list", match_prefix="program_"),
            NavItem("Locations", "location_list", match_prefix="location_"),
            NavItem("Chapters", "chapter_list", match_prefix="chapter_"),
            NavItem("Cohorts", "cohort_list", match_prefix="cohort_"),
        ),
    ),
    NavItem("Users", "platform_user_list", icon="users", match_prefix="platform_user_"),
)
