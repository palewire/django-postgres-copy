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
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
    ]
}
html_theme_options = {
    "canonical_url": "https://palewi.re/docs/django-postgres-copy/",
    "github_user": "palewire",
    "github_repo": "django-postgres-copy",
    'show_powered_by': False,
}
html_short_title = 'a'

pygments_style = 'sphinx'
