import io
import mock
import os
import csv
from datetime import date
from .models import (
    MockObject,
    MockFKObject,
    MockBlankObject,
    ExtendedMockObject,
    LimitedMockObject,
    OverloadMockObject,
    HookedCopyMapping,
    SecondaryMockObject,
    UniqueMockObject
)
from django.test import TestCase
from django.db import transaction
from django.db.transaction import TransactionManagementError
from django.db.models import Count
from postgres_copy import CopyMapping
from django.core.exceptions import FieldDoesNotExist


class BaseTest(TestCase):
    databases = ["default", "sqlite", "other", "secondary"]

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.name_path = os.path.join(self.data_dir, 'names.csv')
        self.foreign_path = os.path.join(self.data_dir, 'foreignkeys.csv')
        self.pipe_path = os.path.join(self.data_dir, 'pipes.csv')
        self.quote_path = os.path.join(self.data_dir, 'quote.csv')
        self.blank_null_path = os.path.join(self.data_dir, 'blanknulls.csv')
        self.null_path = os.path.join(self.data_dir, 'nulls.csv')
        self.backwards_path = os.path.join(self.data_dir, 'backwards.csv')
        self.matching_headers_path = os.path.join(
            self.data_dir,
            'matching_headers.csv'
        )
        self.secondarydb_path = os.path.join(self.data_dir, 'secondary_db.csv')

    def tearDown(self):
        MockObject.objects.all().delete()
        MockFKObject.objects.all().delete()
        ExtendedMockObject.objects.all().delete()
        LimitedMockObject.objects.all().delete()
        OverloadMockObject.objects.all().delete()
        SecondaryMockObject.objects.all().delete()


