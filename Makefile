PYTHON ?= 3.13
.PHONY: dev check test build

dev:
	uv venv --python $(PYTHON)
	uv pip install --python .venv/bin/python -e '.[test]'

check: test
	.venv/bin/ruff check src tests scripts
	.venv/bin/ruff format --check src tests scripts

test:
	.venv/bin/python -m pytest tests -q --cov=owlrl_turbo --cov-branch --cov-fail-under=100

build:
	uv build
