SHELL := /bin/bash
.PHONY: help tests coverage tox


help:
	echo -e\
	"targets:\n" \
	"	coverage - run unit test and report coverage\n" \
	"	tests - discover and run orc tests\n" \
	"	tox   - run tests against different version of python\n"


tests:
	find tests -iname '*.py' | sed 's/^\.\///' | context=$(context) xargs python3 -m unittest
	pycodestyle --ignore=E265 hrsync


coverage:
	find tests -iname '*.py' | sed 's/^\.\///' | context=$(context) xargs coverage run -m unittest
	coverage report
	coverage html
	@echo "file://$(shell pwd)/htmlcov/index.html"
	pycodestyle hrsync


tox:
	docker run -it --rm -v "$(shell pwd):/app" painless/tox
