"""
Django settings for dle project.

Generated by 'django-admin startproject' using Django 4.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
import ssl
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

import environ


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# can override settings in .env, see .env.example
env = environ.Env()
# environ.Env.read_env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
if "pytest" in sys.modules:
    print("Running for pytest ...")
    environ.Env.read_env(os.path.join(BASE_DIR, "tests/test.env"))

STATIC_ROOT = os.path.join(BASE_DIR, "static/")

MEDIA_ROOT = BASE_DIR / "media"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "/static/"

NLP_MODELS = os.path.join(BASE_DIR, "api/bert_models")

# Hosts and CIDR (AWS subnets)
try:
    ALLOWED_HOSTS = [
        "druglabelexplorer.org",
        "www.druglabelexplorer.org",
        "127.0.0.1",
        "localhost",
        "testserver",
    ] + env.list("ALLOWED_HOSTS")
except ImproperlyConfigured:
    ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]
try:
    ALLOWED_CIDR_NETS = env.list("ALLOWED_CIDR_NETS")
    print(f"ALLOWED_CIDR_NETS: {ALLOWED_CIDR_NETS}")
except ImproperlyConfigured:
    print("Allowed CIDR Nets is not set")

# Deployment checklist
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", False)
LOG_LEVEL = env.str("LOG_LEVEL", "INFO")

TESTS = env.bool("TESTS", False)

LOGIN_URL = "/users/login/"

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "elasticsearch_django",
    "django_extensions",
    "users",
    "data",
    "compare",
    "api",
    "search",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "allow_cidr.middleware.AllowCIDRMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "dle.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

FIXTURE_DIRS = [os.path.join(BASE_DIR, "tests/fixtures")]

WSGI_APPLICATION = "dle.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ENGINE"] = ("django.db.backends.postgresql",)

# override host for CI process
if os.environ.get("GITHUB_WORKFLOW"):
    DATABASES["default"]["HOST"] = "127.0.0.1"

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

USE_L10N = True

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,  # the dictConfig format version
    "disable_existing_loggers": False,  # retain the default loggers
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "formatters": {
        "simple": {
            "format": "{asctime} {levelname} {message}",
            "style": "{",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

# Elasticsearch
SEARCH_SETTINGS = {
    "connections": {
        "default": {
            "hosts": env.str("ELASTICSEARCH_URL"),
            "verify_certs": True,
            "http_auth": (env.str("ELASTICSEARCH_USER"), env.str("ELASTIC_PASSWORD")),
            "ssl_version": ssl.TLSVersion.TLSv1_2,
            "ca_certs": "/usr/share/elasticsearch/config/certs/ca/ca.crt",
            "timeout": 180,
        }
    },
    "indexes": {
        "productsection": {
            "models": [
                "data.ProductSection",
            ]
        },
    },
    "settings": {
        # batch size for ES bulk api operations
        # timed out at 500 and 100 and 25 on BERT - was taking ~15 to ~28s per vectorization task so needed 3min timeout and batch size of 5 for that to work
        "chunk_size": 500,
        # default page size for search results
        "page_size": 25,
        # set to True to connect post_save/delete signals
        # If this is True, it will automatically try to sync ES with Django as data is loaded; if False, you must manually sync
        "auto_sync": env.bool("ES_AUTO_SYNC", False),
        # List of models which will never auto_sync even if auto_sync is True
        "never_auto_sync": [],
        # if true, then indexes must have mapping files
        "strict_validation": False,
        "mappings_dir": os.path.join(BASE_DIR, "search/mappings"),
    },
}
