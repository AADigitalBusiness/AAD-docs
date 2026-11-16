"""
Test settings for AAD-docs.

Minimal Django settings for running tests.
"""

SECRET_KEY = "test-secret-key"
DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "aad_docs",
]

ROOT_URLCONF = "tests.urls"

USE_I18N = True
LANGUAGE_CODE = "en"

AAD_DOCS = {
    "ACCESS": "public",
    "SHOW_TREE": True,
}

# For Node import test without Django
import sys
sys.modules["django"] = type(sys)("django")
sys.modules["django.conf"] = type(sys)("django.conf")
sys.modules["django.conf.settings"] = type(sys)("settings")
