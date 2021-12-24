from datetime import datetime

extensions = []
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project = u'django-postgres-copy'
year = datetime.now().year
copyright = f'{year} Ben Welsh'

exclude_patterns = ["_build"]

html_theme = "alabaster"
html_sidebars = {
    '**': [
        # 'about.html',
        # 'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
    ]
}
html_theme_options = {
    "canonical_url": f"https://palewi.re/docs/{project}/",
    "github_user": "palewire",
    "github_repo": project,
    'show_powered_by': False,
}

pygments_style = 'sphinx'
