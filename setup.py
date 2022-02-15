import os
from setuptools import setup
from distutils.core import Command


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


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
                    'HOST': 'localhost',
                    'PORT': 5432,
                    'NAME': 'test',
                    'USER': 'postgres',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                },
                'other': {
                    'HOST': 'localhost',
                    'PORT': 5432,
                    'NAME': 'test_alternative',
                    'USER': 'postgres',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                },
                'sqlite': {
                    'NAME': 'sqlite',
                    'ENGINE': 'django.db.backends.sqlite3'
                },
                'secondary': {
                    'HOST': 'localhost',
                    'PORT': 5432,
                    'NAME': 'test_secondary',
                    'USER': 'postgres',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                }
            },
            INSTALLED_APPS=("tests",),
            DATABASE_ROUTERS=['tests.router.CustomRouter'],
            DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
            LOGGING = {
                'version': 1,
                'disable_existing_loggers': False,
                'handlers': {
                    'file': {
                        'level': 'DEBUG',
                        'class': 'logging.FileHandler',
                        'filename': os.path.join(os.path.dirname(__file__), 'tests.log'),
                    },
                },
                'formatters': {
                    'verbose': {
                        'format': '%(levelname)s|%(asctime)s|%(module)s|%(message)s',
                        'datefmt': "%d/%b/%Y %H:%M:%S"
                    }
                },
                'loggers': {
                    'postgres_copy': {
                        'handlers': ['file'],
                        'level': 'DEBUG',
                        'propagate': True,
                    },
                }
            }
        )
        django.setup()
        call_command('test', 'tests')


setup(
    name='django-postgres-copy',
    version='2.7.0',
    author='Ben Welsh',
    author_email='b@palewi.re',
    url='https://django-postgres-copy.californiacivicdata.org/',
    description="Quickly import and export delimited data with Django support for PostgreSQL’s COPY command",
    long_description=read('README.rst'),
    license="MIT",
    packages=("postgres_copy",),
    cmdclass={'test': TestCommand},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'License :: OSI Approved :: MIT License'
    ],
    project_urls={
        'Documentation': 'https://palewi.re/docs/django-postgres-copy/',
        'Source': 'https://github.com/palewire/django-postgres-copy',
        'Tracker': 'https://github.com/palewire/django-postgres-copy/issues',
        'Tests': 'https://github.com/palewire/django-postgres-copy/actions/workflows/test.yaml',
    },
)
