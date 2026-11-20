"""Minimal Django settings (test project - not for production)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-test-only")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = ["django.contrib.staticfiles"]
MIDDLEWARE = []
ROOT_URLCONF = "mysite.urls"
TEMPLATES = []
WSGI_APPLICATION = "mysite.wsgi.application"
DATABASES = {}
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
