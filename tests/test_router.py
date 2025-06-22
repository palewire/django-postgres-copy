class CustomRouter:
    def db_for_read(self, model, **hints):
        if model.__name__ == "SecondaryMockObject":
            return "secondary"
        return None

    def db_for_write(self, model, **hints):
        if model.__name__ == "SecondaryMockObject":
            return "secondary"
        return None
