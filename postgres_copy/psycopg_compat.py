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

try:
    # Try to import psycopg (version 3)
    import psycopg  # noqa: F401  just detect the presence of psycopg(3)
    from codecs import getincrementaldecoder
    from io import TextIOBase

    # Buffer size for reading data in chunks
    BUFFER_SIZE = 128 * 1024

    class NoopDecoder:
        """
        A no-op decoder that simply returns the input unchanged.

        This is used for binary destinations where no decoding is needed.
        """

        def decode(self, input, final=False):
            """Return the input unchanged."""
            return input

    # Get the UTF-8 incremental decoder class for text destinations
    utf8_decoder_cls = getincrementaldecoder("utf8")

    def copy_to(cursor, sql, params, destination):
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
        if isinstance(destination, TextIOBase):
            # For text destinations, use UTF-8 decoder
            decoder = utf8_decoder_cls()
        else:
            # For binary destinations, use no-op decoder
            decoder = NoopDecoder()

        # Use the psycopg3 copy context manager
        with cursor.copy(sql, params) as copy:
            # Read data in chunks until there's no more
            while data := copy.read():
                # Decode the data if necessary
                data = decoder.decode(data)
                # Write to the destination
                destination.write(data)

            # Finalize the decoder to handle any buffered data
            if data := decoder.decode(b"", final=True):
                destination.write(data)

    def copy_from(cursor, sql, source):
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
            while data := source.read(BUFFER_SIZE):
                copy.write(data)

except ImportError:
    # Fall back to psycopg2 if psycopg3 is not available
    from psycopg2.extensions import adapt

    def copy_to(cursor, sql, params, destination):
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

    def copy_from(cursor, sql, source):
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
