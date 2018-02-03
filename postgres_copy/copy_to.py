#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Handlers for working with PostgreSQL's COPY TO command.
"""
from __future__ import unicode_literals
import logging
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
                if field in self.query.annotations:
                    selection = (expression, self.compile(expression), field)
                else:
                    selection = (expression, self.compile(expression), None)
                self.select.append(selection)

    def execute_sql(self, csv_path):
        """
        Run the COPY TO query.
        """
        logger.debug("Copying data to {}".format(csv_path))

        # adapt SELECT query parameters to SQL syntax
        params = self.as_sql()[1]
        adapted_params = tuple(adapt(p) for p in params)

        # open file for writing
        # use stdout to avoid file permission issues
        with open(csv_path, 'wb') as stdout:
            with connections[self.using].cursor() as c:
                # compile the SELECT query
                select_sql = self.as_sql()[0] % adapted_params
                # then the COPY TO query
                copy_to_sql = "COPY ({}) TO STDOUT DELIMITER '{}' CSV {} {}"
                copy_to_sql = copy_to_sql.format(
                    select_sql,
                    self.query.copy_to_delimiter,
                    self.query.copy_to_header,
                    self.query.copy_to_null_string
                )
                # then execute
                logger.debug(copy_to_sql)
                c.cursor.copy_expert(copy_to_sql, stdout)


class CopyToQuery(Query):
    """
    Represents a "copy to" SQL query.
    """
    def get_compiler(self, using=None, connection=None):
        """
        Return a SQLCopyToCompiler object.
        """
        return SQLCopyToCompiler(self, connection, using)
