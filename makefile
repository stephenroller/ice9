all: tm
	chmod +x ice9

clean:
	rm -f .coverage && rm -f *.pyc && rm -rf htmlcoverage
	rm -f tm

tests: tm
	python tests.py

coverage: tm
	coverage run tests.py || true
	coverage report -m && coverage html -d htmlcoverage && open htmlcoverage/index.html
