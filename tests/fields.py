from django.db.models.fields import IntegerField


class MyIntegerField(IntegerField):
    copy_template = """
        CASE
            WHEN "%(name)s" = 'x' THEN null
            ELSE "%(name)s"::int
        END
    """
