all:
	chmod +x ice9

clean:
	rm -f .coverage && rm -f *.pyc && rm -rf htmlcoverage

test:
	python tests.py

coverage: 
	coverage run tests.py || true
	coverage report -m && coverage html -d htmlcoverage && open htmlcoverage/index.html
