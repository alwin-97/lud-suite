from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allow Google sign-in only for an existing administrator account."""

    def is_open_for_signup(self, request, sociallogin):
        return False

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user if sociallogin.is_existing else None

        if user is None:
            email = (
                sociallogin.account.extra_data.get("email")
                or sociallogin.user.email
                or ""
            ).strip()
            if email:
                user = get_user_model().objects.filter(email__iexact=email).first()

        if user is None or not user.is_platform_admin:
            raise PermissionDenied(
                "This Google account is not authorized for administrator access."
            )

        if not sociallogin.is_existing:
            sociallogin.connect(request, user)

    def get_connect_redirect_url(self, request, socialaccount):
        return "/dashboard/"


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False

    def get_login_redirect_url(self, request):
        if request.user.is_platform_admin:
            return "/dashboard/"
        raise PermissionDenied("Administrator access is required.")
