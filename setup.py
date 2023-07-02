import os
import typing
from distutils.core import Command

from setuptools import setup


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


def version_scheme(version):
    """
    Version scheme hack for setuptools_scm.

    Appears to be necessary to due to the bug documented here: https://github.com/pypa/setuptools_scm/issues/342

    If that issue is resolved, this method can be removed.
    """
    import time

    from setuptools_scm.version import guess_next_version

    if version.exact:
        return version.format_with("{tag}")
    else:
        _super_value = version.format_next_version(guess_next_version)
        now = int(time.time())
        return _super_value + str(now)


def local_version(version):
    """
    Local version scheme hack for setuptools_scm.

    Appears to be necessary to due to the bug documented here: https://github.com/pypa/setuptools_scm/issues/342

    If that issue is resolved, this method can be removed.
    """
    return ""


class TestCommand(Command):
    user_options: typing.List[typing.Any] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import django
        from django.conf import settings
        from django.core.management import call_command

        settings.configure(
            DATABASES={
                "default": {
                    "HOST": "localhost",
                    "PORT": 5432,
                    "NAME": "test",
                    "USER": "postgres",
                    "ENGINE": "django.db.backends.postgresql_psycopg2",
                },
                "other": {
                    "HOST": "localhost",
                    "PORT": 5432,
                    "NAME": "test_alternative",
                    "USER": "postgres",
                    "ENGINE": "django.db.backends.postgresql_psycopg2",
                },
                "sqlite": {"NAME": "sqlite", "ENGINE": "django.db.backends.sqlite3"},
                "secondary": {
                    "HOST": "localhost",
                    "PORT": 5432,
                    "NAME": "test_secondary",
                    "USER": "postgres",
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
                        "filename": os.path.join(
                            os.path.dirname(__file__), "tests.log"
                        ),
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
        django.setup()
        call_command("test", "tests")


setup(
    name="django-postgres-copy",
    author="Ben Welsh",
    author_email="b@palewi.re",
    url="https://palewi.re/docs/django-postgres-copy/",
    description="Quickly import and export delimited data with Django support for PostgreSQL’s COPY command",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    license="MIT",
    packages=("postgres_copy",),
    cmdclass={"test": TestCommand},
    setup_requires=["setuptools_scm"],
    use_scm_version={"version_scheme": version_scheme, "local_scheme": local_version},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "License :: OSI Approved :: MIT License",
    ],
    project_urls={
        "Documentation": "https://palewi.re/docs/django-postgres-copy/",
        "Source": "https://github.com/palewire/django-postgres-copy",
        "Tracker": "https://github.com/palewire/django-postgres-copy/issues",
        "Tests": "https://github.com/palewire/django-postgres-copy/actions/workflows/test.yaml",
    },
)
