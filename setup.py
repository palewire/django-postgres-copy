from setuptools import setup
from distutils.core import Command


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import django
        from django.core.management import call_command
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
        django.setup()
        call_command('test', 'tests.tests')


setup(
    name='django-postgres-copy',
    version='0.0.6',
    description='Quickly load comma-delimited data into a Django model using PostgreSQL\'s COPY command',
    author='Ben Welsh',
    author_email='ben.welsh@gmail.com',
    url='http://www.github.com/california-civic-data-coalition/django-postgresql-copy/',
    license="MIT",
    packages=("postgres_copy",),
    cmdclass={'test': TestCommand},
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
)
