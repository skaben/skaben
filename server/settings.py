"""
Django settings for SKABEN project
"""

import os

from django.core.management.utils import get_random_secret_key

# основные настройки проекта

ENVIRONMENT = os.environ.get("ENVIRONMENT", "")

if not ENVIRONMENT:
    raise ValueError("Environment not set!")

DEBUG = False
if not ENVIRONMENT.startswith("prod"):
    DEBUG = True

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = get_random_secret_key()

# urls

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", [])
DEFAULT_DOMAIN = os.environ.get("DEFAULT_DOMAIN", "http://127.0.0.1")
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1")
API_URL = os.environ.get("DJANGO_API_URL", "http://127.0.0.1/api")

STATIC_URL = "static/"
STATIC_ROOT = "/static/"

MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "/media/")

ROOT_URLCONF = "core.urls"

# CORS

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = False
CORS_ORIGIN_WHITELIST = [
    "http://127.0.0.1:8080",
    "http://127.0.0.1:15674",
    "http://192.168.0.254",
    "http://192.168.0.254:8080",
    "http://skaben",
    "http://skaben:8080",
]

# APPLICATIONS

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "polymorphic",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "django_extensions",
    "alert",
    "assets",
    "core",
    "streams",
    "peripheral_devices",
    "peripheral_behavior",
    "admin_extended",
    "drf_spectacular",
    "drf_spectacular_sidecar",
]

MIDDLEWARE = [
    "core.middleware.auth_middleware.AuthRequiredMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "server", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT", 5432),
        "PASSWORD": os.environ.get("DB_PASS"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# AUTHENTICATION

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# TIMEZONE + I18

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# CACHE

CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache_table"}}

# DRF

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.TokenAuthentication",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SKABEN API",
    "DESCRIPTION": "SKABEN Dungeon API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# FORMATS AND ASSETS

MACADDRESS_DEFAULT_DIALECT = "netaddr.mac_eui48"
AUDIO_ASSET_MAX_SIZE = 30  # MB
VIDEO_ASSET_MAX_SIZE = 120  # MB
IMAGE_ASSET_MAX_SIZE = 5  # MB

# LOGGING

LOGGING_LEVEL = "INFO" if not DEBUG else "DEBUG"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s :: <%(filename)s:%(lineno)s - " "%(funcName)s()>  %(levelname)s > %(message)s"
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "queue_handlers": {
        "console": {"level": LOGGING_LEVEL, "class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {"queue_handlers": ["console"], "level": LOGGING_LEVEL, "propagate": True},
        "django.db.backends": {
            "level": "INFO",
            "queue_handlers": ["console"],
        },
        "django.utils": {
            "level": "INFO",
            "queue_handlers": ["console"],
        },
    },
}

# REDIS

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

# RABBITMQ

RABBITMQ_USER = os.environ.get("RABBITMQ_USERNAME")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASSWORD")
AMQP_URI = f"pyamqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@rabbitmq:5672"
AMQP_TIMEOUT = 10
EXCHANGE_CHOICES = [("mqtt", "mqtt"), ("internal", "internal")]
MAX_CHANNEL_NAME_LEN = 64
RESPONSE_TIMEOUT = {"ask": 10, "ping": 10, "client_update": 30}
ASK_QUEUE = "ask"

# SCHEDULER

SCHEDULER_TASK_TIMEOUT = 10

# INGAME SETTINGS

ACCESS_CODE_CARD_LEN = 6
DEVICE_KEEPALIVE_TIMEOUT = 60

PWR_STATE_DISPATCH_TABLE = {"aux": "cyan", "on": "green"}

ALERT_COOLDOWN = {"increase": 60, "decrease": 120}

# DEBUG

if DEBUG:
    ALLOWED_HOSTS = ["*"]
    REST_FRAMEWORK = REST_FRAMEWORK | {
        "DEFAULT_AUTHENTICATION_CLASSES": [],
        "DEFAULT_PERMISSION_CLASSES": [],
        "UNAUTHENTICATED_USER": None,
    }
    MEDIA_URL = "media/"
