.PHONY: compose-up compose-down dev test lint

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

dev:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	uv run pytest

lint:
	uv run ruff check .
