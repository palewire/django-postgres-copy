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

        call_command('test', 'tests.tests')


setup(
    name='django-postgres-copy',
    version='0.0.3',
    description='A set of helpers for baking your Django site out as flat files',
    author='Ben Welsh',
    author_email='ben.welsh@gmail.com',
    url='http://www.github.com/california-civic-data-coalition/django-postgresql-copy/',
    license="MIT",
    packages=("postgres_copy",),
    cmdclass={'test': TestCommand}
)
