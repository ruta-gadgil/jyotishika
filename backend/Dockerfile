FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app
# Copy ephemeris files into /app/ephe (mount or bake-in)
COPY ephe ./ephe

ENV EPHE_PATH=/app/ephe
ENV PORT=8080

EXPOSE 8080
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:create_app()"]
