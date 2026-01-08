run:
	FLASK_ENV=development EPHE_PATH=./ephe ../venv/bin/python -m flask --app app run --host=0.0.0.0 --port=8000

test:
	../venv/bin/pytest -q

test-all:
	../venv/bin/pytest tests/ -v

docker-build:
	docker build -t vedic-backend:latest .

docker-run:
	docker run -p 8080:8080 -e EPHE_PATH=/app/ephe vedic-backend:latest

format:
	../venv/bin/black app/ tests/
	../venv/bin/ruff check --fix app/ tests/

lint:
	../venv/bin/ruff check app/ tests/
	../venv/bin/black --check app/ tests/
