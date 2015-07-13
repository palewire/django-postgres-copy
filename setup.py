import os
import tempfile
from setuptools import setup
from distutils.core import Command


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from django.conf import settings
        settings.configure(
            DATABASES={
                'default': {
                    'NAME': 'test',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                },
                'sqlite': {
                    'NAME': 'sqlite',
                    'ENGINE': 'django.db.backends.sqlite3'
                }
            },
            INSTALLED_APPS=("tests",),
        )
        from django.core.management import call_command
        import django
        if django.VERSION[:2] >= (1, 7):
            django.setup()

        # With Django 1.6, the way tests were discovered changed (see
        # https://docs.djangoproject.com/en/1.7/releases/1.6/#new-test-runner)
        # Set the argument to the test management command appropriately
        # depending on the Django version
        test_module = 'tests.tests'
        if django.VERSION[:2] < (1, 6):
            test_module = 'tests'

        call_command('test', test_module)


setup(
    name='django-postgres-copy',
    version='0.0.1',
    description='A set of helpers for baking your Django site out as flat files',
    author='Ben Welsh',
    author_email='ben.welsh@gmail.com',
    url='http://www.github.com/california-civic-data-coalition/django-postgresql-copy/',
    license="MIT",
    cmdclass={'test': TestCommand}
)
