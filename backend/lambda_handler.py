"""
AWS Lambda handler using Mangum with ASGI adapter.

This file is the entry point for Lambda invocations.
Mangum requires ASGI, so we wrap Flask (WSGI) with asgiref.
"""
from mangum import Mangum
from asgiref.wsgi import WsgiToAsgi
from app import create_app

# Create Flask app
flask_app = create_app()

# Wrap Flask (WSGI) to ASGI
asgi_app = WsgiToAsgi(flask_app)

# Create Lambda handler
handler = Mangum(asgi_app, lifespan="off")
