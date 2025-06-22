import django
from django.db import models

from postgres_copy import CopyManager, CopyMapping

from .fields import MyIntegerField


class MockObject(models.Model):
    name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column="num")
    dt = models.DateField(null=True)
    parent = models.ForeignKey(
        "MockObject", on_delete=models.CASCADE, null=True, default=None
    )
    objects = CopyManager()

    class Meta:
        app_label = "tests"
        unique_together = ("name", "number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if django.get_version() <= "5.1":
            self._meta.index_together = ("name", "number")
        else:
            self._meta.indexes = [models.Index(fields=["name", "number"])]

    def copy_name_template(self):
        return 'upper("%(name)s")'


class MockFKObject(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column="num")
    dt = models.DateField(null=True)
    parent = models.ForeignKey(
        "MockFKObject", on_delete=models.CASCADE, null=True, default=None
    )
    objects = CopyManager()

    class Meta:
        app_label = "tests"

    def copy_name_template(self):
        return 'upper("%(name)s")'


class MockBlankObject(models.Model):
    name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column="num")
    dt = models.DateField(null=True)
    color = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey(
        "MockObject", on_delete=models.CASCADE, null=True, default=None
    )
    objects = CopyManager()

    class Meta:
        app_label = "tests"

    def copy_name_template(self):
        return 'upper("%(name)s")'


class ExtendedMockObject(models.Model):
    static_val = models.IntegerField()
    name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column="num")
    dt = models.DateField(null=True)
    static_string = models.CharField(max_length=5)
    objects = CopyManager()

    class Meta:
        app_label = "tests"

    def copy_name_template(self):
        return 'upper("%(name)s")'


class LimitedMockObject(models.Model):
    name = models.CharField(max_length=500)
    dt = models.DateField(null=True)
    objects = CopyManager()

    class Meta:
        app_label = "tests"

    def copy_name_template(self):
        return 'upper("%(name)s")'


class OverloadMockObject(models.Model):
    name = models.CharField(max_length=500)
    upper_name = models.CharField(max_length=500)
    lower_name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column="num")
    dt = models.DateField(null=True)
    objects = CopyManager()

    class Meta:
        app_label = "tests"

    def copy_upper_name_template(self):
        return 'upper("%(name)s")'

    def copy_lower_name_template(self):
        return 'lower("%(name)s")'


class HookedCopyMapping(CopyMapping):
    def pre_copy(self, cursor):
        self.ran_pre_copy = True

    def post_copy(self, cursor):
        self.ran_post_copy = True

    def pre_insert(self, cursor):
        self.ran_pre_insert = True

    def post_insert(self, cursor):
        self.ran_post_insert = True


class SecondaryMockObject(models.Model):
    text = models.CharField(max_length=500)
    objects = CopyManager()


class UniqueMockObject(models.Model):
    name = models.CharField(max_length=500, unique=True)
    objects = CopyManager()
