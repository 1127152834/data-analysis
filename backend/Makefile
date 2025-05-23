.PHONY: test

makemigrations:
	@echo "Creating migrations..."
	@if [ -z "$(NAME)" ]; then \
		uv run alembic revision --autogenerate; \
	else \
		uv run alembic revision --autogenerate -m "$(NAME)"; \
	fi

migrate:
	@echo "Migrating database..."
	@uv run alembic upgrade head

reset_migrations:
	@echo "Resetting migrations..."
	@uv run python -c "from app.core.db import engine; from sqlalchemy import text; with engine.begin() as conn: conn.execute(text('DROP TABLE IF EXISTS alembic_version')); print('Migration history reset!')"
	@echo "Creating initial schema migration..."
	@rm -rf app/alembic/versions/*
	@uv run alembic revision --autogenerate -m "initial_schema"

lint:
	@echo "Linting code..."
	@uv run ruff check .

format:
	@echo "Formatting code..."
	@uv run ruff format .

test:
	@echo "Running tests..."
	@uv run pytest -v tests/

dev_backend:
	@echo "Running backend server in development mode..."
	@uv run fastapi dev app/api_server.py --host 127.0.0.1 --port 5001

run_backend:
	@echo "Running backend server..."
	@uv run fastapi run app/api_server.py --host 0.0.0.0 --port 5001 --workers 4

dev_celery_flower:
	@echo "Running Celery Flower..."
	@uv run celery -A app.celery flower --address=0.0.0.0 --port=5555

dev_background_worker:
	@echo "Running background worker..."
	@uv run celery -A app.celery worker -Q default -l INFO -E

dev_eval_worker:
	@echo "Running evaluation worker..."
	@uv run celery -A app.celery worker -Q evaluation --loglevel=debug --pool=solo
