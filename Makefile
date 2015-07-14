.PHONY: test


test:
	clear;
	coverage run setup.py test;
	coverage report -m; 
