import os
from datetime import date

from django.db import ProgrammingError

from .models import (
    MockObject,
    ExtendedMockObject,
    LimitedMockObject,
    OverloadMockObject,
    HookedCopyMapping)
from postgres_copy import CopyMapping
from django.test import TestCase


class PostgresCopyTest(TestCase):

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.name_path = os.path.join(self.data_dir, 'names.csv')
        self.foreign_path = os.path.join(self.data_dir, 'foreignkeys.csv')
        self.pipe_path = os.path.join(self.data_dir, 'pipes.csv')
        self.null_path = os.path.join(self.data_dir, 'nulls.csv')
        self.backwards_path = os.path.join(self.data_dir, 'backwards.csv')

    def tearDown(self):
        MockObject.objects.all().delete()
        ExtendedMockObject.objects.all().delete()
        LimitedMockObject.objects.all().delete()
        OverloadMockObject.objects.all().delete()

    def test_bad_call(self):
        with self.assertRaises(TypeError):
            CopyMapping()

    def test_bad_csv(self):
        with self.assertRaises(ValueError):
            CopyMapping(
                MockObject,
                '/foobar.csv',
                dict(name='NAME', number='NUMBER', dt='DATE'),
                using='sqlite'
            )

    def test_bad_backend(self):
        with self.assertRaises(TypeError):
            CopyMapping(
                MockObject,
                self.name_path,
                dict(name='NAME', number='NUMBER', dt='DATE'),
                using='sqlite'
            )

    def test_bad_header(self):
        with self.assertRaises(ValueError):
            CopyMapping(
                MockObject,
                self.name_path,
                dict(name='NAME1', number='NUMBER', dt='DATE'),
            )

    def test_bad_field(self):
        with self.assertRaises(ValueError):
            CopyMapping(
                MockObject,
                self.name_path,
                dict(name1='NAME', number='NUMBER', dt='DATE'),
            )

    def test_limited_fields(self):
        CopyMapping(
            LimitedMockObject,
            self.name_path,
            dict(name='NAME', dt='DATE'),
        )

    def test_simple_save(self):
        c = CopyMapping(
            MockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_limited_save(self):
        c = CopyMapping(
            LimitedMockObject,
            self.name_path,
            dict(name='NAME', dt='DATE')
        )
        c.save()
        self.assertEqual(LimitedMockObject.objects.count(), 3)
        self.assertEqual(
            LimitedMockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_save_foreign_key(self):
        c = CopyMapping(
            MockObject,
            self.foreign_path,
            dict(name='NAME', number='NUMBER', dt='DATE', parent='PARENT')
        )

        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').parent_id, 4)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_silent_save(self):
        c = CopyMapping(
            MockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        c.save(silent=True)
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_pipe_save(self):
        c = CopyMapping(
            MockObject,
            self.pipe_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            delimiter="|",
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_null_save(self):
        c = CopyMapping(
            MockObject,
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            null='',
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(MockObject.objects.get(name='NULLBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_backwards_save(self):
        c = CopyMapping(
            MockObject,
            self.backwards_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_field_override_save(self):
        c = CopyMapping(
            MockObject,
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BADBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_encoding_save(self):
        c = CopyMapping(
            MockObject,
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            encoding='UTF-8'
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BADBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_static_values(self):
        c = CopyMapping(
            ExtendedMockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            static_mapping={'static_val':1,'static_string':'test'}
        )
        c.save()
        self.assertEqual(
            ExtendedMockObject.objects.filter(static_val = 1).count(),
            3
        )
        self.assertEqual(
            ExtendedMockObject.objects.filter(static_string = 'test').count(),
            3
        )

    def test_bad_static_values(self):
        with self.assertRaises(ValueError):
            c = CopyMapping(
                ExtendedMockObject,
                self.name_path,
                dict(name='NAME', number='NUMBER', dt='DATE'),
                encoding='UTF-8',
                static_mapping={'static_bad':1,}
            )
            c.save()

    def test_save_foreign_key(self):
        c = CopyMapping(
            MockObject,
            self.foreign_path,
            dict(name='NAME', number='NUMBER', dt='DATE', parent='PARENT')
        )

        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').parent_id, 4)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_overload_save(self):
        c = CopyMapping(
            OverloadMockObject,
            self.name_path,
            dict(name='NAME', lower_name='NAME', upper_name='NAME', number='NUMBER', dt='DATE'),
        )
        c.save()
        self.assertEqual(OverloadMockObject.objects.count(), 3)
        self.assertEqual(OverloadMockObject.objects.get(name='ben').number, 1)
        self.assertEqual(OverloadMockObject.objects.get(lower_name='ben').number, 1)
        self.assertEqual(OverloadMockObject.objects.get(upper_name='BEN').number, 1)
        self.assertEqual(
            OverloadMockObject.objects.get(name='ben').dt,
            date(2012, 1, 1)
        )
        omo = OverloadMockObject.objects.first()
        self.assertEqual(omo.name.lower(), omo.lower_name)

    def test_missing_overload_field(self):
        with self.assertRaises(ValueError):
            c = CopyMapping(
                OverloadMockObject,
                self.name_path,
                dict(name='NAME', number='NUMBER', dt='DATE', missing='NAME'),
            )


    def test_save_steps(self):
        c = CopyMapping(
            MockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        cursor = c.conn.cursor()

        c.create(cursor)
        cursor.execute("""SELECT count(*) FROM %s;""" % c.temp_table_name)
        self.assertEquals(cursor.fetchone()[0], 0)
        cursor.execute("""SELECT count(*) FROM %s;""" % c.model._meta.db_table)
        self.assertEquals(cursor.fetchone()[0], 0)

        c.copy(cursor)
        cursor.execute("""SELECT count(*) FROM %s;""" % c.temp_table_name)
        self.assertEquals(cursor.fetchone()[0], 3)
        cursor.execute("""SELECT count(*) FROM %s;""" % c.model._meta.db_table)
        self.assertEquals(cursor.fetchone()[0], 0)

        c.insert(cursor)
        cursor.execute("""SELECT count(*) FROM %s;""" % c.model._meta.db_table)
        self.assertEquals(cursor.fetchone()[0], 3)

        c.drop(cursor)
        self.assertEquals(cursor.statusmessage, 'DROP TABLE')
        cursor.close()

    def test_hooks(self):
        c = HookedCopyMapping(
            MockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        cursor = c.conn.cursor()

        c.create(cursor)
        self.assertRaises(AttributeError, lambda: c.ran_pre_copy)
        self.assertRaises(AttributeError, lambda: c.ran_post_copy)
        self.assertRaises(AttributeError, lambda: c.ran_pre_insert)
        self.assertRaises(AttributeError, lambda: c.ran_post_insert)
        c.copy(cursor)
        self.assertTrue(c.ran_pre_copy)
        self.assertTrue(c.ran_post_copy)
        self.assertRaises(AttributeError, lambda: c.ran_pre_insert)
        self.assertRaises(AttributeError, lambda: c.ran_post_insert)

        c.insert(cursor)
        self.assertTrue(c.ran_pre_copy)
        self.assertTrue(c.ran_post_copy)
        self.assertTrue(c.ran_pre_insert)
        self.assertTrue(c.ran_post_insert)

        c.drop(cursor)
        cursor.close()
