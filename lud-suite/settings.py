import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-development-only-change-me",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
if not DEBUG and SECRET_KEY == "django-insecure-development-only-change-me":
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable must be set when DJANGO_DEBUG is false."
    )
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.forms',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Your app
    'core',

    # Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lud-suite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.app_version',
            ],
        },
    },
]

WSGI_APPLICATION = 'lud-suite.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Localization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------- Authentication ----------------
AUTH_USER_MODEL = "core.CustomUser"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",            # Django default
    "allauth.account.auth_backends.AuthenticationBackend",  # Allauth
]

SITE_ID = 1

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = "admin_dashboard"
LOGOUT_REDIRECT_URL = '/'
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = "none"

# Allauth settings
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_SIGNUP_FORM_CLASS = None

# Adapters
ACCOUNT_ADAPTER = "core.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "core.adapters.SocialAccountAdapter"

SOCIALACCOUNT_AUTO_SIGNUP = False

ACCOUNT_SIGNUP_REDIRECT_URL = '/'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
