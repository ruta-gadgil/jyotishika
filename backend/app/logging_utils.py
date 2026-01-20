"""
Logging Utilities

Centralized logging helpers with built-in sensitive data filtering.
Ensures consistent, secure logging across the application.
"""

import json
from typing import Any, Dict, Optional
from flask import Request


# List of sensitive keys that should never be logged
SENSITIVE_KEYS = {
    "password", "secret", "token", "api_key", "apikey", "auth", 
    "authorization", "cookie", "session", "csrf", "client_secret",
    "access_token", "refresh_token", "id_token", "bearer"
}

# PII keys that should be redacted or masked
PII_KEYS = {
    "email", "phone", "ssn", "address", "name", "first_name", 
    "last_name", "full_name", "birth_date", "birthdate"
}


def sanitize_dict(data: Dict[str, Any], redact_pii: bool = True) -> Dict[str, Any]:
    """
    Sanitize a dictionary by removing/redacting sensitive fields.
    
    Args:
        data: Dictionary to sanitize
        redact_pii: Whether to redact PII fields (default: True)
        
    Returns:
        Sanitized dictionary safe for logging
        
    Example:
        >>> sanitize_dict({"email": "user@test.com", "name": "John", "age": 30})
        {"email": "[REDACTED]", "name": "[REDACTED]", "age": 30}
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Skip sensitive keys entirely
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            continue
        
        # Redact PII if enabled
        if redact_pii and any(pii in key_lower for pii in PII_KEYS):
            if key_lower == "email" and isinstance(value, str) and "@" in value:
                # For email, show only domain
                sanitized[key] = f"***@{value.split('@')[1]}"
            else:
                sanitized[key] = "[REDACTED]"
            continue
        
        # Recursively sanitize nested dicts
        if isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, redact_pii)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, redact_pii) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


def sanitize_request_data(request: Request, max_length: int = 500) -> str:
    """
    Safely extract and sanitize request data for logging.
    
    Args:
        request: Flask request object
        max_length: Maximum length of returned string (default: 500)
        
    Returns:
        Sanitized request data as string, truncated if needed
    """
    try:
        # Try to parse as JSON
        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                sanitized = sanitize_dict(data)
                result = json.dumps(sanitized, separators=(',', ':'))
            else:
                result = "No JSON data"
        else:
            # For non-JSON, just log content type and length
            result = f"Content-Type: {request.content_type or 'none'}, Length: {request.content_length or 0}"
    except Exception:
        result = "Unable to parse request data"
    
    # Truncate if too long
    if len(result) > max_length:
        result = result[:max_length] + "..."
    
    return result


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Sanitize HTTP headers by removing sensitive ones.
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Sanitized headers safe for logging
    """
    # Headers to include in logs (safe ones)
    safe_headers = {
        "content-type", "content-length", "accept", 
        "user-agent", "referer", "origin"
    }
    
    sanitized = {}
    for key, value in headers.items():
        key_lower = key.lower()
        
        # Skip sensitive headers
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            continue
        
        # Only include safe headers
        if key_lower in safe_headers:
            # Truncate user-agent if too long
            if key_lower == "user-agent" and len(value) > 100:
                sanitized[key] = value[:100] + "..."
            else:
                sanitized[key] = value
    
    return sanitized


def mask_email(email: str) -> str:
    """
    Mask email address, showing only domain.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email showing only domain
        
    Example:
        >>> mask_email("user@example.com")
        "***@example.com"
    """
    if not email or "@" not in email:
        return "***@unknown"
    
    parts = email.split("@")
    return f"***@{parts[1]}"


def truncate_id(id_str: str, length: int = 8) -> str:
    """
    Truncate an ID or token to a safe length for logging.
    
    Args:
        id_str: ID or token to truncate
        length: Number of characters to keep (default: 8)
        
    Returns:
        Truncated ID with ellipsis
        
    Example:
        >>> truncate_id("abc123def456ghi789")
        "abc123de..."
    """
    if not id_str:
        return ""
    
    if len(id_str) <= length:
        return id_str
    
    return f"{id_str[:length]}..."


def safe_str(value: Any, max_length: int = 200) -> str:
    """
    Convert any value to a safe string for logging.
    
    Args:
        value: Value to convert
        max_length: Maximum length (default: 200)
        
    Returns:
        Safe string representation, truncated if needed
    """
    try:
        if isinstance(value, dict):
            sanitized = sanitize_dict(value)
            result = json.dumps(sanitized, separators=(',', ':'))
        elif isinstance(value, (list, tuple)):
            result = str(value)
        else:
            result = str(value)
    except Exception:
        result = "[Unable to serialize]"
    
    if len(result) > max_length:
        result = result[:max_length] + "..."
    
    return result
