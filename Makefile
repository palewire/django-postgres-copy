.PHONY: test


test:
	coverage run setup.py test;
	coverage report -m 
