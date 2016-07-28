import os
from datetime import date
from .models import MockObject, ExtendedMockObject, BasicMockObject
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
        self.mapping_path = os.path.join(self.data_dir, 'mappings.csv')
        self.fk_mapping_path = os.path.join(self.data_dir, 'fk_mappings.csv')

    def tearDown(self):
        MockObject.objects.all().delete()
        ExtendedMockObject.objects.all().delete()

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
            encoding='UTF-8',
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

    def test_field_value_mapping(self):
        c = CopyMapping(
            MockObject,
            self.mapping_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            field_value_mapping={
                'name': {
                    'ben': 'Master Ben',
                    'joe': 'Padawan Joe',
                    'jane': 'Jedi Jane'
                },
                'number': {
                    'seven': 7,
                    'three': 3,
                    'five': 5
                }
            }
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(
            list(MockObject.objects.order_by('name').values_list('name', 'number')),
            [('Jedi Jane', 5), ('Master Ben', 7), ('Padawan Joe', 3)]
        )
        self.assertEqual(
            MockObject.objects.get(name='Master Ben').dt,
            date(2012, 1, 1)
        )

    def test_field_value_mapping_and_types(self):
        c = CopyMapping(
            BasicMockObject,
            self.mapping_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            field_value_mapping={
                'name': {
                    'ben': 'Master Ben',
                    'joe': 'Padawan Joe',
                    'jane': 'Jedi Jane'
                },
                'number': {
                    'seven': 7,
                    'three': 3,
                    'five': 5
                }
            },
            field_copy_types={'number': 'text'}
        )
        c.save()
        self.assertEqual(BasicMockObject.objects.count(), 3)
        self.assertEqual(
            list(BasicMockObject.objects.order_by('name').values_list('name', 'number')),
            [('Jedi Jane', 5), ('Master Ben', 7), ('Padawan Joe', 3)]
        )
        self.assertEqual(
            BasicMockObject.objects.get(name='Master Ben').dt,
            date(2012, 1, 1)
        )

    def test_foreignkey_mapping(self):
        c = CopyMapping(
            BasicMockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE')
        )
        c.save()
        self.assertEqual(BasicMockObject.objects.count(), 3)

        c = CopyMapping(
            BasicMockObject,
            self.fk_mapping_path,
            dict(name='NAME', number='NUMBER', dt='DATE', parent='PARENT'),
            field_value_mapping={
                'parent': {
                    'ben': BasicMockObject.objects.get(name='ben').pk,
                    'joe': BasicMockObject.objects.get(name='joe').pk,
                    'jane': BasicMockObject.objects.get(name='jane').pk
                },
            },
            field_copy_types={'parent': 'text'}
        )
        c.save()
        self.assertEqual(BasicMockObject.objects.count(), 6)
        self.assertEqual(
            list(BasicMockObject.objects.order_by('name').
                 values_list('name', 'parent__name')),
            [('ben', None), ('ben junior', 'ben'), ('jane', None),
             ('jane junior', 'jane'), ('joe', None), ('joe junior', 'joe')]
        )

    def test_static_mapping_ignore_non_mapped_headers(self):
        c = CopyMapping(
            BasicMockObject,
            self.name_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
        )
        c.save()
        self.assertEqual(BasicMockObject.objects.count(), 3)

        c = CopyMapping(
            BasicMockObject,
            self.fk_mapping_path,
            dict(name='NAME', number='NUMBER', dt='DATE'),
            static_mapping={'parent': BasicMockObject.objects.get(name='ben').pk},
            ignore_non_mapped_headers=True
        )
        c.save()
        self.assertEqual(BasicMockObject.objects.count(), 6)
        self.assertEqual(
            list(BasicMockObject.objects.order_by('name').
                 values_list('name', 'parent__name')),
            [('ben', None), ('ben junior', 'ben'), ('jane', None),
             ('jane junior', 'ben'), ('joe', None), ('joe junior', 'ben')]
        )


class PostgresCopyFromFileObjectTest(PostgresCopyTest):
    def setUp(self):
        super(PostgresCopyFromFileObjectTest, self).setUp()
        self.name_path = open(self.name_path, 'r')
        self.foreign_path = open(self.foreign_path, 'r')
        self.pipe_path = open(self.pipe_path, 'r')
        self.null_path = open(self.null_path, 'r')
        self.backwards_path = open(self.backwards_path, 'r')
        self.mapping_path = open(self.mapping_path, 'r')
        self.fk_mapping_path = open(self.fk_mapping_path, 'r')

    def tearDown(self):
        self.name_path.close()
        self.foreign_path.close()
        self.pipe_path.close()
        self.null_path.close()
        self.backwards_path.close()
        self.mapping_path.close()
        self.fk_mapping_path.close()
