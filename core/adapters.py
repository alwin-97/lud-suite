from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

from core.roles import role_home_url_name

User = get_user_model()
class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        # Always send them to role_redirect_view instead of connections page
        return "/role-redirect/"

    def pre_social_login(self, request, sociallogin):
        """Link Google account to existing user based on email"""
        if sociallogin.is_existing:
            return  # already linked

        email = sociallogin.account.extra_data.get("email")
        if not email:
            return

        try:
            user = User.objects.get(email=email)  # lookup by email
            sociallogin.connect(request, user)   # connect Google login to this user
        except User.DoesNotExist:
    # Reject login if user not in DB
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("This email is not authorized. Please contact admin.")

class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        return reverse(role_home_url_name(getattr(user, "role", ""), is_superuser=getattr(user, "is_superuser", False)))
