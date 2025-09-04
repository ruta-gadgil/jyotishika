run:
	FLASK_ENV=development EPHE_PATH=./ephe python3 -m flask --app app run --port 8080

test:
	pytest -q

docker-build:
	docker build -t vedic-backend:latest .

docker-run:
	docker run -p 8080:8080 -e EPHE_PATH=/app/ephe vedic-backend:latest

format:
	black app/ tests/
	ruff check --fix app/ tests/

lint:
	ruff check app/ tests/
	black --check app/ tests/
