from pathlib import Path
import environ
env = environ.Env()
environ.Env.read_env(Path(__file__).resolve().parent.parent.parent / '.env')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "apps.core",
    "apps.organizations",
    "apps.accounts",
    "apps.catalog",
    "apps.orders",
    "apps.deductions",
    "apps.documents",
    "apps.deliveries",
    "apps.notifications",
    "channels",
    "apps.audit",
    "apps.da",
    "django_otp",
    "django_otp.plugins.otp_totp",
]

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 30,                    # 30s avant "database is locked"
            'init_command': '''
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA busy_timeout=30000;
                PRAGMA foreign_keys=ON;
            ''',
        },
    }
}

# Sessions en cache (évite les écritures SQLite à chaque requête)
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"



# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Media files (fichiers uploadés : logos, PDF, exports CSV)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# E003 : Django veut USERNAME_FIELD unique globalement.
# Ici l'unicité est garantie par organization+email (contrainte composite) — volontaire, pas un oubli.
SILENCED_SYSTEM_CHECKS = ["auth.E003"]


# --- Celery Beat Schedule ---
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-carts": {
        "task": "orders.cleanup_expired_carts",
        "schedule": crontab(hour=3, minute=0),
    },
    "send-abandoned-cart-reminders": {
        "task": "orders.send_abandoned_cart_reminders",
        "schedule": crontab(hour=10, minute=0),
    },
    "check-low-stock-alerts": {
        "task": "catalog.check_low_stock_alerts",
        "schedule": crontab(hour=8, minute=0),
    },
    "cleanup-expired-deductions": {
        "task": "deductions.cleanup_expired_transmissions",
        "schedule": crontab(hour=4, minute=0),
    },
}


# --- OpenAPI / Swagger ---
SPECTACULAR_SETTINGS = {
    "TITLE": "GroupPay API",
    "DESCRIPTION": "Plateforme d'achat groupé sur retenue salariale",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ============================================================
# Django Channels (WebSocket notifications)
# ============================================================
ASGI_APPLICATION = "config.asgi.application"

# InMemory pour dev — remplacer par channels_redis en prod
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Daphne comme serveur ASGI par défaut (dev)
if "daphne" in INSTALLED_APPS:
    try:
        # 'daphne' doit être le 1er de INSTALLED_APPS pour prendre le runserver
        INSTALLED_APPS.remove("daphne")
        INSTALLED_APPS.insert(0, "daphne")
    except ValueError:
        pass


# ============================================================
# Cache (LocMem pour dev — Redis en prod)
# ============================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "grouppay-default",
    }
}


# ============================================================
# EMAIL & SITE
# ============================================================
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="GroupPay <noreply@grouppay.app>")

# Dev = console, prod = SMTP
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="smtp.sendgrid.net")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="apikey")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")


# ============================================================
# SMS (Africa's Talking) — optionnel
# ============================================================
AFRICASTALKING_USERNAME = env("AFRICASTALKING_USERNAME", default="")
AFRICASTALKING_API_KEY = env("AFRICASTALKING_API_KEY", default="")


# ============================================================
# 2FA (django-otp)
# ============================================================
OTP_TOTP_ISSUER = env("OTP_TOTP_ISSUER", default="GroupPay")
OTP_LOGIN_URL = "/accounts/2fa/verify/"


# ============================================================
# SIGNATURE NUMERIQUE DA
# ============================================================
DA_OTP_EXPIRY_MINUTES = env.int("DA_OTP_EXPIRY_MINUTES", default=10)
DA_OTP_MAX_ATTEMPTS = env.int("DA_OTP_MAX_ATTEMPTS", default=3)
DA_SIGNATURE_LEVEL_DEFAULT = env("DA_SIGNATURE_LEVEL_DEFAULT", default="PIN_OTP")

DA_THRESHOLD_DIRECTOR = env.int("DA_THRESHOLD_DIRECTOR", default=500_000)
DA_THRESHOLD_DG = env.int("DA_THRESHOLD_DG", default=2_000_000)


# ============================================================
# PARRAINAGE
# ============================================================
REFERRAL_REWARD_AMOUNT = env.int("REFERRAL_REWARD_AMOUNT", default=5000)
