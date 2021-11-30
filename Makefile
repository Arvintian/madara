
build:
	@rm -rf dist || true
	python setup.py egg_info --egg-base /tmp sdist

publish:
	@rm -rf dist || true
	python setup.py egg_info --egg-base /tmp sdist upload -r pypi

install: build
	pip uninstall -y madara
	pip install dist/madara*

clean:
	@rm -rf dist
