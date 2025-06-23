import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Database settings
PG_USER = os.environ.get("PG_USER", "postgres")

# Use a unique database name for testing
TEST_DB_NAME = "django_postgres_copy_test"

DATABASES = {
    "default": {
        "HOST": "localhost",
        "PORT": 5432,
        "NAME": TEST_DB_NAME,
        "USER": PG_USER,
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "TEST": {
            "NAME": TEST_DB_NAME,
        },
    },
    "other": {
        "HOST": "localhost",
        "PORT": 5432,
        "NAME": "postgres",
        "USER": PG_USER,
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "TEST": {
            "NAME": "django_postgres_copy_test_other",
        },
    },
    "sqlite": {
        "NAME": "sqlite",
        "ENGINE": "django.db.backends.sqlite3",
        "TEST": {
            "NAME": "django_postgres_copy_test_sqlite",
        },
    },
    "secondary": {
        "HOST": "localhost",
        "PORT": 5432,
        "NAME": "postgres",
        "USER": PG_USER,
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "TEST": {
            "NAME": "django_postgres_copy_test_secondary",
        },
    },
}

# Application definition
INSTALLED_APPS = [
    "tests",
]

# Database router
DATABASE_ROUTERS = ["tests.test_router.CustomRouter"]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "tests.log",
        },
    },
    "formatters": {
        "verbose": {
            "format": "%(levelname)s|%(asctime)s|%(module)s|%(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        }
    },
    "loggers": {
        "postgres_copy": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

# Secret key (required for Django but not used in tests)
SECRET_KEY = "django-insecure-test-key-not-used-in-production"

# Required Django settings (not used in tests)
DEBUG = True
ALLOWED_HOSTS = []
MIDDLEWARE = []
ROOT_URLCONF = "tests.urls"
TEMPLATES = []
WSGI_APPLICATION = ""
