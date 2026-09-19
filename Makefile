.PHONY: help install lint format test test-cov run-api run-worker up down migrate demo clean

help:
	@echo "Available commands:"
	@echo "  make install     Install all dependencies"
	@echo "  make lint        Run ruff and black code checks"
	@echo "  make format      Auto-format code with black and ruff"
	@echo "  make test        Run pytest suite"
	@echo "  make test-cov    Run pytest with coverage report"
	@echo "  make run-api     Run FastAPI development server"
	@echo "  make run-worker  Run ARQ background worker"
	@echo "  make up          Start full stack via docker compose"
	@echo "  make down        Stop docker compose stack"
	@echo "  make migrate     Apply database migrations"
	@echo "  make demo        Run end-to-end automated demonstration"
	@echo "  make clean       Remove temporary files and caches"

install:
	pip install -e ".[dev]"

lint:
	ruff check app tests scripts
	black --check app tests scripts

format:
	ruff check --fix app tests scripts
	black app tests scripts

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

run-api:
	uvicorn app.api.main:app --reload --port 8000

run-worker:
	python -m arq app.workers.worker.WorkerSettings

up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	alembic upgrade head

demo:
	python scripts/generate_samples.py
	python scripts/run_demo.py

clean:
	rm -rf .pytest_cache htmlcov .coverage .ruff_cache .mypy_cache build dist *.egg-info
