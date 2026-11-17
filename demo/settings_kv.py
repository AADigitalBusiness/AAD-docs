"""Django settings for viewing KV documentation with AAD-docs."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path("/home/alejandro/Documents/projects/KV/kv")

SECRET_KEY = "django-insecure-demo-key-for-aad-docs-only"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]

INSTALLED_APPS = [
    "dsadmin",
    "dsadmin.apps.AdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "aad_docs",
    "demo.catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demo.urls"

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

WSGI_APPLICATION = "demo.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
]

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configuración para AAD-docs apuntando a KV
AAD_DOCS = {
    "ROOT": PROJECT_ROOT / "docs",
    "ACCESS": "public",
}

DSADMIN = {
    "SITE_TITLE": "KV Documentation",
    "SITE_HEADER": "KV Production ERP",
    "SITE_SUBHEADER": "Documentation powered by AAD-docs",
    "THEME": "admin",
    "DARK_THEME": None,
}
