django-postgres-copy
====================

Quickly load comma-delimited data into a Django model using PostgreSQL's COPY command

Why and what for?
-----------------

`The people <http://www.californiacivicdata.org/about/>`_ who made this library are data journalists.
We are often downloading, cleaning and analyzing new data.

That means we write a load of loaders. You can usually do this by looping through each row
and saving it to the database using the Django's ORM `create method <https://docs.djangoproject.com/en/1.8/ref/models/querysets/#django.db.models.query.QuerySet.create>`_.

.. code-block:: python

    import csv
    from myapp.models import MyModel

    data = csv.DictReader(open("./data.csv"))
    for row in data:
        MyModel.objects.create(name=row['NAME'], number=row['NUMBER'])

But if you have a big CSV, Django will rack up database queries and it can take a long long time to finish.

Lucky for us, PostgreSQL has a built-in tool called `COPY <http://www.postgresql.org/docs/9.4/static/sql-copy.html>`_ that will hammer data into the
database with one quick query.

This package tries to make using COPY as easy any other database routine supported by Django. It is
largely based on the design of the `LayerMapping <https://docs.djangoproject.com/en/1.8/ref/contrib/gis/layermapping/>`_
utility for importing geospatial data.

.. code-block:: python

    from myapp.models import MyModel
    from postgres_copy import CopyMapping

    c = CopyMapping(
        MyModel,
        "./data.csv",
        dict(name='NAME', number='NUMBER')
    )
    c.save()

Installation
------------

The package can be installed from the Python Package Index with `pip`.

.. code-block:: bash

    $ pip install django-postgres-copy

An example
----------

It all starts with a CSV file you'd like to load into your database. This library
is intended to be used with large files but for here's something simple.

.. code-block:: text

    NAME,NUMBER,DATE
    ben,1,2012-01-01
    joe,2,2012-01-02
    jane,3,2012-01-03

A Django model that corresponds to the data might look something like this.

.. code-block:: python

    from django.db import models


    class Person(models.Model):
        name = models.CharField(max_length=500)
        number = models.IntegerField(null=True)
        dt = models.DateField(null=True)

If the model hasn't been created in your database, that needs to happen.

.. code-block:: bash

    $ python manage.py migrate

Create a loader that uses this library to load CSV data into the model. One place you could
put it is in a Django management command.

.. code-block:: python

    from myapp.models import Person
    from postgres_copy import CopyMapping
    from django.core.management.base import BaseCommand


    class Command(BaseCommand):

        def handle(self, *args, **kwargs):
            c = CopyMapping(
                # Give it the model
                Person,
                # The path to your CSV
                '/path/to/my/data.csv',
                # And a dict mapping the  model fields to CSV headers
                dict(name='NAME', number='NUMBER', dt='DATE')
            )
            # Then save it.
            c.save()

Run your loader and that's it.

.. code-block:: bash

    $ python manage.py mymanagementcommand
    Loading CSV to Person
    3 records loaded

Like I said, that's it!


``CopyMapping`` API
--------------------

.. class:: CopyMapping(model, csv_path, mapping[, using=None, delimiter=',', null=None, encoding=None])

The following are the arguments and keywords that may be used during
instantiation of ``copy`` objects.

=================  =========================================================
Argument           Description
=================  =========================================================
``model``          The target model, *not* an instance.

``csv_path``       The path to the delimited data source file
                   (e.g., a CSV)

``mapping``        A dictionary: keys are strings corresponding to
                   the model field, and values correspond to
                   string field names for the CSV header.
=================  =========================================================

=====================  =====================================================
Keyword Arguments
=====================  =====================================================
``delimiter``          The character that separates values in the data file.
                       By default  it is ",". This must be a single one-byte
                       character.

``null``               Specifies the string that represents a null value.
                       The default is an unquoted empty string. This must
                       be a single one-byte character.

``encoding``           Specifies the character set encoding of the strings
                       in the CSV data source.  For example, ``'latin-1'``,
                       ``'utf-8'``, and ``'cp437'`` are all valid encoding
                       parameters.

``using``              Sets the database to use when importing data.
                       Default is None, which will use the ``'default'``
                       database.
=====================  =====================================================

``save()`` Keyword Arguments
----------------------------

.. method:: CopyMapping.save([silent=False, stream=sys.stdout])

The ``save()`` method also accepts keywords.  These keywords are
used for controlling output logging, error handling, and for importing
specific feature ranges.

===========================  =================================================
Save Keyword Arguments       Description
===========================  =================================================

``silent``                   By default, non-fatal error notifications are
                             printed to ``sys.stdout``, but this keyword may
                             be set to disable these notifications.

``stream``                   Status information will be written to this file
                             handle.  Defaults to using ``sys.stdout``, but
                             any object with a ``write`` method is supported.
===========================  =================================================

Open-source resources
---------------------

* Code: `github.com/california-civic-data-coalition/django-postgres-copy <https://github.com/california-civic-data-coalition/django-postgres-copy>`_
* Issues: `github.com/california-civic-data-coalition/django-postgres-copy/issues <https://github.com/california-civic-data-coalition/django-postgres-copy/issues>`_
* Packaging: `pypi.python.org/pypi/django-postgres-copy <https://pypi.python.org/pypi/django-postgres-copy>`_
* Testing: `travis-ci.org/california-civic-data-coalition/django-postgres-copy <https://travis-ci.org/california-civic-data-coalition/django-postgres-copy>`_
* Coverage: `coveralls.io/r/california-civic-data-coalition/django-postgres-copy <https://coveralls.io/r/california-civic-data-coalition/django-postgres-copy>`_
