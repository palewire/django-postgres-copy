====================
django-postgres-copy
====================

Quickly move comma-delimited data in and out of a Django model using PostgreSQL's COPY command.


Why and what for?
-----------------

`The people <http://www.californiacivicdata.org/about/>`_ who made this library are data journalists. We are often downloading, cleaning and analyzing new data.

That means we write a load of loaders. In the past we did this by looping through each row and saving it to the database using the Django's ORM `create method <https://docs.djangoproject.com/en/dev/ref/models/querysets/#django.db.models.query.QuerySet.create>`_.

.. code-block:: python

    import csv
    from myapp.models import MyModel

    data = csv.DictReader(open("./data.csv"))
    for row in data:
        MyModel.objects.create(name=row['NAME'], number=row['NUMBER'])

That works, but if you have a big file as Django racks up a database query for each row it can take a long time to get all the data in the database.

Lucky for us, PostgreSQL has a built-in tool called `COPY <http://www.postgresql.org/docs/9.4/static/sql-copy.html>`_ that can hammer data in and out the database with one quick query.

This package tries to make using COPY as easy any other database routine supported by Django. It is implemented by a custom `model manager<https://docs.djangoproject.com/en/dev/topics/db/managers/>`_.

Here's how it imports a CSV to a database table.

.. code-block:: python

    from myapp.models import MyModel

    MyModel.objects.from_csv(
        "./data.csv",
        dict(name='NAME', number='NUMBER')
    )

And here's how it exports a database table to a CSV.

.. code-block:: python

    from myapp.models import MyModel

    MyModel.objects.to_csv("./data.csv")


Installation
------------

The package can be installed from the Python Package Index with `pip`.

.. code-block:: bash

    $ pip install django-postgres-copy

You will of course have to have Django, PostgreSQL and an adapter between the two (like psycopg2) already installed to put this library to use.

An example
----------

It all starts with a CSV file you'd like to load into your database. This library is intended to be used with large files but here's something simple as an example.

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

Create a loader that uses this library to load CSV data into the model. One place you could put it is in a Django management command.

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
-------------------

.. class:: CopyMapping(model, csv_path, mapping[, using=None, delimiter=',', null=None, force_not_null=None, force_null=None, encoding=None, static_mapping=None])

The following are the arguments and keywords that may be used during
instantiation of ``CopyMapping`` objects.

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

``quote_character``    Specifies the quoting character to be used when a
                       data value is quoted. The default is double-quote.
                       This must be a single one-byte character.

``null``               Specifies the string that represents a null value.
                       The default is an unquoted empty string. This must
                       be a single one-byte character.

``force_not_null``     Specifies which columns should ignore matches
                       against the null string. Empty values in these columns
                       will remain zero-length strings rather than becoming
                       nulls. The default is None. If passed, this must be
                       list of column names.

``force_null``         Specifies which columns should register matches
                       against the null string, even if it has been quoted.
                       In the default case where the null string is empty,
                       this converts a quoted empty string into NULL. The
                       default is None. If passed, this must be list of
                       column names.

``encoding``           Specifies the character set encoding of the strings
                       in the CSV data source.  For example, ``'latin-1'``,
                       ``'utf-8'``, and ``'cp437'`` are all valid encoding
                       parameters.

``using``              Sets the database to use when importing data.
                       Default is None, which will use the ``'default'``
                       database.

``static_mapping``     Set model attributes not in the CSV the same
                       for every row in the database by providing a dictionary
                       with the name of the columns as keys and the static
                       inputs as values.
=====================  =====================================================


``save()`` keyword arguments
----------------------------

.. method:: CopyMapping.save([silent=False, stream=sys.stdout])

The ``save()`` method also accepts keywords.  These keywords are used for controlling output logging and error handling.

===========================  =================================================
Keyword Arguments            Description
===========================  =================================================
``silent``                   By default, non-fatal error notifications are
                             printed to ``sys.stdout``, but this keyword may
                             be set to disable these notifications.

``stream``                   Status information will be written to this file
                             handle.  Defaults to using ``sys.stdout``, but
                             any object with a ``write`` method is supported.
===========================  =================================================


Transforming data
-----------------

By default, the COPY command cannot transform data on-the-fly as it is loaded into the database.

This library first loads the data into a temporary table before inserting all records into the model table. So it is possible to use PostgreSQL's built-in SQL methods to modify values during the insert.

As an example, imagine a CSV that includes a column of yes and no values that you wanted to store in the database as 1 or 0 in an integer field.

.. code-block:: text

    NAME,VALUE
    ben,yes
    joe,no

A model to store the data as you'd prefer to might look like this.

.. code-block:: python

    from django.db import models


    class Person(models.Model):
        name = models.CharField(max_length=500)
        value = models.IntegerField()

But if the CSV file was loaded directly into the database, you would receive a data type error when the 'yes' and 'no' strings were inserted into the integer field.

This library offers two ways you can transform that data during the insert.


Custom-field transformations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One approach is to create a custom Django field.

