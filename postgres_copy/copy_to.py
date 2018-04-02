#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Handlers for working with PostgreSQL's COPY TO command.
"""
from __future__ import unicode_literals
import logging
from io import BytesIO
from django.db import connections
from psycopg2.extensions import adapt
from django.db.models.sql.query import Query
from django.db.models.sql.compiler import SQLCompiler
logger = logging.getLogger(__name__)


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
                selection = (
                    expression,
                    self.compile(expression),
                    field if field in self.query.annotations else None,
                )
                self.select.append(selection)

    def execute_sql(self, csv_path=None):
        """
        Run the COPY TO query.
        """
        logger.debug("Copying data to {}".format(csv_path))

        # adapt SELECT query parameters to SQL syntax
        params = self.as_sql()[1]
        adapted_params = tuple(adapt(p) for p in params)

        # use stdout to avoid file permission issues
        with connections[self.using].cursor() as c:
            # compile the SELECT query
            select_sql = self.as_sql()[0] % adapted_params
            # then the COPY TO query
            copy_to_sql = "COPY ({}) TO STDOUT {} CSV {}"
            # Optional extras
            options_list = [
                self.query.copy_to_header,
                self.query.copy_to_null_string,
                self.query.copy_to_quote_char,
                self.query.copy_to_force_quote,
                self.query.copy_to_encoding,
                self.query.copy_to_escape
            ]
            # Construct the copy_to_sql string
            copy_to_sql = copy_to_sql.format(
                select_sql,
                self.query.copy_to_delimiter,
                " ".join(option for option in options_list if True),
                )
            # then execute
            logger.debug(copy_to_sql)

            # If there is, write it out there.
            if csv_path:
                with open(csv_path, 'wb') as stdout:
                    c.cursor.copy_expert(copy_to_sql, stdout)
                    return
            # If there's no csv_path, return the output as a string.
            else:
                stdout = BytesIO()
                c.cursor.copy_expert(copy_to_sql, stdout)
                return stdout.getvalue()


class CopyToQuery(Query):
    """
    Represents a "copy to" SQL query.
    """
    def get_compiler(self, using=None, connection=None):
        """
        Return a SQLCopyToCompiler object.
        """
        return SQLCopyToCompiler(self, connection, using)
