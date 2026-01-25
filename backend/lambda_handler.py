"""
AWS Lambda handler using Mangum WSGI adapter.

This file is the entry point for Lambda invocations.
Mangum translates API Gateway events to WSGI requests for Flask.
"""
from mangum import Mangum
from app import create_app

# Create Flask app
app = create_app()

# Create Lambda handler
# lifespan="off" disables ASGI lifespan events (not needed for Flask/WSGI)
handler = Mangum(app, lifespan="off")
