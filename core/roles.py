ROLE_CHOICES = (
    ("admin", "Admin"),
    ("endorser", "Endorser"),
    ("mentor", "Mentor"),
    ("mentee", "Mentee"),
    ("volunteer", "Volunteer"),
)

ROLE_LABELS = dict(ROLE_CHOICES)
ROLE_KEYS = [key for key, _ in ROLE_CHOICES]

REVIEWER_ROLES = ("mentor", "endorser")
REVIEW_ACCESS_ROLES = REVIEWER_ROLES + ("admin",)
MENTEE_OVERSIGHT_ROLES = ("mentor", "admin")
DIRECT_MENTOR_REVIEW_ROLES = ("mentor", "admin")

NOTIFICATION_TARGET_CHOICES = ROLE_CHOICES + (("all", "All Users"),)

ROLE_LAYOUTS = {
    "admin": {"base_template": "core/admin/base_admin.html", "home_url_name": "admin_dashboard"},
    "mentor": {"base_template": "core/mentor/base_mentor.html", "home_url_name": "dashboard"},
    "mentee": {"base_template": "core/mentee/base_mentee.html", "home_url_name": "mentee_dashboard"},
    "endorser": {"base_template": "core/endorser/base_endorser.html", "home_url_name": "endorser_dashboard"},
    "volunteer": {"base_template": "core/mentor/base_mentor.html", "home_url_name": "volunteer_dashboard"},
}


def role_layout(role):
    return ROLE_LAYOUTS.get(
        role,
        {"base_template": "core/mentor/base_mentor.html", "home_url_name": "profile"},
    )


def role_home_url_name(role, is_superuser=False):
    if role:
        return role_layout(role)["home_url_name"]
    if is_superuser:
        return "admin_dashboard"
    return "profile"
