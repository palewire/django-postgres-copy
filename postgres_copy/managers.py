#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db import connection
from django.db.transaction import TransactionManagementError
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
                logger.debug("Dropping field constraint from {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_constraint = False
                args = (self.model, field, field_copy)
                self.edit_schema(schema_editor, 'alter_field', args)

            # Remove remaining constraints
            for constraint in getattr(self.model._meta, 'constraints', []):
                logger.debug("Dropping constraint '{}'".format(constraint.name))
                args = (self.model, constraint)
                self.edit_schema(schema_editor, 'remove_constraint', args)

    def drop_indexes(self):
        """
        Drop indexes on the model and its fields.
        """
        logger.debug("Dropping indexes from {}".format(self.model.__name__))
        with connection.schema_editor() as schema_editor:
            # Remove any "index_together" constraints
            if self.model._meta.index_together:
                logger.debug("Dropping index_together of {}".format(self.model._meta.index_together))
                args = (self.model, self.model._meta.index_together, ())
                self.edit_schema(schema_editor, 'alter_index_together', args)

            # Remove any field indexes
            for field in self.indexed_fields:
                logger.debug("Dropping field index from {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_index = False
                args = (self.model, field, field_copy)
                self.edit_schema(schema_editor, 'alter_field', args)

            # Remove remaining indexes
            for index in getattr(self.model._meta, 'indexes', []):
                logger.debug("Dropping index '{}'".format(index.name))
                args = (self.model, index)
                self.edit_schema(schema_editor, 'remove_index', args)

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

            # Add any field constraints
            for field in self.constrained_fields:
                logger.debug("Adding field constraint to {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_constraint = False
                args = (self.model, field_copy, field)
                self.edit_schema(schema_editor, 'alter_field', args)

            # Add remaining constraints
            for constraint in getattr(self.model._meta, 'constraints', []):
                logger.debug("Adding constraint '{}'".format(constraint.name))
                args = (self.model, constraint)
                self.edit_schema(schema_editor, 'add_constraint', args)

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
                logger.debug("Restoring field index to {}".format(field))
                field_copy = field.__copy__()
                field_copy.db_index = False
                args = (self.model, field_copy, field)
                self.edit_schema(schema_editor, 'alter_field', args)

            # Add remaining indexes
            for index in getattr(self.model._meta, 'indexes', []):
                logger.debug("Adding index '{}'".format(index.name))
                args = (self.model, index)
                self.edit_schema(schema_editor, 'add_index', args)


class CopyQuerySet(ConstraintQuerySet):
    """
    Subclass of QuerySet that adds from_csv and to_csv methods.
    """
    def from_csv(self, csv_path, mapping=None, drop_constraints=True, drop_indexes=True, silent=True, **kwargs):
        """
        Copy CSV file from the provided path to the current model using the provided mapping.
        """
        # Dropping constraints or indices will fail with an opaque error for all but
        # very trivial databases which wouldn't benefit from this optimization anyway.
        # So, we prevent the user from even trying to avoid confusion.
        if drop_constraints or drop_indexes:
            try:
                connection.validate_no_atomic_block()
            except TransactionManagementError:
                raise TransactionManagementError("You are attempting to drop constraints or "
                                                 "indexes inside a transaction block, which is "
                                                 "very likely to fail.  If it doesn't fail, you "
                                                 "wouldn't gain any significant benefit from it "
                                                 "anyway.  Either remove the transaction block, or set "
                                                 "drop_constraints=False and drop_indexes=False.")

        # NOTE: See GH Issue #117
        #       We could remove this block if drop_constraints' default was False
        if on_conflict := kwargs.get('on_conflict'):
            if target := on_conflict.get('target'):
                if target in [c.name for c in self.model._meta.constraints]:
                    drop_constraints = False
            elif on_conflict.get('action') == 'ignore':
                drop_constraints = False

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

    def to_csv(self, csv_path=None, *fields, **kwargs):
        """
        Copy current QuerySet to CSV at provided path or file-like object.
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
        query.copy_to_delimiter = "DELIMITER '{}'".format(kwargs.get('delimiter', ','))

        # Header
        with_header = kwargs.get('header', True)
        query.copy_to_header = "HEADER" if with_header else ""

        # Null string
        null_string = kwargs.get('null', None)
        query.copy_to_null_string = "NULL '{}'".format(null_string) if null_string else ""

        # Quote character
        quote_char = kwargs.get('quote', None)
        query.copy_to_quote_char = "QUOTE '{}'".format(quote_char) if quote_char else ""

        # Force quote on columns
        force_quote = kwargs.get('force_quote', None)
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
        set_encoding = kwargs.get('encoding', None)
        query.copy_to_encoding = "ENCODING '{}'".format(set_encoding) if set_encoding else ""

        # Escape character
        escape_char = kwargs.get('escape', None)
        query.copy_to_escape = "ESCAPE '{}'".format(escape_char) if escape_char else ""

        # Run the query
        compiler = query.get_compiler(self.db, connection=connection)
        data = compiler.execute_sql(csv_path)

        # If no csv_path is provided, then the query will come back as a string.
        if csv_path is None:
            # So return that.
            return data


CopyManager = models.Manager.from_queryset(CopyQuerySet)
