import os
from models import MockObject
from postgres_copy import Copy
from django.test import TestCase


class PostgresCopyTest(TestCase):

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.name_path = os.path.join(self.data_dir, 'names.csv')
        self.pipe_path = os.path.join(self.data_dir, 'pipes.csv')

    def tearDown(self):
        MockObject.objects.all().delete()

    def test_bad_call(self):
        with self.assertRaises(TypeError):
            Copy()

    def test_simple_save(self):
        c = Copy(
            MockObject,
            self.name_path,
            dict(name='name', number='number')
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)

    def test_silent_save(self):
        c = Copy(
            MockObject,
            self.name_path,
            dict(name='name', number='number'),
        )
        c.save(silent=True)
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)

    def test_pipe_save(self):
        c = Copy(
            MockObject,
            self.pipe_path,
            dict(name='name', number='number'),
            delimiter="|",
        )
        c.save()
        self.assertEqual(MockObject.objects.count(), 3)
        self.assertEqual(MockObject.objects.get(name='ben').number, 1)
