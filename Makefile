.PHONY: test


test:
	clear;
	flake8 postgres_copy;
	coverage run setup.py test;
	coverage report -m;
