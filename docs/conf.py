from datetime import datetime

extensions = []
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project = 'django-postgres-copy'
year = datetime.now().year
copyright = f'{year} Ben Welsh'

exclude_patterns = ["_build"]

html_theme = "alabaster"
html_theme_options = {
    "description": "Quickly import and export delimited data with Django support for PostgreSQL’s COPY command",
    "github_user": "palewire",
    "github_repo": "django-postgres-copy",
    'show_powered_by': False,
}

pygments_style = 'sphinx'
