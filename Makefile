.PHONY: up down test eval demo lint
up:
	docker compose up --build
down:
	docker compose down
test:
	cd backend && python -m pytest ../tests
eval:
	python eval/run_eval.py
demo:
	python scripts/seed_demo.py
lint:
	cd backend && ruff check app
