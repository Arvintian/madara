
build: clean
	python -m build -n --sdist

publish: build
	twine upload -r pypi dist/*

install: build
	pip uninstall -y madara
	pip install dist/madara*

clean:
	@rm -rf dist *.egg-info
