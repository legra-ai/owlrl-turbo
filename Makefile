PYTHON ?= 3.13

.PHONY: dev check test build

dev:
	uv sync --locked --extra test --python $(PYTHON)

check: test
	uv run --locked --extra test ruff check src tests scripts
	uv run --locked --extra test ruff format --check src tests scripts

test:
	uv run --locked --extra test pytest tests -q --cov=owlrl_turbo --cov-branch --cov-fail-under=100

build:
	uv build

.PHONY: benchmark-companions
.PHONY: test-rust-coverage
test-rust-coverage:
	$(MAKE) -C ../rdflib-turbo test-rust-coverage

benchmark-companions:
	$(MAKE) -C ../pyshacl-turbo benchmark-companions
