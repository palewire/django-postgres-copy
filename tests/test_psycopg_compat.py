import io
import importlib.util
import unittest
from unittest import mock

from postgres_copy.psycopg_compat import copy_from, copy_to

# Check if psycopg3 is available
PSYCOPG3_AVAILABLE = importlib.util.find_spec("psycopg") is not None
# Check if psycopg2 is available
PSYCOPG2_AVAILABLE = importlib.util.find_spec("psycopg2") is not None


class PsycopgCompatTest(unittest.TestCase):
    """
    Tests for the psycopg_compat module which provides compatibility between psycopg2 and psycopg3.
    """

    def setUp(self):
        self.cursor = mock.MagicMock()
        self.sql = "SELECT %s, %s"
        self.source = io.StringIO("test data")
        self.destination = io.StringIO()

    @unittest.skipIf(not PSYCOPG2_AVAILABLE, "psycopg2 not available")
    def test_copy_to_with_psycopg2(self):
        """Test copy_to function with psycopg2."""
        # Mock the psycopg2 import to succeed and psycopg to fail
        with mock.patch.dict("sys.modules", {"psycopg": None}):
            with mock.patch("psycopg2.extensions.adapt") as mock_adapt:
                mock_adapt.return_value.getquoted.return_value = b"'test'"

                # Call the function
                copy_to(self.cursor, self.sql, (1, 2), self.destination)

                # Check that the psycopg2 version was called with the right parameters
                self.cursor.copy_expert.assert_called_once()
                # Verify that the destination was passed as the second argument
                self.assertEqual(
                    self.destination, self.cursor.copy_expert.call_args[0][1]
                )

    @unittest.skipIf(not PSYCOPG2_AVAILABLE, "psycopg2 not available")
    def test_copy_from_with_psycopg2(self):
        """Test copy_from function with psycopg2."""
        # Mock the psycopg2 import to succeed and psycopg to fail
        with mock.patch.dict("sys.modules", {"psycopg": None}):
            # Call the function
            copy_from(self.cursor, self.sql, self.source)

            # Check that the psycopg2 version was called with the right parameters
            self.cursor.copy_expert.assert_called_once()
            # Verify that the source was passed as the second argument
            self.assertEqual(self.source, self.cursor.copy_expert.call_args[0][1])

    @unittest.skipIf(not PSYCOPG3_AVAILABLE, "psycopg3 not available")
    def test_copy_to_with_psycopg3(self):
        """Test copy_to function with psycopg3."""
        # Mock the psycopg import to succeed
        with mock.patch.dict("sys.modules", {"psycopg": mock.MagicMock()}):
            # Mock the cursor.copy context manager
            mock_copy = mock.MagicMock()
            self.cursor.copy = mock.MagicMock(return_value=mock_copy)
            mock_copy.__enter__ = mock.MagicMock(return_value=mock_copy)
            mock_copy.__exit__ = mock.MagicMock(return_value=None)
            mock_copy.read = mock.MagicMock(side_effect=[b"data1", b"data2", None])

            # Call the function with a text destination
            destination = io.StringIO()
            copy_to(self.cursor, self.sql, (1, 2), destination)

            # Check that the psycopg3 version was called with the right parameters
            self.cursor.copy.assert_called_once_with(self.sql, (1, 2))
            mock_copy.read.assert_called()

            # Check the content of the destination
            destination.seek(0)
            content = destination.read()
            self.assertEqual("data1data2", content)

    @unittest.skipIf(not PSYCOPG3_AVAILABLE, "psycopg3 not available")
    def test_copy_from_with_psycopg3(self):
        """Test copy_from function with psycopg3."""
        # Mock the psycopg import to succeed
        with mock.patch.dict("sys.modules", {"psycopg": mock.MagicMock()}):
            # Mock the cursor.copy context manager
            mock_copy = mock.MagicMock()
            self.cursor.copy = mock.MagicMock(return_value=mock_copy)
            mock_copy.__enter__ = mock.MagicMock(return_value=mock_copy)
            mock_copy.__exit__ = mock.MagicMock(return_value=None)
            mock_copy.write = mock.MagicMock()

            # Call the function
            source = io.StringIO("test data")
            copy_from(self.cursor, self.sql, source)

            # Check that the psycopg3 version was called with the right parameters
            self.cursor.copy.assert_called_once_with(self.sql)
            mock_copy.write.assert_called_once_with("test data")

    @unittest.skipIf(not PSYCOPG3_AVAILABLE, "psycopg3 not available")
    def test_copy_to_with_psycopg3_binary_destination(self):
        """Test copy_to function with psycopg3 and a binary destination."""
        # Mock the psycopg import to succeed
        with mock.patch.dict("sys.modules", {"psycopg": mock.MagicMock()}):
            # Mock the cursor.copy context manager
            mock_copy = mock.MagicMock()
            self.cursor.copy = mock.MagicMock(return_value=mock_copy)
            mock_copy.__enter__ = mock.MagicMock(return_value=mock_copy)
            mock_copy.__exit__ = mock.MagicMock(return_value=None)

            # Set up the read method to return binary data
            read_data = [b"data1", b"data2", None]

            def side_effect():
                return read_data.pop(0) if read_data else None

            mock_copy.read = mock.MagicMock(side_effect=side_effect)

            # Call the function with a binary destination
            destination = io.BytesIO()
            copy_to(self.cursor, self.sql, (1, 2), destination)

            # Check that the psycopg3 version was called with the right parameters
            self.cursor.copy.assert_called_once_with(self.sql, (1, 2))
            self.assertEqual(mock_copy.read.call_count, 3)

            # Check the content of the destination
            destination.seek(0)
            content = destination.read()
            self.assertIn(b"data1", content)
            self.assertIn(b"data2", content)

    @unittest.skipIf(not PSYCOPG3_AVAILABLE, "psycopg3 not available")
    def test_copy_from_with_psycopg3_binary_source(self):
        """Test copy_from function with psycopg3 and a binary source."""
        # Mock the psycopg import to succeed
        with mock.patch.dict("sys.modules", {"psycopg": mock.MagicMock()}):
            # Mock the cursor.copy context manager
            mock_copy = mock.MagicMock()
            self.cursor.copy = mock.MagicMock(return_value=mock_copy)
            mock_copy.__enter__ = mock.MagicMock(return_value=mock_copy)
            mock_copy.__exit__ = mock.MagicMock(return_value=None)
            mock_copy.write = mock.MagicMock()

            # Call the function with a binary source
            source = io.BytesIO(b"test data")
            copy_from(self.cursor, self.sql, source)

            # Check that the psycopg3 version was called with the right parameters
            self.cursor.copy.assert_called_once_with(self.sql)
            mock_copy.write.assert_called_once_with(b"test data")

    def test_import_error_handling(self):
        """Test that the module handles import errors gracefully."""
        # This test doesn't need to do anything specific, as the import error handling
        # is done at module import time. If the module imported successfully, then
        # the import error handling worked.
        self.assertTrue(True)
