import os

from .local_settings import (
    SECRET_KEY, DEBUG, ALLOWED_HOSTS, DB_CONFIG,
    TEMPLATES_DIR, STATICFILES_DIR, STATIC_DIR, MEDIA_DIR, LOGS_DIR,
    EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
)
from Server_dev.logging import LOGGING

# Build paths inside the project like this: BASE_DIR / 'subdir'
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SETTINGS_DIR)

# Optional: Allow overriding via environment
TEMPLATES_DIR = os.getenv('TEMPLATES_DIR', TEMPLATES_DIR)
STATICFILES_DIR = os.getenv('STATICFILES_DIR', STATICFILES_DIR)
STATIC_DIR = os.getenv('STATIC_DIR', STATIC_DIR)
MEDIA_DIR = os.getenv('MEDIA_DIR', MEDIA_DIR)
LOGS_DIR = os.getenv('LOGS_DIR', LOGS_DIR)

# ======================
# Core Django Settings
# ======================

SECRET_KEY = SECRET_KEY
DEBUG = DEBUG
ALLOWED_HOSTS = ALLOWED_HOSTS

# ======================
# Custom User Model
# ======================
AUTH_USER_MODEL = 'Auth.CustomUser'

# ======================
# Login / Logout Redirects
# ======================
LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = 'devops:dashboard'  # Assuming namespaced URL
LOGOUT_REDIRECT_URL = 'login'
SOCIALACCOUNT_LOGIN_ON_GET = True  # Redirect to the login page after successful login

# ======================
# Applications
# ======================
INSTALLED_APPS = [
    'jazzmin',  # Admin theme (install via pip)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required by allauth

    # Third-party
    'django_extensions',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',  # Example provider
    'allauth.socialaccount.providers.github',

    # Your apps
    'Auth',       # CustomUser model likely here
    'DevOps', 
    'collaboration',
    'System',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required by allauth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Server_dev.urls'

# ======================
# Templates
# ======================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Add custom dirs like [BASE_DIR / 'templates'] if needed
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # ❌ Remove deprecated allauth context processors:
                # 'allauth.account.context_processors.account',
                # 'allauth.socialaccount.context_processors.socialaccount',
            ],
        },
    },
]

WSGI_APPLICATION = 'Server_dev.wsgi.application'

# ======================
# Database
# ======================
DATABASES = {
    'default': os.getenv('DB_CONFIG', DB_CONFIG)  # Usually a dict from local_settings.py
}

# ======================
# Password Validation
# ======================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ======================
# Internationalization
# ======================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ======================
# Authentication & Allauth (Fixed)
# ======================
AUTHENTICATION_BACKENDS = [
    'allauth.account.auth_backends.AuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

SITE_ID = 1

# ✅ Correct & Modern Settings (No Deprecations)
ACCOUNT_LOGIN_METHODS = {'email'}  # ✅ Only allow login with email
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1', 'password2']  # ✅ email* = required & used for login

# ✅ Correct & Modern Settings (No Deprecations)
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # Changed from ACCOUNT_LOGIN_METHODS
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'

ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',
}

# ======================
# Social Account Providers (e.g., Google)
# ======================
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    },
    'github': {
        'SCOPE': [
            'user:email',
        ],
        'VERIFIED_EMAIL': True,
    }
}

# Add these social account settings
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_STORE_TOKENS = True  # Store OAuth tokens for later use

# Optional: Additional allauth settings
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False  # Don't require email confirmation during signup
ACCOUNT_SESSION_REMEMBER = True  # Remember user sessions
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5  # Limit login attempts
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300  # 5 minutes timeout
# ======================
# Email Configuration (SMTP)
# ======================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = EMAIL_HOST_USER         # From local_settings.py or env
EMAIL_HOST_PASSWORD = EMAIL_HOST_PASSWORD  # App password if 2FA enabled
DEFAULT_FROM_EMAIL = DEFAULT_FROM_EMAIL    # e.g. noreply@example.com

# ======================
# Static & Media
# ======================
STATIC_URL = '/static/'
STATIC_ROOT = STATIC_DIR  # For collectstatic (prod)

STATICFILES_DIRS = [STATICFILES_DIR]  # Optional dev static files folder

MEDIA_URL = '/media/'
MEDIA_ROOT = MEDIA_DIR

# ======================
# Logging
# ======================
if os.getenv('DISABLE_LOGGING', False):  # e.g., for CI/CD
    LOGGING_CONFIG = None
LOGGING = LOGGING  # Imported from Server_dev.logging

# ======================
# Default Auto Field
# ======================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'