from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Allow Google sign-in only for users provisioned by an administrator."""

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

        if user is None or not user.is_authorized_user:
            raise PermissionDenied(
                "This Google account has not been provisioned for platform access."
            )

        if not sociallogin.is_existing:
            sociallogin.connect(request, user)

    def get_connect_redirect_url(self, request, socialaccount):
        return "/role-redirect/"


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False

    def get_login_redirect_url(self, request):
        if request.user.is_authorized_user:
            return "/role-redirect/"
        raise PermissionDenied("This account is not authorized for platform access.")
