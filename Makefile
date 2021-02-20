
build:
	@rm -rf dist || true
	python setup.py egg_info --egg-base /tmp sdist

publish:
	@rm -rf dist || true
	python setup.py egg_info --egg-base /tmp sdist upload -r pypi

clean:
	@rm -rf dist
