# Check if dependencies are installed, install if missing
.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	@../venv/bin/pip install -q -r requirements.txt || (echo "Failed to install dependencies" && exit 1)
	@echo "Dependencies OK"

# Run the Flask application
# Automatically loads environment from local.env (handled by app/__init__.py)
# DATABASE_URL must be set in local.env for authorization to work
run: check-deps
	@echo "Starting Flask application..."
	@echo "Note: Ensure DATABASE_URL is set in local.env for authorization"
	@FLASK_ENV=development EPHE_PATH=./ephe ../venv/bin/python -m flask --app app run --host=0.0.0.0 --port=8000

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
