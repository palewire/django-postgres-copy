"""
Compatibility layer between psycopg2 and psycopg3 (psycopg) for COPY operations.

This module provides a unified interface for PostgreSQL COPY operations that works with
both psycopg2 and psycopg3 database drivers. It automatically detects which driver is
available and provides appropriate implementations of copy_to and copy_from functions.

The main differences between psycopg2 and psycopg3 COPY operations:
1. psycopg2 uses copy_expert method which takes an SQL string with parameters already inlined
2. psycopg3 uses a copy method that returns a context manager and accepts parameters separately
3. psycopg3 handles encoding differently, requiring explicit decoding for text destinations

This module abstracts away these differences, allowing code to work with either driver
without modification.
"""

from __future__ import annotations

import typing


# Define a protocol for cursor objects that have the methods we need
class CursorProtocol(typing.Protocol):
    """Protocol for database cursor objects."""

    def copy_expert(self, sql: str, file: typing.TextIO | typing.BinaryIO) -> None: ...
    def copy(
        self, sql: str, params: typing.Sequence[typing.Any] | None = None
    ) -> typing.Any: ...


# Define a protocol for file-like objects
class FilelikeProtocol(typing.Protocol):
    """Protocol for file-like objects."""

    def read(self, size: int = -1) -> str | bytes: ...
    def write(self, data: str | bytes) -> int: ...


try:
    # Try to import psycopg (version 3)
    import psycopg  # noqa: F401  just detect the presence of psycopg(3)
    from io import TextIOBase

    # Buffer size for reading data in chunks
    BUFFER_SIZE = 128 * 1024

    # Type alias for text or binary file-like objects
    FileObj = typing.Union[typing.TextIO, typing.BinaryIO]

    def copy_to(
        cursor: CursorProtocol,
        sql: str,
        params: typing.Sequence[typing.Any],
        destination: FileObj,
    ) -> None:
        """
        Copy data from the database to a file-like object using psycopg3.

        Args:
            cursor: A psycopg3 cursor object
            sql: SQL query string with placeholders
            params: Parameters for the SQL query
            destination: A file-like object to write the data to

        The function handles both text and binary destinations appropriately:
        - For text destinations (TextIOBase), it decodes the binary data from PostgreSQL
        - For binary destinations, it passes the data through unchanged
        """
        # psycopg3 returns binary data that needs to be decoded for text destinations
        is_text = isinstance(destination, TextIOBase)

        # Use the psycopg3 copy context manager
        with cursor.copy(sql, params) as copy:
            # Read data in chunks until there's no more
            while True:
                data = copy.read()
                if not data:
                    break

                # Decode the data if necessary and write to the destination
                if is_text:
                    # For text destinations, we need to decode to str
                    text_dest = typing.cast(typing.TextIO, destination)
                    text_dest.write(data.decode("utf-8"))
                else:
                    # For binary destinations, we keep as bytes
                    binary_dest = typing.cast(typing.BinaryIO, destination)
                    binary_dest.write(data)

    def copy_from(cursor: CursorProtocol, sql: str, source: FileObj) -> None:
        """
        Copy data from a file-like object to the database using psycopg3.

        Args:
            cursor: A psycopg3 cursor object
            sql: SQL COPY statement string
            source: A file-like object to read the data from

        The function reads data from the source in chunks and writes it to
        the database using the psycopg3 copy protocol.
        """
        # Use the psycopg3 copy context manager
        with cursor.copy(sql) as copy:
            # Read data in chunks and write to the database
            while True:
                data = source.read(BUFFER_SIZE)
                if not data:
                    break
                copy.write(data)

except ImportError:
    # Fall back to psycopg2 if psycopg3 is not available
    from psycopg2.extensions import adapt

    def copy_to(
        cursor: CursorProtocol,
        sql: str,
        params: typing.Sequence[typing.Any],
        destination: typing.TextIO | typing.BinaryIO,
    ) -> None:
        """
        Copy data from the database to a file-like object using psycopg2.

        Args:
            cursor: A psycopg2 cursor object
            sql: SQL query string with placeholders
            params: Parameters for the SQL query
            destination: A file-like object to write the data to

        The function adapts the parameters to SQL syntax and inlines them into the query,
        then uses psycopg2's copy_expert method to execute the COPY operation.
        """
        # psycopg2 requires parameters to be adapted and inlined into the SQL
        adapted_params = tuple(adapt(p) for p in params)
        inlined_sql = sql % adapted_params

        # Use psycopg2's copy_expert method
        cursor.copy_expert(inlined_sql, destination)

    def copy_from(
        cursor: CursorProtocol,
        sql: str,
        source: typing.TextIO | typing.BinaryIO,
    ) -> None:
        """
        Copy data from a file-like object to the database using psycopg2.

        Args:
            cursor: A psycopg2 cursor object
            sql: SQL COPY statement string
            source: A file-like object to read the data from

        The function uses psycopg2's copy_expert method to execute the COPY operation.
        """
        # Use psycopg2's copy_expert method
        cursor.copy_expert(sql, source)
