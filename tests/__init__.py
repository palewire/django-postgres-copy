import os
from models import MockObject
from postgres_copy import Copy
from django.test import TestCase


class PostgresCopyTest(TestCase):

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.name_path = os.path.join(self.data_dir, 'names.csv')

    def test_copy(self):
        with self.assertRaises(TypeError):
            Copy()
        c = Copy(
            MockObject,
            self.name_path,
            dict(name='name', number='number')
        )
        c.save()
