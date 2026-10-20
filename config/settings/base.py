from decimal import Decimal
from pathlib import Path
import environ
env = environ.Env()
environ.Env.read_env(Path(__file__).resolve().parent.parent.parent / '.env')

# ═══════════════════════════════════════════════════════════════
# Mode hybride : desktop (SQLite + offline) vs server (PostgreSQL)
# ═══════════════════════════════════════════════════════════════
import os as _os
import sys as _sys

_is_frozen = getattr(_sys, "frozen", False)
_mode = _os.environ.get("GROUPPAY_MODE", "").lower()
_has_db_url = bool(_os.environ.get("DATABASE_URL", "").strip())

# Mode desktop par defaut (dev local, SQLite, ~/.grouppay/)
# Mode serveur si : GROUPPAY_MODE=server OU DATABASE_URL defini (Render, prod)
if _is_frozen:
    IS_DESKTOP = True
elif _mode == "server":
    IS_DESKTOP = False
elif _mode == "desktop":
    IS_DESKTOP = True
else:
    IS_DESKTOP = not _has_db_url
IS_SERVER = not IS_DESKTOP

# Build paths inside the project like this: BASE_DIR / 'subdir'.
if getattr(__import__("sys"), "frozen", False):
    BASE_DIR = Path(__import__("sys")._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Dossier de données utilisateur (survit à une réinstallation)
DATA_DIR = Path.home() / '.grouppay'
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=IS_SERVER)

if IS_DESKTOP:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
    CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1', 'http://localhost']
else:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=['localhost'])
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


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
    "apps.inventory",
    "apps.burkina",
    "apps.sync",
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.access_middleware.AccessControlMiddleware',
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
                'apps.core.context_processors.grouppay_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

if IS_DESKTOP:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': DATA_DIR / 'grouppay.db',
            'OPTIONS': {
                'timeout': 30,
                'init_command': '''
                    PRAGMA journal_mode=WAL;
                    PRAGMA synchronous=NORMAL;
                    PRAGMA busy_timeout=30000;
                    PRAGMA foreign_keys=ON;
                ''',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='grouppay'),
            'USER': env('DB_USER', default='grouppay'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
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
STATIC_ROOT = (DATA_DIR / 'staticfiles') if IS_DESKTOP else (BASE_DIR / 'staticfiles')


# Media files (fichiers uploadés : logos, PDF, exports CSV)

MEDIA_URL = '/media/'
MEDIA_ROOT = (DATA_DIR / 'media') if IS_DESKTOP else (BASE_DIR / 'media')


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
    "generate-monthly-reports": {
        "task": "orders.generate_monthly_reports",
        "schedule": crontab(day_of_month=1, hour=6, minute=0),
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
if IS_DESKTOP:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [env("REDIS_URL", default="redis://localhost:6379/0")]},
        }
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
if IS_DESKTOP:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "grouppay-desktop",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
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


# ============================================================
# WEB PUSH (VAPID)
# ============================================================
# ATTENTION : en production, generer les cles avec :
#   python -c "from py_vapid import Vapid; v = Vapid(); v.generate_keys(); print(v.private_pem().decode()); print(v.public_key_urlsafe_base64())"
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
PUSH_CONTACT_EMAIL = env("PUSH_CONTACT_EMAIL", default="admin@grouppay.app")

# ═══════════════════════════════════════════════════════════════
# MODE HYBRIDE — Config additionnelle
# ═══════════════════════════════════════════════════════════════

# ─── Celery : exécution synchrone en desktop ───
if IS_DESKTOP:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
else:
    CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")

# ─── Sentry (opt-in via SENTRY_DSN) ───
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default=("desktop" if IS_DESKTOP else "production"))

if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            environment=SENTRY_ENVIRONMENT,
            traces_sample_rate=0.0 if IS_DESKTOP else 0.1,
            send_default_pii=False,
        )
    except ImportError:
        pass

# ─── Synchronisation (mode hybride) ───
SYNC_SERVER_URL = env("SYNC_SERVER_URL", default="")
SYNC_API_KEY = env("SYNC_API_KEY", default="")
SYNC_ENABLED = env.bool("SYNC_ENABLED", default=False)

if IS_DESKTOP and SYNC_SERVER_URL and SYNC_API_KEY:
    SYNC_ENABLED = True


# ─── Support DATABASE_URL (Render, Fly, Heroku) ───
if IS_SERVER:
    import dj_database_url
    _db_url = env("DATABASE_URL", default="")
    if _db_url:
        DATABASES["default"] = dj_database_url.parse(_db_url, conn_max_age=600)
        DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

# ─── WhiteNoise : servir les statiques en prod ───
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# ═══════════════════════════════════════════════════════════════
# SPÉCIFICITÉS BURKINA FASO
# ═══════════════════════════════════════════════════════════════
GROUPPAY_COUNTRY = env("GROUPPAY_COUNTRY", default="BF")
GROUPPAY_CURRENCY = "XOF"
GROUPPAY_CURRENCY_SYMBOL = "FCFA"
GROUPPAY_LOCALE = "fr-BF"

# Fiscalité
GROUPPAY_TVA_RATE = Decimal("0.18")           # TVA standard BF
GROUPPAY_TVA_REDUIT = Decimal("0.11")          # TVA réduite (prestations)
GROUPPAY_TVA_EXO = Decimal("0.00")
GROUPPAY_IUTS_ANNEE = 2024
GROUPPAY_SMIG = 45000                          # SMIG mensuel FCFA
GROUPPAY_CNSS_PLAFOND = 600000                 # Plafond cotisable FCFA

# Devise par défaut
DEFAULT_CURRENCY = "XOF"
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = " "
USE_THOUSAND_SEPARATOR = True

# Mentions légales BF (à personnaliser par organisation)
GROUPPAY_LEGAL = {
    "pays": "Burkina Faso",
    "devise_iso": "XOF",
    "tva_standard": 18,
    "mention_facture": "Facture émise conformément au Code Général des Impôts du Burkina Faso",
    "mention_tva": "TVA acquittée — IFU et RCCM disponibles sur demande",
}



# ═══════════════════════════════════════════════════════════════
# FASO ARZEKA — Plateforme nationale de paiements (BF)
# https://my.fasoarzeka.bf  |  USSD *700#
# ═══════════════════════════════════════════════════════════════
FASOARZEKA = {
    "ENABLED": env.bool("FASOARZEKA_ENABLED", default=False),
    "USERNAME": env("FASOARZEKA_USERNAME", default=""),
    "PASSWORD": env("FASOARZEKA_PASSWORD", default=""),
    "MERCHANT_ID": env("FASOARZEKA_MERCHANT_ID", default=""),
    "HASH_SECRET": env("FASOARZEKA_HASH_SECRET", default=""),
    "WEBHOOK_URL": env("FASOARZEKA_WEBHOOK_URL",
                       default="https://grouppay.bf/webhook/fasoarzeka/"),
    "RETURN_URL": env("FASOARZEKA_RETURN_URL",
                      default="https://grouppay.bf/retour-paiement/"),
    "PROTOCOL": env("FASOARZEKA_PROTOCOL", default="https"),
    "SANDBOX": env.bool("FASOARZEKA_SANDBOX", default=True),
}
