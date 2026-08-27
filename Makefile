PHONY: install lint test test-unit test-db migrate migrate-new sandbox-build fmt env-check

install:
	uv sync --all-packages

fmt:
	uv run ruff format packages/ apps/

lint:
	uv run ruff check packages/ apps/
	uv run ruff format --check packages/ apps/
	uv run mypy packages/core/src packages/testing/src
	uv run lint-imports

env-check:
	@test -f .env || (echo "Missing .env — copy .env.example to .env and fill in real values." && exit 1)

test:
	uv run pytest packages/ apps/ -x --tb=short -q

test-unit:
	uv run pytest packages/ apps/ -x --tb=short -q -m "not integration and not e2e"

test-db:
	uv run pytest packages/ apps/ -x --tb=short -q -m integration

migrate:
	uv run alembic -c apps/api/alembic.ini upgrade head

migrate-new:
	uv run alembic -c apps/api/alembic.ini revision --autogenerate -m "$(MSG)"

sandbox-build:
	docker build -t vera-sandbox:latest packages/sandbox/src/vera_sandbox/image/

api-dev:
	uv run uvicorn vera_api.main:app --reload --port 8000 --app-dir apps/api/src
