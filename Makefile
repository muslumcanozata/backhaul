.PHONY: api test web

api:
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000

test:
	cd apps/api && .venv/bin/pytest

web:
	cd apps/web && npm run dev
