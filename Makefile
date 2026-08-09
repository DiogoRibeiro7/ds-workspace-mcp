.PHONY: install lint format format-check type test test-unit test-integration quality build clean

install:
	poetry install

lint:
	poetry run ruff check .

format:
	poetry run ruff format src tests examples

format-check:
	poetry run ruff format --check src tests examples

type:
	poetry run mypy

test:
	poetry run pytest

test-unit:
	poetry run pytest -m "not integration"

test-integration:
	poetry run pytest -m integration tests/integration tests/test_examples.py -vv

quality: lint format-check type test-unit

build:
	poetry build

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache .tox .nox build dist htmlcov site
