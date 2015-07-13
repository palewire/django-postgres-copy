import os
from models import MockObject
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
                dict(NAME='name', NUMBER='number'),
                using='sqlite'
            )

    def test_simple_save(self):
        c = Copy(
            MockObject,
            self.name_path,
            dict(NAME='name', NUMBER='number')
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)

    def test_silent_save(self):
        c = Copy(
            MockObject,
            self.name_path,
            dict(NAME='name', NUMBER='number'),
        )
        c.save(silent=True)
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)

    def test_pipe_save(self):
        c = Copy(
            MockObject,
            self.pipe_path,
            dict(NAME='name', NUMBER='number'),
            delimiter="|",
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)

    def test_null_save(self):
        c = Copy(
            MockObject,
            self.null_path,
            dict(NAME='name', NUMBER='number'),
            null='',
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 4)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)
        self.assertEqual(MockObject.objects.get(name='nullboy').number, None)

    def test_backwards_save(self):
        c = Copy(
            MockObject,
            self.backwards_path,
            dict(NAME='name', NUMBER='number'),
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)
