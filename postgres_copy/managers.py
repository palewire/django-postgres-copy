#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db import connection
from .copy_to import CopyToQuery
from .copy_from import CopyMapping
logger = logging.getLogger(__name__)


class ConstraintQuerySet(models.QuerySet):
    """
    Utilities for temporarily dropping and restoring constraints and indexes.
    """
    @property
    def constrained_fields(self):
        """
        Returns list of model's fields with db_constraint set to True.
        """
        return [
            f for f in self.model._meta.fields
            if hasattr(f, 'db_constraint') and f.db_constraint
        ]

    @property
    def indexed_fields(self):
        """
        Returns list of model's fields with db_index set to True.
        """
        return [f for f in self.model._meta.fields if f.db_index]

    def edit_schema(self, schema_editor, method_name, args):
        """
        Edits the schema without throwing errors.

        This allows for the add and drop methods to be run frequently and without fear.
        """
        try:
            getattr(schema_editor, method_name)(*args)
        except Exception:
            logger.debug("Edit of {}.{} failed. Skipped".format(schema_editor, method_name))
            pass

    def drop_constraints(self):
        """
        Drop constraints on the model and its fields.
        """
        logger.debug("Dropping constraints from {}".format(self.model.__name__))
        with connection.schema_editor() as schema_editor:
            # Remove any "unique_together" constraints
            if self.model._meta.unique_together:
                logger.debug("Dropping unique_together of {}".format(self.model._meta.unique_together))
                args = (self.model, self.model._meta.unique_together, ())
                self.edit_schema(schema_editor, 'alter_unique_together', args)

            # Remove any field constraints
            for field in self.constrained_fields:
                logger.debug("Dropping constraints from {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_constraint = False
                args = (self.model, field, field_copy)
                self.edit_schema(schema_editor, 'alter_field', args)

    def drop_indexes(self):
        """
        Drop indexes on the model and its fields.
        """
        logger.debug("Dropping indexes from {}".format(self.model.__name__))
        with connection.schema_editor() as schema_editor:
            # Remove any "index_together" constraints
            logger.debug("Dropping index_together of {}".format(self.model._meta.index_together))
            if self.model._meta.index_together:
                args = (self.model, self.model._meta.index_together, ())
                self.edit_schema(schema_editor, 'alter_index_together', args)

            # Remove any field indexes
            for field in self.indexed_fields:
                logger.debug("Dropping index from {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_index = False
                args = (self.model, field, field_copy)
                self.edit_schema(schema_editor, 'alter_field', args)

    def restore_constraints(self):
        """
        Restore constraints on the model and its fields.
        """
        logger.debug("Adding constraints to {}".format(self.model.__name__))
        with connection.schema_editor() as schema_editor:
            # Add any "unique_together" contraints from the database
            if self.model._meta.unique_together:
                logger.debug("Adding unique_together of {}".format(self.model._meta.unique_together))
                args = (self.model, (), self.model._meta.unique_together)
                self.edit_schema(schema_editor, 'alter_unique_together', args)

            # Add any constraints to the fields
            for field in self.constrained_fields:
                logger.debug("Adding constraints to {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_constraint = False
                args = (self.model, field_copy, field)
                self.edit_schema(schema_editor, 'alter_field', args)

    def restore_indexes(self):
        """
        Restore indexes on the model and its fields.
        """
        logger.debug("Adding indexes to {}".format(self.model.__name__))
        with connection.schema_editor() as schema_editor:
            # Add any "index_together" contraints to the database.
            if self.model._meta.index_together:
                logger.debug("Restoring index_together of {}".format(self.model._meta.index_together))
                args = (self.model, (), self.model._meta.index_together)
                self.edit_schema(schema_editor, 'alter_index_together', args)

            # Add any indexes to the fields
            for field in self.indexed_fields:
                logger.debug("Restoring index to {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_index = False
                args = (self.model, field_copy, field)
                self.edit_schema(schema_editor, 'alter_field', args)


class CopyQuerySet(ConstraintQuerySet):
    """
    Subclass of QuerySet that adds from_csv and to_csv methods.
    """
    def from_csv(self, csv_path, mapping=None, drop_constraints=True, drop_indexes=True, silent=True, **kwargs):
        """
        Copy CSV file from the provided path to the current model using the provided mapping.
        """
        mapping = CopyMapping(self.model, csv_path, mapping, **kwargs)

        if drop_constraints:
            self.drop_constraints()
        if drop_indexes:
            self.drop_indexes()

        insert_count = mapping.save(silent=silent)

        if drop_constraints:
            self.restore_constraints()
        if drop_indexes:
            self.restore_indexes()

        return insert_count

    def to_csv(self, csv_path=None, *fields,
        delimiter=',',
        header=True,
        null=None,
        quote=None,
        force_quote=None,
        encoding=None,
        escape=None):
        """
        Copy current QuerySet to CSV at provided path.
        """
        try:
            # For Django 2.0 forward
            query = self.query.chain(CopyToQuery)
        except AttributeError:
            # For Django 1.11 backward
            query = self.query.clone(CopyToQuery)

        # Get fields
        query.copy_to_fields = fields

        # Delimiter
        query.copy_to_delimiter = "DELIMITER '{}'".format(delimiter)

        # Header
        query.copy_to_header = "HEADER" if header else ""

        # Null string
        query.copy_to_null_string = "NULL '{}'".format(null) if null else ""

        # Quote character
        query.copy_to_quote_char = "QUOTE '{}'".format(quote) if quote else ""

        # Force quote on columns
        if force_quote:
            # If it's a list of fields, pass them in with commas
            if type(force_quote) == list:
                query.copy_to_force_quote = \
                    "FORCE QUOTE {}".format(", ".join(column for column in force_quote))
            # If it's True or a * force quote everything
            elif force_quote is True or force_quote == "*":
                query.copy_to_force_quote = "FORCE QUOTE *"
            # Otherwise, assume it's a string and pass it through
            else:
                query.copy_to_force_quote = "FORCE QUOTE {}".format(force_quote)
        else:
            query.copy_to_force_quote = ""

        # Encoding
        query.copy_to_encoding = "ENCODING '{}'".format(encoding) if encoding else ""

        # Escape character
        query.copy_to_escape = "ESCAPE '{}'".format(escape) if escape else ""

        # Run the query
        compiler = query.get_compiler(self.db, connection=connection)
        data = compiler.execute_sql(csv_path)

        # If no csv_path is provided, then the query will come back as a string.
        if csv_path is None:
            # So return that.
            return data


CopyManager = models.Manager.from_queryset(CopyQuerySet)
