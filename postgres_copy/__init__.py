import os
import sys
import csv
import six
from django.db import connections, router
from django.contrib.humanize.templatetags.humanize import intcomma
from collections import OrderedDict


class CopyMapping(object):
    """
    Maps comma-delimited data file to a Django model
    and loads it into PostgreSQL databases using its
    COPY command.
    """
    def __init__(
        self,
        model,
        csv_file,
        mapping,
        using=None,
        delimiter=',',
        null=None,
        encoding=None,
        static_mapping=None,
        field_value_mapping=None,
        field_copy_types=None,
        ignore_non_mapped_headers=False,
        not_null_fields=[]
    ):
        self.model = model
        self.mapping = mapping
        self.not_null_fields = not_null_fields
        if isinstance(csv_file, six.string_types):
            if os.path.exists(csv_file):
                self.csv_file = open(csv_file, 'r')
            else:
                raise ValueError("csv_file does not exist")
        else:
            self.csv_file = csv_file
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
        self.encoding = encoding
        if static_mapping is not None:
            self.static_mapping = OrderedDict(static_mapping)
        else:
            self.static_mapping = {}
        self.field_value_mapping = field_value_mapping or {}
        self.field_copy_types = field_copy_types or {}

        # Connect the headers from the CSV with the fields on the model
        self.headers = []
        self.field_header_crosswalk = []
        inverse_mapping = {v: k for k, v in self.mapping.items()}
        for h in self.get_headers():
            self.headers.append(h)
            try:
                f_name = inverse_mapping[h]
            except KeyError:
                if ignore_non_mapped_headers:
                    self.field_header_crosswalk.append((None, h))
                    continue
                raise ValueError("Map does not include %s field" % h)
            try:
                f = [f for f in self.model._meta.fields if f.name == f_name][0]
            except IndexError:
                raise ValueError("Model does not include %s field" % f_name)
            self.field_header_crosswalk.append((f, h))

        # Validate that the static mapping columns exist
        for f_name in self.static_mapping.keys():
            try:
                [s for s in self.model._meta.fields if s.name == f_name][0]
            except IndexError:
                raise ValueError("Model does not include %s field" % f_name)

        self.temp_table_name = "temp_%s" % self.model._meta.db_table

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

        # Connect to the database
        cursor = self.conn.cursor()

        # Create all of the raw SQL
        drop_sql = self.prep_drop()
        create_sql = self.prep_create()
        copy_sql = self.prep_copy()
        insert_sql = self.prep_insert()

        # Run all of the raw SQL
        cursor.execute(drop_sql)
        cursor.execute(create_sql)
        fp = self.csv_file
        fp.seek(0)
        cursor.copy_expert(copy_sql, fp)
        cursor.execute(insert_sql)
        cursor.execute(drop_sql)

        if not silent:
            stream.write(
                "%s records loaded\n" % intcomma(self.model.objects.count())
            )

    def get_headers(self):
        """
        Returns the column headers from the csv as a list.
        """
        csv_reader = csv.reader(self.csv_file, delimiter=self.delimiter)
        headers = next(csv_reader)
        return headers

    def sql_value(self, v):
        if isinstance(v, six.string_types):
            return "'{}'".format(v)
        return v

    def get_value_mapping_sql(self, header, mapping):
        sql = '''\nCASE {cases} END'''
        cases = (
            "WHEN \"{header}\" = {src} THEN {dst}".
            format(header=header, src=self.sql_value(k), dst=self.sql_value(v))
            for k, v in six.iteritems(mapping)
        )
        return sql.format(cases='\n'.join(cases))

    def prep_drop(self):
        """
        Creates a DROP statement that gets rid of the temporary table.

        Return SQL that can be run.
        """
        return "DROP TABLE IF EXISTS %s;" % self.temp_table_name

    def prep_create(self):
        """
        Creates a CREATE statement that makes a new temporary table.

        Returns SQL that can be run.
        """
        sql = """CREATE TEMPORARY TABLE "%(table_name)s" (%(field_list)s);"""
        options = dict(table_name=self.temp_table_name)
        field_list = []

        default_copy_type = 'text'

        # Loop through all the fields and CSV headers together
        for field, header in self.field_header_crosswalk:
            # in order or priority, set copy_type according to
            # 1) field_copy_types[header]
            # 2) field.copy_type
            # 3) model.copy_FIELD_template.method
            # 4) default_copy_type
            copy_type = default_copy_type
            if field:
                template_method = 'copy_%s_template' % field.name
                method = getattr(self.model(), template_method, None)
                if self.field_copy_types.get(field.name):
                    copy_type = self.field_copy_types[field.name]
                elif hasattr(field, 'copy_type'):
                    copy_type = getattr(field, 'copy_type')
                elif hasattr(method, 'copy_type'):
                    copy_type = method.copy_type
                else:
                    copy_type = field.db_type(self.conn)
            string = '"%s" %s' % (header, copy_type)

            # Add the string to the list
            field_list.append(string)

        # Join all the field strings together
        options['field_list'] = ", ".join(field_list)

        # Mash together the SQL and pass it out
        return sql % options

    def prep_copy(self):
        """
        Creates a COPY statement that loads the CSV into a temporary table.

        Returns SQL that can be run.
        """
        sql = """
            COPY "%(db_table)s" (%(header_list)s)
            FROM STDIN
            WITH CSV HEADER %(extra_options)s;
        """
        options = {
            'db_table': self.temp_table_name,
            'extra_options': '',
            'header_list': ", ".join([
                '"%s"' % h for f, h in self.field_header_crosswalk
            ])
        }
        if self.delimiter:
            options['extra_options'] += " DELIMITER '%s'" % self.delimiter
        if self.null is not None:
            options['extra_options'] += " NULL '%s'" % self.null
        if self.encoding:
            options['extra_options'] += " ENCODING '%s'" % self.encoding
        if len(self.not_null_fields) > 0:
            quoted_fields = ['"{}"'.format(field) for field in self.not_null_fields]
            options['extra_options'] += " FORCE NOT NULL {}".format(', '.join(quoted_fields))
        return sql % options

    def prep_insert(self):
        """
        Creates a INSERT statement that reorders and cleans up
        the fields from the temporary table for insertion into the
        Django model.

        Returns SQL that can be run.
        """
        sql = """
            INSERT INTO "%(model_table)s" (%(model_fields)s) (
            SELECT %(temp_fields)s
            FROM "%(temp_table)s");
        """
        options = dict(
            model_table=self.model._meta.db_table,
            temp_table=self.temp_table_name,
        )

        model_fields = []

        for field, header in self.field_header_crosswalk:
            if field:
                model_fields.append('"%s"' % field.get_attname_column()[1])

        for k in self.static_mapping.keys():
            db_column = self.model._meta.get_field(k).get_attname_column()[1]
            model_fields.append('"%s"' % db_column)

        options['model_fields'] = ", ".join(model_fields)

        temp_fields = []
        for field, header in self.field_header_crosswalk:
            if not field:
                continue
            string = '"%s"' % header
            template_method = 'copy_%s_template' % field.name
            # If a value mapping is provided, use that
            value_mapping = self.field_value_mapping.get(field.name)
            if value_mapping:
                string = self.get_value_mapping_sql(header, value_mapping)
            elif hasattr(self.model, template_method):
                template = getattr(self.model(), template_method)()
                string = template % dict(name=header)
            elif hasattr(field, 'copy_template'):
                string = field.copy_template % dict(name=header)
            temp_fields.append(string)
        for v in self.static_mapping.values():
            temp_fields.append("'%s'" % v)
        options['temp_fields'] = ", ".join(temp_fields)
        return sql % options
