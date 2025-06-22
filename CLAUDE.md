# Django Postgres Copy

This document provides a comprehensive overview of the `django-postgres-copy` repository, explaining its purpose, architecture, and how to use it effectively.

## Repository Overview

`django-postgres-copy` is a Django package that provides a simple interface for using PostgreSQL's `COPY` command to efficiently import and export data between CSV files and Django models. The `COPY` command is significantly faster than using Django's ORM for bulk operations, especially for large datasets.

## Motivation

The creators of this library are data journalists who frequently download, clean, and analyze new data. This involves writing many data loaders. Traditionally, this was done by looping through each row and saving it to the database using Django's ORM `create` method:

```python
import csv
from myapp.models import MyModel

data = csv.DictReader(open("./data.csv"))
for row in data:
    MyModel.objects.create(name=row["NAME"], number=row["NUMBER"])
```

This approach works but is inefficient for large files because Django executes a database query for each row, which can take a long time to complete.

PostgreSQL's built-in `COPY` command can import and export data with a single query, making it much faster. This package makes using `COPY` as easy as any other database operation in Django.

## Installation

The package can be installed from the Python Package Index with `pip`:

```bash
pip install django-postgres-copy
```

You will need to have Django, PostgreSQL, and a database adapter (like `psycopg2` or `psycopg3`) already installed.

## Key Components

### 1. Core Functionality

The package provides two main operations:
- **Import from CSV**: Load data from CSV files into Django models
- **Export to CSV**: Export data from Django models to CSV files

### 2. Main Modules

- **`managers.py`**: Contains the `CopyManager` and `CopyQuerySet` classes that extend Django's standard manager and queryset with CSV import/export capabilities.
- **`copy_from.py`**: Handles importing data from CSV files to database tables using the `CopyMapping` class.
- **`copy_to.py`**: Handles exporting data from database tables to CSV files using custom SQL compilers.
- **`psycopg_compat.py`**: Provides compatibility between psycopg2 and psycopg3 database drivers for COPY operations.

### 3. Database Driver Compatibility

The package supports both psycopg2 and psycopg3 database drivers through a compatibility layer in `psycopg_compat.py`. This allows users to migrate to the newer driver at their own pace while maintaining the same API.

## Architecture

### CopyManager and CopyQuerySet

The `CopyManager` is a custom Django model manager that extends the standard manager with CSV import/export capabilities. It uses the `CopyQuerySet` class, which adds the `from_csv` and `to_csv` methods to Django's standard queryset.

```python
# Usage example
from postgres_copy import CopyManager


class MyModel(models.Model):
    name = models.CharField(max_length=100)
    objects = CopyManager()  # Use the custom manager
```

### CopyMapping

The `CopyMapping` class handles the process of mapping CSV columns to Django model fields and loading the data into the database. It uses a four-step process:

1. **Create**: Create a temporary table with the same structure as the CSV file
2. **Copy**: Copy data from the CSV file into the temporary table
3. **Insert**: Insert data from the temporary table into the Django model's table
4. **Drop**: Drop the temporary table

This approach allows for efficient data loading and validation before committing to the actual database table.

### Database Driver Compatibility

The `psycopg_compat.py` module provides a compatibility layer between psycopg2 and psycopg3 database drivers. It automatically detects which driver is available and provides appropriate implementations of `copy_to` and `copy_from` functions.

The main differences between the drivers that this module handles:
1. psycopg2 uses `copy_expert` method which takes an SQL string with parameters already inlined
2. psycopg3 uses a `copy` method that returns a context manager and accepts parameters separately
3. psycopg3 handles encoding differently, requiring explicit decoding for text destinations

## Usage Examples

### Importing Data from CSV

```python
# Basic import
MyModel.objects.from_csv(
    "path/to/file.csv",
    mapping={"name": "NAME_COLUMN", "number": "NUMBER_COLUMN", "date": "DATE_COLUMN"},
)

# With custom options
MyModel.objects.from_csv(
    "path/to/file.csv",
    mapping={"name": "NAME", "number": "NUMBER"},
    delimiter=";",
    null="NULL",
    encoding="utf-8",
)

# If CSV headers match model fields, mapping is optional
MyModel.objects.from_csv("path/to/file.csv")
```

#### Import Method Parameters

The `from_csv` method accepts the following parameters:

- `csv_path_or_obj`: The path to the CSV file or a Python file object
- `mapping`: (Optional) Dictionary mapping model fields to CSV headers
- `drop_constraints`: (Default: True) Whether to drop constraints during import
- `drop_indexes`: (Default: True) Whether to drop indexes during import
- `using`: Database to use for import
- `delimiter`: (Default: ',') Character separating values in the CSV
- `quote_character`: Character used for quoting
- `null`: String representing NULL values
- `force_not_null`: List of columns that should ignore NULL string matches
- `force_null`: List of columns that should convert empty quoted strings to NULL
- `encoding`: Character encoding of the CSV
- `ignore_conflicts`: (Default: False) Whether to ignore constraint violations
- `static_mapping`: Dictionary of static values to set for each row
- `temp_table_name`: Name for the temporary table used during import

