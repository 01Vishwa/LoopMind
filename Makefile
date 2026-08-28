.PHONY: install lint test test-unit test-db db-migrate db-new db-reset sandbox-build fmt env-check api-dev loop

install:
	uv sync --all-packages

fmt:
	uv run ruff format packages/ apps/

lint:
	uv run ruff check packages/ apps/
	uv run ruff format --check packages/ apps/
	uv run mypy packages/core/src packages/testing/src packages/db/src packages/llm/src apps/cli/src
	uv run lint-imports

env-check:
	@test -f .env || (echo "Missing .env — copy .env.example to .env and fill in real values." && exit 1)

test:
	uv run pytest packages/ apps/ -x --tb=short -q

test-unit:
	uv run pytest packages/ apps/ -x --tb=short -q -m "not integration and not e2e"

test-db:
	uv run pytest packages/ apps/ -x --tb=short -q -m integration

db-migrate:
	supabase db push

db-new:
	supabase migration new $(MSG)

db-reset:
	supabase db reset

sandbox-build:
	docker build -t vera-sandbox:latest packages/sandbox/src/vera_sandbox/image/

api-dev:
	uv run uvicorn vera_api.main:app --reload --port 8000 --app-dir apps/api/src

loop:
	uv run vera run --workspace ./fixtures/payments \
	  --query "What share of Q3 chargebacks came from merchants with manual capture delay?" \
	  --fake-llm --scenario backtrack
