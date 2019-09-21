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
                    'NAME': 'test',
                    'USER': 'postgres',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                },
                'other': {
                    'NAME': 'test_alternative',
                    'USER': 'postgres',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                },
                'sqlite': {
                    'NAME': 'sqlite',
                    'ENGINE': 'django.db.backends.sqlite3'
                },
                'secondary': {
                    'NAME': 'test_secondary',
                    'USER': 'postgres',
                    'ENGINE': 'django.db.backends.postgresql_psycopg2'
                }
            },
            INSTALLED_APPS=("tests",),
            DATABASE_ROUTERS=['tests.router.CustomRouter'],
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
        # call_command('test', 'tests.tests.PostgresCopyToTest.test_related_fields')


setup(
    name='django-postgres-copy',
    version='2.4.2',
    author='Ben Welsh',
    author_email='ben.welsh@gmail.com',
    url='http://django-postgres-copy.californiacivicdata.org/',
    description="Quickly import and export delimited data with Django support for PostgreSQL's COPY command",
    long_description=read('README.rst'),
    license="MIT",
    packages=("postgres_copy",),
    install_requires=("psycopg2>=2.8.1",),
    cmdclass={'test': TestCommand},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'License :: OSI Approved :: MIT License'
    ],
    project_urls={
        'Documentation': 'http://django-postgres-copy.californiacivicdata.org',
        'Funding': 'https://www.californiacivicdata.org/about/',
        'Source': 'https://github.com/california-civic-data-coalition/django-postgres-copy',
        'Coverage': 'https://coveralls.io/github/california-civic-data-coalition/django-postgres-copy?branch=master',
        'Tracker': 'https://github.com/california-civic-data-coalition/django-postgres-copy/issues'
    },
)