class PostgresCopyToTest(BaseTest):

    def setUp(self):
        super(PostgresCopyToTest, self).setUp()
        self.export_path = os.path.join(os.path.dirname(__file__), 'export.csv')
        self.export_files = [
            io.StringIO(),
            io.BytesIO()
        ]

    def tearDown(self):
        super(PostgresCopyToTest, self).tearDown()
        if os.path.exists(self.export_path):
            os.remove(self.export_path)

    def _load_objects(self, file_path, mapping=dict(name='NAME', number='NUMBER', dt='DATE')):
        MockObject.objects.from_csv(file_path, mapping)

    def _load_secondary_objects(self, file_path, mapping=dict(text='TEXT')):
        SecondaryMockObject.objects.from_csv(file_path, mapping)

    # These tests are using simple enough databases that they can safely proceed
    # with uploading objects from CSV despite being within a transaction block.
    # In particular, Django wraps all tests in a transaction so that database
    # changes can be rolled back.  Therefore, we bypass validate_no_atomic_block
    # here and elsewhere.
    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.to_csv(self.export_path)
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_to_file(self, _):
        self._load_objects(self.name_path)
        for f in self.export_files:
            MockObject.objects.to_csv(f)
            reader = csv.DictReader(f)
            self.assertTrue(
                ['BEN', 'JOE', 'JANE'],
                [i['name'] for i in reader]
            )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_to_str(self, _):
        self._load_objects(self.name_path)
        export = MockObject.objects.to_csv()
        self.assertEqual(export, b"""id,name,num,dt,parent_id
89,BEN,1,2012-01-01,
90,JOE,2,2012-01-02,
91,JANE,3,2012-01-03,
""")

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_header_setting(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.to_csv(self.export_path)
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )
        MockObject.objects.to_csv(self.export_path, header=True)
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )
        MockObject.objects.to_csv(self.export_path, header=False)
        reader = csv.DictReader(open(self.export_path, 'r'))
        with self.assertRaises(KeyError):
            [i['name'] for i in reader]
        self.assertTrue(
            ['JOE', 'JANE'],
            [i['BEN'] for i in reader]
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_delimiter(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.to_csv(self.export_path, delimiter=';')
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'), delimiter=';')
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_null_string(self, _):
        self._load_objects(self.blank_null_path)
        MockObject.objects.to_csv(self.export_path)
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['1', '2', '3', '', ''],
            [i['num'] for i in reader]
        )

        MockObject.objects.to_csv(self.export_path, null='NULL')
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['1', '2', '3', 'NULL', ''],
            [i['num'] for i in reader]
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_quote_character_and_force_quoting(self, _):
        self._load_objects(self.name_path)

        # Single column being force_quoted with pipes
        MockObject.objects.to_csv(self.export_path, quote='|', force_quote='NAME')
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['|BEN|', '|JOE|', '|JANE|'],
            [i['name'] for i in reader]
        )

        # Multiple columns passed as a list and force_quoted with pipes
        MockObject.objects.to_csv(self.export_path, quote='|', force_quote=['NAME', 'DT'])
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            [('|BEN|', '|2012-01-01|'), ('|JOE|', '|2012-01-02|'), ('|JANE|', '|2012-01-03|')],
            [(i['name'], i['dt']) for i in reader]
        )

        # All columns force_quoted with pipes
        MockObject.objects.to_csv(self.export_path, quote='|', force_quote=True)
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        reader = next(reader)
        self.assertTrue(
            ['|BEN|', '|1|', '|2012-01-01|'],
            list(reader.values())[1:]
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_encoding(self, _):
        self._load_objects(self.name_path)

        # Function should pass on valid inputs ('utf-8', 'Unicode', 'LATIN2')
        # If these don't raise an error, then they passed nicely
        MockObject.objects.to_csv(self.export_path, encoding='utf-8')
        MockObject.objects.to_csv(self.export_path, encoding='Unicode')
        MockObject.objects.to_csv(self.export_path, encoding='LATIN2')

        # Function should fail on known invalid inputs ('ASCII', 'utf-16')
        self.assertRaises(Exception, MockObject.objects.to_csv(self.export_path), encoding='utf-16')
        self.assertRaises(Exception, MockObject.objects.to_csv(self.export_path), encoding='ASCII')

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_escape_character(self, _):
        self._load_objects(self.name_path)

        # Function should not fail on known valid inputs
        MockObject.objects.to_csv(self.export_path, escape='-')

        # Function should fail on known invalid inputs
        self.assertRaises(Exception, MockObject.objects.to_csv(self.export_path), escape='--')

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_filter(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.filter(name="BEN").to_csv(self.export_path)
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['BEN'],
            [i['name'] for i in reader]
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_fewer_fields(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.to_csv(self.export_path, 'name')
        reader = csv.DictReader(open(self.export_path, 'r'))
        for row in reader:
            self.assertTrue(row['name'] in ['BEN', 'JOE', 'JANE'])
            self.assertTrue(len(row.keys()), 1)

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_related_fields(self, _):
        MockFKObject.objects.from_csv(
            self.foreign_path,
            mapping=dict(id="NUMBER", name='NAME', number='NUMBER', dt='DATE', parent='PARENT')
        )
        MockFKObject.objects.to_csv(self.export_path, 'name', 'parent__id', 'parent__name')
        reader = csv.DictReader(open(self.export_path, 'r'))
        for row in reader:
            self.assertTrue(row['parent_id'] in ['1', '2', '3'])
            self.assertTrue(len(row.keys()), 3)

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_annotate(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.annotate(name_count=Count('name')).to_csv(self.export_path)
        reader = csv.DictReader(open(self.export_path, 'r'))
        for row in reader:
            self.assertTrue('name_count' in row)
            self.assertTrue(row['name_count'] == '1')

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_extra(self, _):
        self._load_objects(self.name_path)
        MockObject.objects.extra(select={'lower': 'LOWER("name")'}).to_csv(self.export_path)
        reader = csv.DictReader(open(self.export_path, 'r'))
        for row in reader:
            self.assertTrue('lower' in row)

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_export_multi_db(self, _):
        self._load_objects(self.name_path)
        self._load_secondary_objects(self.secondarydb_path)

        MockObject.objects.to_csv(self.export_path)
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )

        SecondaryMockObject.objects.to_csv(self.export_path)
        self.assertTrue(os.path.exists(self.export_path))
        reader = csv.DictReader(open(self.export_path, 'r'))
        items = [i['text'] for i in reader]
        self.assertEqual(len(items), 3)
        self.assertEqual(
            ['SECONDARY TEXT 1', 'SECONDARY TEXT 2', 'SECONDARY TEXT 3'],
            items
        )


class PostgresCopyFromTest(BaseTest):

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
        with self.assertRaises(FieldDoesNotExist):
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

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_simple_save_with_fileobject(self, _):
        f = open(self.name_path, 'r')
        MockObject.objects.from_csv(
            f,
            dict(name='NAME', number='NUMBER', dt='DATE')
        )
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_save_with_binary_fileobject(self, _):
        f = open(self.name_path, 'rb')
        MockObject.objects.from_csv(
            f,
            dict(name='NAME', number='NUMBER', dt='DATE')
        )
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_atomic_block(self):
        with transaction.atomic():
            try:
                f = open(self.name_path, 'r')
                MockObject.objects.from_csv(
                    f,
                    dict(name='NAME', number='NUMBER', dt='DATE')
                )
                self.fail("Expected TransactionManagementError.")
            except TransactionManagementError:
                # Expected
                pass

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_simple_save(self, _):
        insert_count = MockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE')
        )
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )
        self.assertEqual(insert_count, 3)

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_loud_save(self, _):
        MockObject.objects.from_csv(
            self.name_path,
            mapping=dict(name='NAME', number='NUMBER', dt='DATE'),
            silent=False
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_match_heading(self, _):
        MockObject.objects.from_csv(self.matching_headers_path)
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_bad_match_heading(self, _):
        with self.assertRaises(FieldDoesNotExist):
            MockObject.objects.from_csv(self.name_path)

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_limited_save(self, _):
        LimitedMockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME', dt='DATE')
        )
        self.assertEqual(LimitedMockObject.objects.count(), 3)
        self.assertEqual(
            LimitedMockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_save_foreign_key(self, _):
        MockFKObject.objects.from_csv(
            self.foreign_path,
            dict(id="NUMBER", name='NAME', number='NUMBER', dt='DATE', parent='PARENT')
        )
        self.assertEqual(MockFKObject.objects.count(), 3)
        self.assertEqual(MockFKObject.objects.get(name='BEN').parent_id, 3)
        self.assertEqual(
            MockFKObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_save_foreign_key_by_id(self, _):
        MockFKObject.objects.from_csv(
            self.foreign_path,
            dict(id="NUMBER", name='NAME', number='NUMBER', dt='DATE', parent_id='PARENT')
        )
        self.assertEqual(MockFKObject.objects.count(), 3)
        self.assertEqual(MockFKObject.objects.get(name='BEN').parent_id, 3)
        self.assertEqual(
            MockFKObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_save_pk_field_type(self, _):
        # Django casts PK fields to "serial"
        MockObject.objects.from_csv(
            self.name_path,
            dict(id='NUMBER', name='NAME', dt='DATE'),
        )
        self.assertEqual(MockObject.objects.count(), 3)

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

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_pipe_save(self, _):
        MockObject.objects.from_csv(
            self.pipe_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            delimiter="|",
        )
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_quote_save(self, _):
        MockObject.objects.from_csv(
            self.quote_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            delimiter="\t",
            quote_character='`'
        )
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(number=1).name, 'B`EN')
        self.assertEqual(MockObject.objects.get(number=2).name, 'JO\tE')
        self.assertEqual(MockObject.objects.get(number=3).name, 'JAN"E')

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_null_save(self, _):
        MockObject.objects.from_csv(
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            null='',
        )
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(MockObject.objects.get(name='NULLBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_force_not_null_save(self, _):
        MockBlankObject.objects.from_csv(
            self.blank_null_path,
            dict(name='NAME', number='NUMBER', dt='DATE', color='COLOR'),
            force_not_null=('COLOR',),
        )
        self.assertEqual(MockBlankObject.objects.count(), 5)
        self.assertEqual(MockBlankObject.objects.get(name='BEN').color, 'red')
        self.assertEqual(MockBlankObject.objects.get(name='NULLBOY').color, '')
        self.assertEqual(
            MockBlankObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_force_null_save(self, _):
        MockObject.objects.from_csv(
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            force_null=('NUMBER',),
        )
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(MockObject.objects.get(name='NULLBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_backwards_save(self, _):
        MockObject.objects.from_csv(
            self.backwards_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_field_override_save(self, _):
        MockObject.objects.from_csv(
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BADBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_encoding_save(self, _):
        MockObject.objects.from_csv(
            self.null_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            encoding='UTF-8'
        )
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BADBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_ignore_conflicts(self, _):
        UniqueMockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME'),
            ignore_conflicts=True
        )
        UniqueMockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME'),
            ignore_conflicts=True
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_static_values(self, _):
        ExtendedMockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            static_mapping=dict(static_val=1, static_string='test')
        )
        self.assertEqual(
            ExtendedMockObject.objects.filter(static_val=1).count(),
            3
        )
        self.assertEqual(
            ExtendedMockObject.objects.filter(static_string='test').count(),
            3
        )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_bad_static_values(self, _):
        with self.assertRaises(ValueError):
            ExtendedMockObject.objects.from_csv(
                self.name_path,
                dict(name='NAME', number='NUMBER', dt='DATE'),
                encoding='UTF-8',
                static_mapping=dict(static_bad=1)
            )

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_overload_save(self, _):
        OverloadMockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME', lower_name='NAME', upper_name='NAME', number='NUMBER', dt='DATE'),
        )
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
        with self.assertRaises(FieldDoesNotExist):
            CopyMapping(
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


class MultiDbTest(BaseTest):
    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_from_csv(self, _):
        MockObject.objects.from_csv(
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            using='other'
        )
        self.assertEqual(MockObject.objects.count(), 0)
        self.assertEqual(MockObject.objects.using('other').count(), 3)
        self.assertEqual(MockObject.objects.using('other').get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.using('other').get(name='BEN').dt,
            date(2012, 1, 1)
        )
        MockObject.objects.using("other").all().delete()

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_to_csv(self, _):
        # First with the default database
        mapping = dict(name='NAME', number='NUMBER', dt='DATE')
        MockObject.objects.from_csv(self.name_path, mapping)
        export_path = os.path.join(os.path.dirname(__file__), 'default.csv')
        MockObject.objects.to_csv(export_path)
        self.assertTrue(os.path.exists(export_path))
        reader = csv.DictReader(open(export_path, 'r'))
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )
        os.remove(export_path)

    @mock.patch("django.db.connection.validate_no_atomic_block")
    def test_to_csv_from_alt_db(self, _):
        # Next with the other database
        mapping = dict(name='NAME', number='NUMBER', dt='DATE')
        MockObject.objects.from_csv(self.name_path, mapping, using="other")
        export_path = os.path.join(os.path.dirname(__file__), 'other.csv')
        MockObject.objects.using('other').to_csv(export_path)
        self.assertTrue(os.path.exists(export_path))
        reader = csv.DictReader(open(export_path, 'r'))
        self.assertTrue(
            ['BEN', 'JOE', 'JANE'],
            [i['name'] for i in reader]
        )
        MockObject.objects.using("other").all().delete()
        os.remove(export_path)
