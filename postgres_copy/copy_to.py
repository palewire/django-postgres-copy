#!/usr/bin/env python
"""
Handlers for working with PostgreSQL's COPY TO command.
"""

import logging
from io import BytesIO

from django.db import connections
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query

from .psycopg_compat import copy_to

logger = logging.getLogger(__name__)


class SQLCopyToCompiler(SQLCompiler):
    """
    Custom SQL compiler for creating a COPY TO query (postgres backend only).
    """

    def setup_query(self, **kwargs):
        """
        Extend the default SQLCompiler.setup_query to add re-ordering of items in select.
        """
        super().setup_query(**kwargs)
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

    def execute_sql(self, csv_path_or_obj=None):
        """
        Run the COPY TO query.
        """
        logger.debug(f"Copying data to {csv_path_or_obj}")

        params = self.as_sql()[1]

        # use stdout to avoid file permission issues
        with connections[self.using].cursor() as c:
            # grab the SELECT query
            select_sql = self.as_sql()[0]
            # then the COPY TO query
            copy_to_sql = "COPY ({}) TO STDOUT {} CSV"
            copy_to_sql = copy_to_sql.format(select_sql, self.query.copy_to_delimiter)
            # Optional extras
            options_list = [
                self.query.copy_to_header,
                self.query.copy_to_null_string,
                self.query.copy_to_quote_char,
                self.query.copy_to_force_quote,
                self.query.copy_to_encoding,
                self.query.copy_to_escape,
            ]
            options_sql = " ".join([o for o in options_list if o]).strip()
            if options_sql:
                copy_to_sql = copy_to_sql + " " + options_sql
            # then execute
            logger.debug(copy_to_sql)

            # If a file-like object was provided, write it out there.
            if hasattr(csv_path_or_obj, "write"):
                copy_to(c.cursor, copy_to_sql, params, csv_path_or_obj)
                return
            # If a file path was provided, write it out there.
            elif csv_path_or_obj:
                with open(csv_path_or_obj, "wb") as stdout:
                    copy_to(c.cursor, copy_to_sql, params, stdout)
                    return
            # If there's no csv_path, return the output as a string.
            else:
                stdout = BytesIO()
                copy_to(c.cursor, copy_to_sql, params, stdout)
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