You can provide a SQL statement for how to transform the data during the insert into the model table. The transformation must include a string interpolation keyed to "name", where the title of the database column will be slotted.

This example uses a `CASE statement <http://www.postgresql.org/docs/9.4/static/plpgsql-control-structures.html>`_ to transforms the data.

.. code-block:: python

  from django.db.models.fields import IntegerField


  class MyIntegerField(IntegerField):
      copy_template = """
          CASE
              WHEN "%(name)s" = 'yes' THEN 1
              WHEN "%(name)s" = 'no' THEN 0
          END
      """

Back in the models file the custom field can be substituted for the default.

.. code-block:: python

    from django.db import models
    from myapp.fields import MyIntegerField

    class Person(models.Model):
        name = models.CharField(max_length=500)
        value = MyIntegerField()

Run your loader and it should finish fine.


Model-method transformations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A second approach is to provide a SQL string for how to transform a field during the insert on the model itself. This lets you specify different transformations for different fields of the same type.

You must name the method so that the field name is sandwiched between ``copy_`` and ``_template``. It must return a SQL statement with a string interpolation keyed to "name", where the name of the database column will be slotted.

For the example above, the model might be modified to look like this.

.. code-block:: python

    from django.db import models

    class Person(models.Model):
        name = models.CharField(max_length=500)
        value = models.IntegerField()

        def copy_value_template(self):
          return """
              CASE
                  WHEN "%(name)s" = 'yes' THEN 1
                  WHEN "%(name)s" = 'no' THEN 0
              END
              """

And that's it.

Here's another example of a common issue, transforming the CSV's date format to one PostgreSQL and Django will understand.

.. code-block:: python

        def copy_mydatefield_template(self):
            return """
                CASE
                    WHEN "%(name)s" = '' THEN NULL
                    ELSE to_date("%(name)s", 'MM/DD/YYYY') /* The source CSV's date pattern can be set here. */
                END
            """

It's important to handle empty strings (by converting them to NULL) in this example. PostgreSQL will accept empty strings, but Django won't be able to ingest the field and you'll get a strange "year out of range" error when you call something like ``MyModel.objects.all()``.

Inserting static values
-----------------------

If your model has columns that are not in the CSV, you can set static values for what is inserted using the ``static_mapping`` keyword argument. It will insert the provided values into every row in the database.

An example could be if you want to include the name of the source CSV file along with each row.

Your model might look like this:

.. code-block:: python
    :emphasize-lines: 6

    from django.db import models

    class Person(models.Model):
        name = models.CharField(max_length=500)
        number = models.IntegerField()
        source_csv = models.CharField(max_length=500)

And your loader would look like this:

.. code-block:: python
    :emphasize-lines: 16-18

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
                dict(name='NAME', number='NUMBER'),
                static_mapping = {
                    'source_csv': 'data.csv'
                }
            )
            # Then save it.
            c.save()


Extending with hooks
--------------------

The ``CopyMapping`` loader includes optional hooks run before and after the COPY statement that loads your CSV into a temporary table and again before and again the INSERT statement that then slots it into your model.

If you have extra steps or more complicated logic you'd like to work into a loading routine, these hooks provide an opportunity to extend the base library.

To try them out, subclass ``CopyMapping`` and fill in as many of the optional hook methods below as you need.

.. code-block:: python

    from postgres_copy import CopyMapping


    class HookedCopyMapping(CopyMapping):
        def pre_copy(self, cursor):
            print "pre_copy!"
            # Doing whatever you'd like here

        def post_copy(self, cursor):
            print "post_copy!"
            # And here

        def pre_insert(self, cursor):
            print "pre_insert!"
            # And here

        def post_insert(self, cursor):
            print "post_insert!"
            # And finally here


Now you can run that subclass as you normally would its parent

.. code-block:: python

    from myapp.models import Person
    from myapp.loaders import HookedCopyMapping
    from django.core.management.base import BaseCommand


    class Command(BaseCommand):

        def handle(self, *args, **kwargs):
            # Note that we're using HookedCopyMapping here
            c = HookedCopyMapping(
                Person,
                '/path/to/my/data.csv',
                dict(name='NAME', number='NUMBER'),
            )
            # Then save it.
            c.save()


Open-source resources
---------------------

* Code: `github.com/california-civic-data-coalition/django-postgres-copy <https://github.com/california-civic-data-coalition/django-postgres-copy>`_
* Issues: `github.com/california-civic-data-coalition/django-postgres-copy/issues <https://github.com/california-civic-data-coalition/django-postgres-copy/issues>`_
* Packaging: `pypi.python.org/pypi/django-postgres-copy <https://pypi.python.org/pypi/django-postgres-copy>`_
* Testing: `travis-ci.org/california-civic-data-coalition/django-postgres-copy <https://travis-ci.org/california-civic-data-coalition/django-postgres-copy>`_
* Coverage: `coveralls.io/r/california-civic-data-coalition/django-postgres-copy <https://coveralls.io/r/california-civic-data-coalition/django-postgres-copy>`_
