import os
from pathlib import Path
from django.conf import settings

ROOT_DIR = Path(__file__).parent.parent
PG_USER = os.environ.get("PG_USER", "postgres")


def pytest_configure():
    settings.configure(
        DATABASES={
            "default": {
                "HOST": "localhost",
                "PORT": 5432,
                "NAME": "test",
                "USER": PG_USER,
                "ENGINE": "django.db.backends.postgresql_psycopg2",
            },
            "other": {
                "HOST": "localhost",
                "PORT": 5432,
                "NAME": "test_alternative",
                "USER": PG_USER,
                "ENGINE": "django.db.backends.postgresql_psycopg2",
            },
            "sqlite": {"NAME": "sqlite", "ENGINE": "django.db.backends.sqlite3"},
            "secondary": {
                "HOST": "localhost",
                "PORT": 5432,
                "NAME": "test_secondary",
                "USER": PG_USER,
                "ENGINE": "django.db.backends.postgresql_psycopg2",
            },
        },
        INSTALLED_APPS=("tests",),
        DATABASE_ROUTERS=["tests.router.CustomRouter"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        LOGGING={
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "file": {
                    "level": "DEBUG",
                    "class": "logging.FileHandler",
                    "filename": ROOT_DIR / "tests.log",
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
        },
    )
