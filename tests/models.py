from django.db import models


class MockObject(models.Model):
    name = models.CharField(max_length=500)
    number = models.IntegerField(null=True)
    objects = models.Manager()

    class Meta:
        app_label = 'tests'
