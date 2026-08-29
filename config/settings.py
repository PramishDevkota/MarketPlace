"""
Django settings for Islington Marketplace.
"""

import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-vx!0!*p&z$fawjgyd@r-v0v70grzf!(-c(i87qwq#ndwbwmmpy')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,.vercel.app',
    cast=Csv()
)
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'accounts',
    'marketplace',
    'orders',
    'messaging',
    'reviews',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'marketplace:home'
LOGOUT_REDIRECT_URL = '/'

GEMINI_API_KEY = config('GEMINI_API_KEY', default='')

KHALTI_INITIATE_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"
KHALTI_LOOKUP_URL = "https://dev.khalti.com/api/v2/epayment/lookup/"
KHALTI_SECRET_KEY = config('KHALTI_SECRET_KEY', default='')
KHALTI_PUBLIC_KEY = config('KHALTI_PUBLIC_KEY', default='')

JAZZMIN_SETTINGS = {
    'site_title': 'Islington Marketplace Admin',
    'site_header': 'Islington Marketplace',
    'site_brand': 'Islington Marketplace',
    'site_footer': 'Islington Marketplace Administration',
    'welcome_sign': 'Welcome to Islington Marketplace Admin',
    'copyright': 'Islington Marketplace Ltd',
    'site_logo': None,
    'site_logo_classes': None,
    'site_icon': None,
    'navigation_expanded': True,
    'order_with_respect_to': [
        'accounts',
        'marketplace',
        'orders',
        'messaging',
        'reviews',
    ],
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.User': 'fas fa-user',
        'auth.Group': 'fas fa-users',
        'accounts.UserProfile': 'fas fa-id-card',
        'accounts.SellerRequest': 'fas fa-store',
        'marketplace.Category': 'fas fa-tags',
        'marketplace.Product': 'fas fa-box',
        'orders.Order': 'fas fa-shopping-cart',
        'reviews.Review': 'fas fa-star',
        'messaging.Conversation': 'fas fa-comments',
        'messaging.Message': 'fas fa-envelope',
    },
    'default_icon_parents': 'fas fa-folder',
    'default_icon_children': 'fas fa-circle',
    'related_modal_active': True,
    'custom_css': None,
    'custom_js': None,
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {
        'auth.User': 'vertical_tabs',
        'auth.Group': 'vertical_tabs',
    },
    'topmenu_links': [
        {'name': 'Main Site', 'url': '/', 'new_window': False, 'icon': 'fas fa-globe'},
        {'name': 'Dashboard', 'url': 'admin:index', 'icon': 'fas fa-tachometer-alt'},
    ],
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': False,
    'accent': 'accent-primary',
    'navbar': 'navbar-dark',
    'no_navbar_border': False,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-dark-primary',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': True,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    'theme': 'default',
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}
