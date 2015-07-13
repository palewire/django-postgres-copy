import os
import sys
from django.db import connections, router
from django.contrib.humanize.templatetags.humanize import intcomma


class Copy(object):
    """
    Maps comma-delimited data file to a Django model
    and loads it into PostgreSQL databases using its
    COPY command.
    """
    def __init__(self, model, csv_path, mapping, using=None, delimiter=None):
        self.model = model
        self.mapping = mapping
        if os.path.exists(csv_path):
            self.csv_path = csv_path
        else:
            raise ValueError("csv_path does not exist")
        if using is not None:
            self.using = using
        else:
            self.using = router.db_for_write(model)
        self.conn = connections[self.using]
        self.backend = self.conn.ops
        # THROW AN ERROR HERE IF THE BACKEND IS NOT PSQL!
        self.delimiter = delimiter

    def save(self, silent=False, stream=sys.stdout):
        """
        Saves the contents of the CSV file to the database.

         silent:
           By default, non-fatal error notifications are printed to stdout,
           but this keyword may be set to disable these notifications.

         stream:
           Status information will be written to this file handle. Defaults to
           using `sys.stdout`, but any object with a `write` method is
           supported.
        """
        if not silent:
            stream.write("Loading CSV to %s\n" % self.model.__name__)

        csv_headers = []
        for col in self.model._meta.fields:
            if col.name == 'id' and col.primary_key:
                # What do we do with Django's automatic primary keys?
                continue
            try:
                csv_headers.append(self.mapping[col.name])
            except KeyError:
                # What do we do if somebody wants to have extra columns
                # on their model not included in the CSV that are left empty?
                raise ValueError("Map does not include %s field" % col.name)

        # CREATE TEMPORARY TABLE HERE

        sql = """COPY %(db_table)s (%(header_list)s)
FROM '%(csv_path)s'
WITH CSV HEADER %(extra_options)s;"""

        options = {
            'db_table': self.model._meta.db_table,
            'csv_path': self.csv_path,
            'extra_options': '',
            'header_list': ", ".join(['"%s"' % h for h in csv_headers])
        }
        if self.delimiter:
            options['extra_options'] += "DELIMITER '%s'" % self.delimiter

        cursor = self.conn.cursor()
        cursor.execute(sql % options)

        # INSERT DATA FROM TEMPORARY TABLE TO DJANGO MODEL HERE

        # DROP TEMPORARY TABLE HERE

        if not silent:
            stream.write(
                "%s records loaded\n" % intcomma(self.model.objects.count())
            )
