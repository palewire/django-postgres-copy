#!/usr/bin/env python
"""
Handlers for working with PostgreSQL's COPY command.
"""

import csv
import logging
import os
import sys
import typing
from collections import OrderedDict
from io import TextIOWrapper

from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.exceptions import FieldDoesNotExist
from django.db import NotSupportedError, connections, router
from django.db.models import Field, Model
from django.db.backends.utils import CursorWrapper

from .psycopg_compat import copy_from

logger = logging.getLogger(__name__)


class CopyMapping:
    """
    Maps comma-delimited file to Django model and loads it into PostgreSQL database using COPY command.
    """

    def __init__(
        self,
        model: typing.Type[Model],
        csv_path_or_obj: typing.Union[str, typing.BinaryIO, typing.TextIO],
        mapping: typing.Dict[str, str],
        using: typing.Optional[str] = None,
        delimiter: str = ",",
        quote_character: typing.Optional[str] = None,
        null: typing.Optional[str] = None,
        force_not_null: typing.Optional[typing.List[str]] = None,
        force_null: typing.Optional[typing.List[str]] = None,
        encoding: typing.Optional[str] = None,
        ignore_conflicts: bool = False,
        static_mapping: typing.Optional[typing.Dict[str, str]] = None,
        temp_table_name: typing.Optional[str] = None,
    ) -> None:
        # Set the required arguments
        self.model = model
        self.csv_path_or_obj = csv_path_or_obj

        # If the CSV is not a file object already ...
        if hasattr(csv_path_or_obj, "read"):
            self.csv_file = csv_path_or_obj
        else:
            # We know it's a string path at this point
            csv_path = csv_path_or_obj
            # ... verify the path exists ...
            if not os.path.exists(csv_path):
                raise ValueError("CSV path does not exist")
            # ... then open it up.
            self.csv_file = open(csv_path)

        # Hook in the other optional settings
        self.quote_character = quote_character
        self.delimiter = delimiter
        self.null = null
        self.force_not_null = force_not_null
        self.force_null = force_null
        self.encoding = encoding
        self.supports_ignore_conflicts = True
        self.ignore_conflicts = ignore_conflicts
        if static_mapping is not None:
            self.static_mapping = OrderedDict(static_mapping)
        else:
            self.static_mapping = OrderedDict()

        # Line up the database connection
        if using is not None:
            self.using = using
        else:
            self.using = router.db_for_write(model)
        self.conn = connections[self.using]
        self.backend = self.conn.ops

        # Verify it is PostgreSQL
        if self.conn.vendor != "postgresql":
            raise TypeError("Only PostgreSQL backends supported")

        # Check if it is PSQL 9.5 or greater, which determines if ignore_conflicts is supported
        self.supports_ignore_conflicts = self.is_postgresql_9_5()
        if self.ignore_conflicts and not self.supports_ignore_conflicts:
            raise NotSupportedError(
                "This database backend does not support ignoring conflicts."
            )

        # Pull the CSV headers
        self.headers = self.get_headers()

        # Map them to the model
        self.mapping = self.get_mapping(mapping)

        # Make sure the everything is legit
        self.validate_mapping()

        # Configure the name of our temporary table to COPY into
        self.temp_table_name = temp_table_name or "temp_%s" % self.model._meta.db_table

    def save(self, silent: bool = False, stream: typing.TextIO = sys.stdout) -> int:
        """
        Saves the contents of the CSV file to the database.

        Override this method and use 'self.create(cursor)`,
        `self.copy(cursor)`, `self.insert(cursor)`, and `self.drop(cursor)`
        if you need functionality other than the default create/copy/insert/drop
        workflow.

         silent:
           By default, non-fatal error notifications are printed to stdout,
           but this keyword may be set to disable these notifications.

         stream:
           Status information will be written to this file handle. Defaults to
           using `sys.stdout`, but any object with a `write` method is
           supported.
        """
        logger.debug(f"Loading CSV to {self.model.__name__}")
        if not silent:
            stream.write(f"Loading CSV to {self.model.__name__}\n")

        # Connect to the database
        with self.conn.cursor() as c:
            self.create(c)
            self.copy(c)
            insert_count = self.insert(c)
            self.drop(c)

        if not silent:
            stream.write(f"{intcomma(insert_count)} records loaded\n")

        return insert_count

    def is_postgresql_9_5(self) -> bool:
        pg_version = getattr(self.conn, "pg_version", 0)
        return pg_version >= 90500

    def get_field(self, name: str) -> typing.Optional[Field]:
        """
        Returns any fields on the database model matching the provided name.
        """
        try:
            return self.model._meta.get_field(name)
        except FieldDoesNotExist:
            return None

    def get_mapping(self, mapping: typing.Dict[str, str]) -> typing.Dict[str, str]:
        """
        Returns a generated mapping based on the CSV header
        """
        if mapping:
            return OrderedDict(mapping)
        return {name: name for name in self.headers}

    def get_headers(self) -> typing.List[str]:
        """
        Returns the column headers from the csv as a list.
        """
        logger.debug(f"Retrieving headers from {self.csv_file}")

        # Check if it's a text or binary file
        is_binary = hasattr(self.csv_file, "mode") and "b" in getattr(
            self.csv_file, "mode", ""
        )

        if is_binary:
            # For binary files, we need to wrap it in a TextIOWrapper
            encoding = self.encoding or "utf-8"
            text_file = TextIOWrapper(
                typing.cast(typing.BinaryIO, self.csv_file), encoding=encoding
            )
            csv_reader = csv.reader(text_file, delimiter=self.delimiter)
            headers = next(csv_reader)
            # Detach the wrapper so the file stays open
            text_file.detach()
        else:
            # For text files or file-like objects without a mode attribute
            try:
                # Try to read directly
                csv_reader = csv.reader(
                    typing.cast(typing.Iterable[str], self.csv_file),
                    delimiter=self.delimiter,
                )
                headers = next(csv_reader)
            except (csv.Error, TypeError, AttributeError):
                # If that fails, try the binary approach as a fallback
                if hasattr(self.csv_file, "seek"):
                    self.csv_file.seek(0)
                encoding = self.encoding or "utf-8"
                text_file = TextIOWrapper(
                    typing.cast(typing.BinaryIO, self.csv_file), encoding=encoding
                )
                csv_reader = csv.reader(text_file, delimiter=self.delimiter)
                headers = next(csv_reader)
                text_file.detach()

        # Move back to the top of the file if possible
        if hasattr(self.csv_file, "seek"):
            self.csv_file.seek(0)

        return headers

    def validate_mapping(self) -> None:
        """
        Verify that the mapping provided by the user is acceptable.

        Raises errors if something goes wrong. Returns nothing if everything is kosher.
        """
        # Make sure all of the CSV headers in the mapping actually exist
        for map_header in self.mapping.values():
            if map_header not in self.headers:
                raise ValueError(f"Header '{map_header}' not found in CSV file")

        # Make sure all the model fields in the mapping actually exist
        for map_field in self.mapping.keys():
            if not self.get_field(map_field):
                raise FieldDoesNotExist(f"Model does not include {map_field} field")

        # Make sure any static mapping columns exist
        for static_field in self.static_mapping.keys():
            if not self.get_field(static_field):
                raise ValueError(f"Model does not include {static_field} field")

    #
    # CREATE commands
    #

    def prep_create(self) -> str:
        """
        Creates a CREATE statement that makes a new temporary table.

        Returns SQL that can be run.
        """
        sql = """CREATE TEMPORARY TABLE "%(table_name)s" (%(field_list)s);"""
        options = dict(table_name=self.temp_table_name)
        field_list = []

        # Loop through all the fields and CSV headers together
        for header in self.headers:
            # Format the SQL create statement
            string = '"%s" text' % header

            # Add the string to the list
            field_list.append(string)

        # Join all the field strings together
        options["field_list"] = ", ".join(field_list)

        # Mash together the SQL and pass it out
        return sql % options

    def create(self, cursor: CursorWrapper) -> None:
        """
        Generate and run create sql for the temp table.
        Runs a DROP on same prior to CREATE to avoid collisions.

        cursor:
          A cursor object on the db
        """
        logger.debug("Running CREATE command")
        self.drop(cursor)
        create_sql = self.prep_create()
        logger.debug(create_sql)
        cursor.execute(create_sql)

    #
    # COPY commands
    #

    def prep_copy(self) -> str:
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
            "db_table": self.temp_table_name,
            "extra_options": "",
            "header_list": ", ".join([f'"{h}"' for h in self.headers]),
        }
        if self.quote_character:
            options["extra_options"] += f" QUOTE '{self.quote_character}'"
        if self.delimiter:
            options["extra_options"] += f" DELIMITER '{self.delimiter}'"
        if self.null is not None:
            options["extra_options"] += f" NULL '{self.null}'"
        if self.force_not_null is not None:
            options["extra_options"] += " FORCE NOT NULL {}".format(
                ",".join(f'"{s}"' for s in self.force_not_null)
            )
        if self.force_null is not None:
            options["extra_options"] += " FORCE NULL {}".format(
                ",".join('"%s"' % s for s in self.force_null)
            )
        if self.encoding:
            options["extra_options"] += f" ENCODING '{self.encoding}'"
        return sql % options

    def pre_copy(self, cursor: CursorWrapper) -> None:
        pass

    def copy(self, cursor: CursorWrapper) -> None:
        """
        Generate and run the COPY command to copy data from csv to temp table.

        Calls `self.pre_copy(cursor)` and `self.post_copy(cursor)` respectively
        before and after running copy

        cursor:
          A cursor object on the db
        """
        # Run pre-copy hook
        self.pre_copy(cursor)

        logger.debug("Running COPY command")
        copy_sql = self.prep_copy()
        logger.debug(copy_sql)
        copy_from(
            cursor,
            copy_sql,
            typing.cast(typing.Union[typing.TextIO, typing.BinaryIO], self.csv_file),
        )

        # At this point all data has been loaded to the temp table
        if hasattr(self.csv_file, "close"):
            self.csv_file.close()

        # Run post-copy hook
        self.post_copy(cursor)

    def post_copy(self, cursor: CursorWrapper) -> None:
        pass

    #
    # INSERT commands
    #

    def insert_suffix(self) -> str:
        """
        Preps the suffix to the insert query.
        """
        if self.ignore_conflicts:
            return """
                ON CONFLICT DO NOTHING;
            """
        else:
            return ";"

    def prep_insert(self) -> str:
        """
        Creates a INSERT statement that reorders and cleans up
        the fields from the temporary table for insertion into the
        Django model.

        Returns SQL that can be run.
        """
        sql = """
            INSERT INTO "%(model_table)s" (%(model_fields)s) (
            SELECT %(temp_fields)s
            FROM "%(temp_table)s")%(insert_suffix)s
        """
        options = dict(
            model_table=self.model._meta.db_table,
            temp_table=self.temp_table_name,
            insert_suffix=self.insert_suffix(),
        )

        #
        # The model fields to be inserted into
        #

        model_fields = []
        for field_name in self.mapping.keys():
            field = self.get_field(field_name)
            if field is not None:
                model_fields.append('"%s"' % field.get_attname_column()[1])

        for k in self.static_mapping.keys():
            model_fields.append('"%s"' % k)

        options["model_fields"] = ", ".join(model_fields)

        #
        # The temp fields to SELECT from
        #

        temp_fields = []
        for field_name, header in self.mapping.items():
            # Pull the field object from the model
            field = self.get_field(field_name)
            if field is not None:
                field_type = field.db_type(self.conn)
                if field_type in ["serial", "bigserial"]:
                    field_type = "integer"

                # Format the SQL
                string = f'cast("{header}" as {field_type})'

                # Apply a datatype template override, if it exists
                if hasattr(field, "copy_template"):
                    string = field.copy_template % dict(name=header)

                # Apply a field specific template override, if it exists
                template_method = "copy_%s_template" % field.name
                if hasattr(self.model, template_method):
                    template = getattr(self.model(), template_method)()
                    string = template % dict(name=header)

            # Add field to list
            temp_fields.append(string)

        # Tack on static fields
        for v in self.static_mapping.values():
            temp_fields.append("'%s'" % v)

        # Join it all together
        options["temp_fields"] = ", ".join(temp_fields)

        # Pass it out
        return sql % options

    def pre_insert(self, cursor: CursorWrapper) -> None:
        pass

    def insert(self, cursor: CursorWrapper) -> int:
        """
        Generate and run the INSERT command to move data from the temp table
        to the concrete table.

        Calls `self.pre_copy(cursor)` and `self.post_copy(cursor)` respectively
        before and after running copy

        returns: the count of rows inserted

        cursor:
          A cursor object on the db
        """
        # Pre-insert hook
        self.pre_insert(cursor)

        logger.debug("Running INSERT command")
        insert_sql = self.prep_insert()
        logger.debug(insert_sql)
        cursor.execute(insert_sql)
        insert_count = cursor.rowcount
        logger.debug(f"{insert_count} rows inserted")

        # Post-insert hook
        self.post_insert(cursor)

        # Return the row count
        return insert_count if isinstance(insert_count, int) else 0

    def post_insert(self, cursor: CursorWrapper) -> None:
        pass

    #
    # DROP commands
    #

    def prep_drop(self) -> str:
        """
        Creates a DROP statement that gets rid of the temporary table.

        Return SQL that can be run.
        """
        return 'DROP TABLE IF EXISTS "%s";' % self.temp_table_name

    def drop(self, cursor: CursorWrapper) -> None:
        """
        Generate and run the DROP command for the temp table.

        cursor:
          A cursor object on the db
        """
        logger.debug("Running DROP command")
        drop_sql = self.prep_drop()
        logger.debug(drop_sql)
        cursor.execute(drop_sql)
