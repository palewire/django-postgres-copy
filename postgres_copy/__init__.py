#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.db import connection
from .copy_from import CopyMapping
from .copy_to import SQLCopyToCompiler, CopyToQuery
__version__ = '0.1.2'


class CopyQuerySet(models.QuerySet):
    """
    Subclass of QuerySet that adds from_csv to to_csv methods.
    """
    def from_csv(self, csv_path, mapping, **kwargs):
        """
        Copy CSV file to model using the provided mapping.
        """
        mapping = CopyMapping(self.model, csv_path, mapping, **kwargs)
        mapping.save()

    def to_csv(self, csv_path, *fields):
        """
        Copy current objects in QuerySet to a file at csv_path.
        """
        query = self.query.clone(CopyToQuery)
        query.copy_to_fields = fields
        compiler = query.get_compiler(self.db, connection=connection)
        compiler.execute_sql(csv_path)


CopyManager = models.Manager.from_queryset(CopyQuerySet)


__all__ = (
    'CopyMapping',
    'SQLCopyToCompiler',
    'CopyToQuery',
    'CopyManager',
)
