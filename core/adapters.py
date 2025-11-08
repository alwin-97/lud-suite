from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from allauth.account.adapter import DefaultAccountAdapter

User = get_user_model()
class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        # Always send them to role_redirect_view instead of connections page
        return "/role-redirect/"

class SocialAccountAdapter(DefaultSocialAccountAdapter):
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
        if user.role == "admin":
            return "/admin-dashboard/"
        elif user.role == "mentor":
            return "/dashboard/"
        elif user.role == "endorser":
            return "/endorser-dashboard/"
        else:
            return "/"  # fallback