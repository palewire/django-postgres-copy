try:
    import psycopg  # noqa: F401  just detect the presence of psycopg(3)
    from codecs import getincrementaldecoder
    from io import TextIOBase

    BUFFER_SIZE = 128 * 1024

    class NoopDecoder:
        def decode(self, input, final=False):
            return input

    utf8_decoder_cls = getincrementaldecoder("utf8")

    def copy_to(cursor, sql, params, destination):
        # psycopg2.copy_expert has special handling of encoding
        if isinstance(destination, TextIOBase):
            decoder = utf8_decoder_cls()
        else:
            decoder = NoopDecoder()
        with cursor.copy(sql, params) as copy:
            while data := copy.read():
                data = decoder.decode(data)
                destination.write(data)
            # TODO: is this extra one needed?
            if data := decoder.decode(b"", final=True):
                destination.write(data)

    def copy_from(cursor, sql, source):
        with cursor.copy(sql) as copy:
            while data := source.read(BUFFER_SIZE):
                copy.write(data)

except ImportError:
    from psycopg2.extensions import adapt

    def copy_to(cursor, sql, params, destination):
        # adapt SELECT query parameters to SQL syntax
        adapted_params = tuple(adapt(p) for p in params)
        inlined_sql = sql % adapted_params
        cursor.copy_expert(inlined_sql, destination)

    def copy_from(cursor, sql, source):
        cursor.copy_expert(sql, source)
