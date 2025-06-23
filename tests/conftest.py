import os
import sys
import pytest
from django.db import connections

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Fixture to set up the test database with the required tables.
    This extends the built-in django_db_setup fixture.
    """
    # Import all test models
    from tests.test_models import (
        MockObject,
        MockFKObject,
        MockBlankObject,
        ExtendedMockObject,
        LimitedMockObject,
        OverloadMockObject,
        SecondaryMockObject,
        UniqueMockObject,
    )

    with django_db_blocker.unblock():
        # Check if tables exist and create them if they don't
        for alias in connections:
            connection = connections[alias]

            # Get a list of all tables in the database
            with connection.cursor() as cursor:
                if connection.vendor == "postgresql":
                    cursor.execute(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                    )
                    existing_tables = {row[0] for row in cursor.fetchall()}
                elif connection.vendor == "sqlite":
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    existing_tables = {row[0] for row in cursor.fetchall()}
                else:
                    existing_tables = set()

                # Create tables that don't exist
                with connection.schema_editor() as schema_editor:
                    for model in [
                        MockObject,
                        MockFKObject,
                        MockBlankObject,
                        ExtendedMockObject,
                        LimitedMockObject,
                        OverloadMockObject,
                        SecondaryMockObject,
                        UniqueMockObject,
                    ]:
                        table_name = model._meta.db_table
                        if table_name not in existing_tables:
                            try:
                                schema_editor.create_model(model)
                                print(f"Created table {table_name} in {alias}")
                            except Exception as e:
                                print(f"Error creating {table_name} in {alias}: {e}")
