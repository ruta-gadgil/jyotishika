"""
Geocoding API routes for city autocomplete and coordinate lookup.

Provides two endpoints:
- GET /cities?q=<query> - Search for cities by name (autocomplete)
- POST /geocode - Resolve a city name to lat/lng coordinates

These endpoints require authentication to prevent abuse and protect
against excessive calls to the upstream Nominatim API.

Rate limiting is handled at the API Gateway layer (see template.yaml),
which is the correct approach for Lambda — in-process rate limiting
does not work reliably across multiple Lambda instances.
"""

from flask import Blueprint, request, jsonify, current_app
from .schemas import GeocodeRequest
from .auth import get_current_user
from .geocoding_service import (
    search_cities,
    geocode_city,
    NotFoundError,
    GeocodingError,
)

geocoding_bp = Blueprint("geocoding", __name__)


@geocoding_bp.route("/cities", methods=["GET"])
def cities():
    """
    Search for cities matching a query string.
    
    Used for autocomplete as the user types a city name.
    Returns up to 5 matching cities with name and coordinates.
    
    SECURITY:
    - Requires authentication to prevent abuse
    - Rate limiting handled by API Gateway (see template.yaml)
    
    Query Parameters:
        q (str): Partial city name to search (minimum 3 characters)
    
    Returns:
        200: List of matching cities
        400: Query too short or missing
        401: Not authenticated
        404: No cities found
        502: Upstream geocoding service error
    """
    # Require authentication to prevent anonymous abuse
    session_data = get_current_user()
    if isinstance(session_data, tuple):
        return session_data
    
    query = request.args.get("q", "").strip()
    
    # Validate query parameter
    if not query or len(query) < 3:
        current_app.logger.warning(f"Invalid city search query: '{query}'")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Query parameter 'q' must be at least 3 characters"
            }
        }), 400
    
    current_app.logger.info(f"City search request: q='{query}'")
    
    try:
        results = search_cities(query, limit=5)
        current_app.logger.debug(f"Found {len(results)} cities for query '{query}'")
        return jsonify(results), 200
    
    except NotFoundError as e:
        current_app.logger.info(f"No cities found for query '{query}'")
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": str(e)
            }
        }), 404
    
    except GeocodingError as e:
        current_app.logger.error(f"Geocoding service error: {str(e)}")
        return jsonify({
            "error": {
                "code": "UPSTREAM_ERROR",
                "message": "Failed to reach geocoding service"
            }
        }), 502


@geocoding_bp.route("/geocode", methods=["POST"])
def geocode():
    """
    Resolve a city name to latitude/longitude coordinates.
    
    Called when user selects a city from the autocomplete dropdown.
    Takes the full city name string and returns coordinates.
    
    SECURITY:
    - Requires authentication to prevent abuse
    - Rate limiting handled by API Gateway (see template.yaml)
    
    Request Body:
        city (str): Full city name (3-200 characters)
    
    Returns:
        200: Coordinates {lat, lng}
        400: Invalid request body
        401: Not authenticated
        404: City not found
        502: Upstream geocoding service error
    """
    # Require authentication to prevent anonymous abuse
    session_data = get_current_user()
    if isinstance(session_data, tuple):
        return session_data
    
    # Validate request body using Pydantic schema
    try:
        payload = GeocodeRequest.model_validate_json(request.data)
    except Exception as e:
        current_app.logger.warning(f"Geocode request validation error: {str(e)}")
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    
    current_app.logger.info(f"Geocode request: city='{payload.city}'")
    
    try:
        result = geocode_city(payload.city)
        current_app.logger.debug(f"Geocoded '{payload.city}' to {result}")
        return jsonify(result), 200
    
    except NotFoundError:
        current_app.logger.info(f"No results found for city '{payload.city}'")
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"No results found for '{payload.city}'"
            }
        }), 404
    
    except GeocodingError as e:
        current_app.logger.error(f"Geocoding service error: {str(e)}")
        return jsonify({
            "error": {
                "code": "UPSTREAM_ERROR",
                "message": "Failed to reach geocoding service"
            }
        }), 502
