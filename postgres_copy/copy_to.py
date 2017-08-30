#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom managers for working with CAL-ACCESS processed data models.
"""
from __future__ import unicode_literals
from django.db import models, connection
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query
from psycopg2.sql import Literal


class SQLCopyToCompiler(SQLCompiler):
    """
    Custom SQL compiler for creating a COPY TO query (postgres backend only).
    """
    def setup_query(self):
        """
        Extend the default SQLCompiler.setup_query to add re-ordering of items in select.
        """
        super(SQLCopyToCompiler, self).setup_query()
        if self.query.copy_to_fields:
            self.select = []
            for field in self.query.copy_to_fields:
                # raises error if field is not available
                expression = self.query.resolve_ref(field)

                if field in self.query.annotations:
                    selection = (expression, self.compile(expression), field)
                else:
                    selection = (expression, self.compile(expression), None)

                self.select.append(selection)

    def execute_sql(self, csv_path):
        """
        Run the COPY TO query.
        """
        # open file for writing
        # use stdout to avoid file permission issues
        with open(csv_path, 'wb') as stdout:
            with connection.cursor() as c:
                # compose SELECT query parameters as sql strings
                params = self.as_sql()[1]
                adapted_params = tuple(
                    Literal(p).as_string(c.cursor) for p in params
                )
                # compile the SELECT query
                select_sql = self.as_sql()[0] % adapted_params
                # then the COPY TO query
                copy_to_sql = "COPY (%s) TO STDOUT CSV HEADER" % select_sql
                # then executw
                c.cursor.copy_expert(copy_to_sql, stdout)


class CopyToQuery(Query):
    """
    Represents a "copy to" SQL query.
    """
    def __init__(self, *args, **kwargs):
        """
        Extend inherited __init__ method to include setting copy_to_fields from args.
        """
        super(CopyToQuery, self).__init__(*args, **kwargs)
        self.copy_to_fields = args

    def get_compiler(self, using=None, connection=None):
        """
        Return a SQLCopyToCompiler object.
        """
        return SQLCopyToCompiler(self, connection, using)


class CopyToQuerySet(models.QuerySet):
    """
    Subclass of QuerySet that adds _copy_to_csv method.
    """
    def to_csv(self, csv_path, *fields):
        """
        Copy current objects in QuerySet to a file at csv_path.
        Use optional fields arguments to specify the names of fields
        to be copied and their order in the csv file.
        Return a call to .execute_sql() on the compiler of the queryset's query.
        """
        query = self.query.clone(CopyToQuery)
        query.copy_to_fields = fields
        compiler = query.get_compiler(self.db, connection=connection)
        compiler.execute_sql(csv_path)
