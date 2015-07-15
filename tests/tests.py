import os
from datetime import date
from .models import MockObject
from postgres_copy import Copy
from django.test import TestCase


class PostgresCopyTest(TestCase):

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.name_path = os.path.join(self.data_dir, 'names.csv')
        self.pipe_path = os.path.join(self.data_dir, 'pipes.csv')
        self.null_path = os.path.join(self.data_dir, 'nulls.csv')
        self.backwards_path = os.path.join(self.data_dir, 'backwards.csv')

    def tearDown(self):
        MockObject.objects.all().delete()

    def test_bad_call(self):
        with self.assertRaises(TypeError):
            Copy()

    def test_bad_backend(self):
        with self.assertRaises(TypeError):
            Copy(
                MockObject,
                self.name_path,
                dict(NAME='name', NUMBER='number', DATE='dt'),
                using='sqlite'
            )

    def test_simple_save(self):
        c = Copy(
            MockObject,
            self.name_path,
            dict(NAME='name', NUMBER='number', DATE='dt')
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_silent_save(self):
        c = Copy(
            MockObject,
            self.name_path,
            dict(NAME='name', NUMBER='number', DATE='dt'),
        )
        c.save(silent=True)
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_pipe_save(self):
        c = Copy(
            MockObject,
            self.pipe_path,
            dict(NAME='name', NUMBER='number', DATE='dt'),
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
        c = Copy(
            MockObject,
            self.null_path,
            dict(NAME='name', NUMBER='number', DATE='dt'),
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
        c = Copy(
            MockObject,
            self.backwards_path,
            dict(NAME='name', NUMBER='number', DATE='dt'),
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='BEN').number, 1)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_field_override_save(self):
        c = Copy(
            MockObject,
            self.null_path,
            dict(NAME='name', NUMBER='number', DATE='dt'),
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BADBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )

    def test_encoding_save(self):
        c = Copy(
            MockObject,
            self.null_path,
            dict(NAME='name', NUMBER='number', DATE='dt'),
            encoding='UTF-8'
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 5)
        self.assertEqual(MockObject.objects.get(name='BADBOY').number, None)
        self.assertEqual(
            MockObject.objects.get(name='BEN').dt,
            date(2012, 1, 1)
        )
