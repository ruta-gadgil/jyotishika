"""
Geocoding service using the Nominatim API from OpenStreetMap.

This module provides functions to search for cities by name and resolve
city names to latitude/longitude coordinates. It calls the Nominatim
search API and transforms the response into a simplified format.

Nominatim usage policy requires a User-Agent header identifying the application.
See: https://operations.osmfoundation.org/policies/nominatim/
"""

import requests
from typing import Optional

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Jyotishika/1.0 (astrology app)"
REQUEST_TIMEOUT = 10  # seconds


class GeocodingError(Exception):
    """Raised when geocoding fails due to upstream issues (network, timeout, etc.)."""
    pass


class NotFoundError(Exception):
    """Raised when no results are found for the given query."""
    pass


def search_cities(query: str, limit: int = 5) -> list[dict]:
    """
    Search for cities matching the given query string.
    
    Calls the Nominatim search API and returns up to `limit` results
    in a simplified format suitable for autocomplete dropdowns.
    
    Args:
        query: Partial or full city name to search for (min 3 characters)
        limit: Maximum number of results to return (default 5)
    
    Returns:
        List of dicts with keys: name, lat, lng
        Example: [{"name": "San Jose, California, United States", "lat": 37.336, "lng": -121.890}]
    
    Raises:
        ValueError: If query is less than 3 characters
        NotFoundError: If no results are found
        GeocodingError: If the upstream API request fails
    """
    if len(query) < 3:
        raise ValueError("Query must be at least 3 characters")
    
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 0,
    }
    
    headers = {
        "User-Agent": USER_AGENT,
    }
    
    try:
        response = requests.get(
            NOMINATIM_BASE_URL,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise GeocodingError("Request to geocoding service timed out")
    except requests.exceptions.RequestException as e:
        raise GeocodingError(f"Failed to reach geocoding service: {str(e)}")
    
    data = response.json()
    
    if not data:
        raise NotFoundError(f"No cities found for '{query}'")
    
    # Transform Nominatim response to simplified format
    results = []
    for item in data:
        results.append({
            "name": item.get("display_name", ""),
            "lat": float(item.get("lat", 0)),
            "lng": float(item.get("lon", 0)),
        })
    
    return results


def geocode_city(city: str) -> dict:
    """
    Resolve a city name to latitude/longitude coordinates.
    
    Calls the Nominatim search API with limit=1 to get the best match
    for the given city name string.
    
    Args:
        city: Full city name string (as returned by search_cities)
    
    Returns:
        Dict with keys: lat, lng
        Example: {"lat": 37.336, "lng": -121.890}
    
    Raises:
        ValueError: If city is less than 3 characters
        NotFoundError: If no results are found
        GeocodingError: If the upstream API request fails
    """
    # Reuse search_cities with limit=1 to avoid code duplication
    results = search_cities(city, limit=1)
    
    # search_cities already raises NotFoundError if empty, but be defensive
    if not results:
        raise NotFoundError(f"No results found for '{city}'")
    
    # Return only lat/lng (not the full name)
    return {
        "lat": results[0]["lat"],
        "lng": results[0]["lng"],
    }
