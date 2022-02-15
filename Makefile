.PHONY: ship test docs


ship:
	pipenv run python setup.py sdist bdist_wheel
	pipenv run twine upload dist/* --skip-existing


test:
	pipenv run flake8 postgres_copy
	pipenv run flake8 tests
	pipenv run python setup.py test


docs:
	rm -rf docs/_build
	cd docs && pipenv run make livehtml