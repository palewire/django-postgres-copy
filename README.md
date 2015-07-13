# django-postgres-copy

Maps a comma-delimited data file to a Django model and loads it into a PostgreSQL database using its built-in COPY command

*This is a work in progress and should not be expected to work.*

## Getting started

Start with a CSV file you'd like to load. Let's start with something simple.

```csv
NAME,NUMBER,DATE
ben,1,2012-01-01
joe,2,2012-01-02
jane,3,2012-01-03
```

Create a Django model that corresponds to the data.

```python
from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=500)
    number = models.IntegerField(null=True)
    dt = models.DateField(null=True)
```

You probably need to create the database table like so.

```bash
$ python manage.py migrate
```

Create a loader that uses this library to load CSV data. Once place you could
put it is in a Django management command.

```python
from postgres_copy import Copy
from myapp.models import Person
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        c = Copy(
            # Give it the model
            Person,
            # The path to your CSV
            '/path/to/my/data.csv',
            # And a dict mapping the CSV headers to model fields
            dict(NAME='name', NUMBER='number', DATE='dt')
        )
        # Then save it.
        c.save()
```

Run your loader and that's it.

```bash
$ python manage.py mymanagementcommand
Loading CSV to Person
3 records loaded
```

That's it!
