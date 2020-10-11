.PHONY: help venv vulnerability-scan lint test travis-test tox tox-recreate docs server-docs bumpversion-patch bumpversion-minor

.DEFAULT: help
help:
	@echo "make venv"
	@echo "    activates the virtual environment with pipenv (eg $ pipenv shell)"
	@echo " "
	@echo "make vulnerability-scan"
	@echo "    runs $ pipenv check to look for vulnerabilities in Python packages used"
	@echo " "
	@echo "make lint"
	@echo "    runs mypy"
	@echo " "
	@echo "make test"
	@echo "    runs the tests"
	@echo " "
	@echo "make test-travis"
	@echo "    runs the tests like they would run on Travis (where some tests are skipped)"
	@echo " "
	@echo "make tox"
	@echo "    runs tox - tests in all environments"
	@echo " "
	@echo "make tox-recreate"
	@echo "    makes tox to recreate all its virtual environments before running the tests."
	@echo "    This is required everytime when package dependencies change!"
	@echo " "
	@echo "make docs"
	@echo "    builds the html docs which becomes available under docs/_build/html"
	@echo " "
	@echo "make serve-docs"
	@echo "    serves the docs from docs/_build/html by making it available under http://127.0.0.1:8088/_build/html/"
	@echo " "
	@echo "make bumpversion-patch"
	@echo "    bump the patch version"
	@echo " "
	@echo "make bumpversion-minor"
	@echo "    bump the minor version"

venv:
	pipenv shell

vulnerability-scan:
	pipenv check . --verbose

lint:
	mypy falcon_limiter --ignore-missing-imports

test:
	pytest -x --cov-report term-missing

test-travis:
	TRAVIS='yes' pytest -x --cov-report term-missing

tox:
	tox

tox-recreate:
	tox --recreate

docs:
	cd docs && \
	make html

serve-docs:
	cd docs && \
	python -m http.server 8088

bumpversion-patch:
	bump2version patch
	cd docs && \
	make html

bumpversion-minor:
	bump2version minor
	cd docs && \
	make html