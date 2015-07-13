import os
import sys
import csv
from django.db import connections, router
from django.contrib.humanize.templatetags.humanize import intcomma


class Copy(object):
    """
    Maps comma-delimited data file to a Django model
    and loads it into PostgreSQL databases using its
    COPY command.
    """
    def __init__(
        self,
        model,
        csv_path,
        mapping,
        using=None,
        delimiter=',',
        null=None
    ):
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
        if self.conn.vendor != 'postgresql':
            raise TypeError("Only PostgreSQL backends supported")
        self.backend = self.conn.ops
        self.delimiter = delimiter
        self.null = null

    def get_headers(self):
        """
        Returns the column headers from the csv as a list.
        """
        with open(self.csv_path, 'r') as infile:
            csv_reader = csv.reader(infile, delimiter=self.delimiter)
            headers = next(csv_reader)
        return headers

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

        header2field = []
        for h in self.get_headers():
            try:
                f_name = self.mapping[h]
            except KeyError:
                raise ValueError("Map does not include %s field" % h)
            try:
                f = [f for f in self.model._meta.fields if f.name == f_name][0]
            except IndexError:
                raise ValueError("Model does not include %s field" % f_name)
            header2field.append((h, f))

        temp_table_name = "temp_%s" % self.model._meta.db_table
        temp_field_list = ", ".join([
            '"%s" %s' % (x, y.db_type(self.conn))
            for x, y in header2field
        ])

        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS %s;" % temp_table_name)

        sql = """CREATE TEMPORARY TABLE %(table_name)s (%(field_list)s);"""

        sql = sql % dict(
            table_name=temp_table_name,
            field_list=temp_field_list,
        )
        cursor.execute(sql)

        sql = """COPY %(db_table)s (%(header_list)s) FROM '%(csv_path)s'
WITH CSV HEADER %(extra_options)s;"""

        options = {
            'db_table': temp_table_name,
            'csv_path': self.csv_path,
            'extra_options': '',
            'header_list': ", ".join(['"%s"' % x for x, y in header2field])
        }
        if self.delimiter:
            options['extra_options'] += " DELIMITER '%s'" % self.delimiter
        if self.null:
            options['extra_options'] += " NULL '%s'" % self.null

        cursor.execute(sql % options)

        sql = """INSERT INTO %(model_table)s (%(model_fields)s) (
SELECT %(temp_fields)s
FROM %(temp_table)s);
"""
        sql = sql % dict(
            model_table=self.model._meta.db_table,
            model_fields=", ".join(['"%s"' % y.name for x, y in header2field]),
            temp_table=temp_table_name,
            temp_fields=", ".join(['"%s"' % x for x, y in header2field])
        )
        cursor.execute(sql)

        cursor.execute("DROP TABLE IF EXISTS %s;" % temp_table_name)

        if not silent:
            stream.write(
                "%s records loaded\n" % intcomma(self.model.objects.count())
            )
