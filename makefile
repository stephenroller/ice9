all:
	chmod +x ice9

clean:
	rm -f .coverage && rm -f *.pyc && rm -rf htmlcoverage

test:
	coverage run tests.py  && coverage report -m && coverage html -d htmlcoverage && open htmlcoverage/index.html
