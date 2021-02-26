.PHONY: ship test


ship:
	pipenv run python setup.py sdist bdist_wheel
	pipenv run twine upload dist/* --skip-existing


test:
	clear;
	flake8 postgres_copy;
	flake8 tests;
	coverage run setup.py test;
	coverage report -m;
