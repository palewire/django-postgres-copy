from django.db import models
from .fields import MyIntegerField


class MockObject(models.Model):
    name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column='num')
    dt = models.DateField(null=True)
    parent = models.ForeignKey('MockObject', null=True, default=None)

    class Meta:
        app_label = 'tests'

    def copy_name_template(self):
        return 'upper("%(name)s")'
    copy_name_template.copy_type = 'text'


class ExtendedMockObject(models.Model):
    static_val = models.IntegerField()
    name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column='num')
    dt = models.DateField(null=True)
    static_string = models.CharField(max_length=5)

    class Meta:
        app_label = 'tests'

    def copy_name_template(self):
        return 'upper("%(name)s")'
    copy_name_template.copy_type = 'text'


class OverloadMockObject(models.Model):
    name = models.CharField(max_length=500)
    lower_name = models.CharField(max_length=500)
    number = MyIntegerField(null=True, db_column='num')
    dt = models.DateField(null=True)
    parent = models.ForeignKey('MockObject', null=True, default=None)

    class Meta:
        app_label = 'tests'

    def copy_name_template(self):
        return 'upper("%(name)s")'
    copy_name_template.copy_type = 'text'

    def copy_lower_name_template(self):
        return 'lower("%(name)s")'
    copy_name_template.copy_type = 'text'

