.PHONY: ship test


ship:
	python setup.py sdist bdist_wheel
	twine upload dist/* --skip-existing


test:
	clear;
	flake8 postgres_copy;
	coverage run setup.py test;
	coverage report -m;