### Exporting Data to CSV

```python
# Basic export
MyModel.objects.to_csv("path/to/output.csv")

# With filtering and custom options
MyModel.objects.filter(active=True).to_csv(
    "path/to/output.csv",
    "name",
    "number",  # Only export these fields
    delimiter=";",
    header=True,
    quote='"',
)

# Export to string (no file path provided)
csv_data = MyModel.objects.to_csv()

# Export with annotations
MyModel.objects.annotate(name_count=Count("name")).to_csv("path/to/output.csv")
```

#### Export Method Parameters

The `to_csv` method accepts the following parameters:

- `csv_path`: Path to output file or file-like object (optional - returns string if not provided)
- `*fields`: Field names to include in the export (all fields by default)
- `delimiter`: (Default: ',') Character to use as delimiter
- `header`: (Default: True) Whether to include header row
- `null`: String to use for NULL values
- `encoding`: Character encoding for the output file
- `escape`: Escape character to use
- `quote`: Quote character to use
- `force_quote`: Fields to force quote (field name, list of fields, True, or "*")

### Advanced Features

#### Static Mapping

You can provide static values for fields that don't exist in the CSV:

```python
MyModel.objects.from_csv(
    "path/to/file.csv",
    mapping={"name": "NAME", "number": "NUMBER"},
    static_mapping={"created_by": "import_script"},
)
```

#### Custom Field Processing

You can customize how fields are processed during import by defining a `copy_template` attribute on your model fields:

```python
class MyIntegerField(models.IntegerField):
    copy_template = """
        CASE
            WHEN "%(name)s" = 'x' THEN null
            ELSE "%(name)s"::int
        END
    """
```

Or by defining a method on your model:

```python
class MyModel(models.Model):
    name = models.CharField(max_length=100)

    def copy_name_template(self):
        return 'upper("%(name)s")'
```

A common use case is transforming date formats:

```python
def copy_mydatefield_template(self):
    return """
        CASE
            WHEN "%(name)s" = '' THEN NULL
            ELSE to_date("%(name)s", 'MM/DD/YYYY') /* The source CSV's date pattern */
        END
    """
```

It's important to handle empty strings by converting them to NULL in date fields to avoid "year out of range" errors.

#### Hooks

You can extend the `CopyMapping` class to add custom behavior at different stages of the import process:

```python
class CustomCopyMapping(CopyMapping):
    def pre_copy(self, cursor):
        # Run before copying data
        pass

    def post_copy(self, cursor):
        # Run after copying data
        pass

    def pre_insert(self, cursor):
        # Run before inserting data
        pass

    def post_insert(self, cursor):
        # Run after inserting data
        pass
```

### Working with Related Models

When exporting data, you can include fields from related models using Django's double underscore notation:

```python
# Models
class Hometown(models.Model):
    name = models.CharField(max_length=500)
    objects = CopyManager()


class Person(models.Model):
    name = models.CharField(max_length=500)
    number = models.IntegerField()
    hometown = models.ForeignKey(Hometown, on_delete=models.CASCADE)
    objects = CopyManager()


# Export with related fields
Person.objects.to_csv("path/to/export.csv", "name", "number", "hometown__name")
```

## Performance Considerations

- The package temporarily drops constraints and indexes during import to improve performance
- For large imports, it's recommended to run the import outside of a transaction block
- The package uses PostgreSQL's `COPY` command which is much faster than Django's ORM for bulk operations
- Importing data happens in a four-step process (create temp table, copy data, insert into model table, drop temp table)

## Testing

The package includes comprehensive tests for all functionality, including:
- Basic import/export operations
- Custom field processing
- Error handling
- Multi-database support
- psycopg2 and psycopg3 compatibility

## Limitations

- Only works with PostgreSQL databases
- Requires direct file access (for file-based imports)
- May not handle very complex data transformations without custom field processing

## Contributing

To set up a development environment:
1. Fork and clone the repository
2. Run `pipenv install` to install dependencies
3. Run `pipenv run pytest tests` to run tests

## License

The package is released under the MIT License.

## Resources

- Documentation: [palewi.re/docs/django-postgres-copy/](https://palewi.re/docs/django-postgres-copy/)
- Issues: [github.com/palewire/django-postgres-copy/issues](https://github.com/palewire/django-postgres-copy/issues)
- Packaging: [pypi.python.org/pypi/django-postgres-copy](https://pypi.python.org/pypi/django-postgres-copy)
- Testing: [github.com/palewire/django-postgres-copy/actions](https://github.com/palewire/django-postgres-copy/actions/workflows/test.yaml)
