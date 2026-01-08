"""
Google OAuth 2.0 Authentication Blueprint

This module implements Google OAuth 2.0 authentication with HTTP-only cookies
for local development. It includes login, callback, user info, and logout endpoints.
"""

import os
import secrets
import uuid
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify, redirect, make_response, current_app
from jose import jwt, JWTError
from jose.utils import base64url_decode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import requests

# Create auth blueprint
auth_bp = Blueprint("auth", __name__)

# In-memory session storage
# Key: session_id (UUID string), Value: dict with user info
# PRODUCTION: Replace with Redis, database, or distributed cache (e.g., Redis, Memcached)
# This in-memory storage won't work with multiple server instances or after restarts
sessions = {}

# In-memory state token storage for CSRF protection
# Key: state token (string), Value: timestamp (datetime)
# PRODUCTION: Replace with Redis or database-backed storage
# State tokens should be shared across all server instances for load-balanced deployments
state_tokens = {}

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
# PRODUCTION: APP_BASE_URL must use HTTPS (e.g., "https://api.yourdomain.com")
# Google OAuth requires HTTPS for production redirect URIs
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")
# PRODUCTION: FRONTEND_BASE_URL should be your production frontend domain
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# OAuth scopes
SCOPES = "openid email profile"

# Redirect URI for Google OAuth callback
REDIRECT_URI = f"{APP_BASE_URL}/auth/google/callback"


def generate_state_token():
    """Generate a random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def validate_state_token(state: str) -> bool:
    """
    Validate a state token to prevent CSRF attacks.
    
    Args:
        state: The state token to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not state or state not in state_tokens:
        return False
    
    # Clean up old state tokens (older than 10 minutes)
    # PRODUCTION: If using Redis/database, use TTL/expiration instead of manual cleanup
    current_time = datetime.utcnow()
    expired_states = [
        s for s, timestamp in state_tokens.items()
        if (current_time - timestamp).total_seconds() > 600
    ]
    for expired_state in expired_states:
        del state_tokens[expired_state]
    
    # Check if state exists and is not expired
    if state in state_tokens:
        del state_tokens[state]  # Use once
        return True
    
    return False


def get_current_user():
    """
    Protected route dependency - validates session and authorization.
    
    This function implements a multi-layer authorization check:
    1. Validates session cookie exists and is valid
    2. Queries users table by google_sub
    3. Verifies users.is_active = True
    4. Queries approved_users table by email
    5. Verifies approved_users.is_active = True
    
    SECURITY NOTES:
    - Checks BOTH tables' is_active flags (defense in depth)
    - Returns 401 for all failure modes (doesn't leak which check failed)
    - Should be called at the start of every protected route
    - Use as decorator or call directly in route function
    
    Returns:
        dict: Session data with user info if authorized
        
    Raises:
        Returns 401 JSON response if not authorized (Flask will handle the return)
        
    Usage:
        @auth_bp.route("/protected")
        def protected_route():
            session_data = get_current_user()
            if isinstance(session_data, tuple):  # Error response
                return session_data
            # User is authorized, proceed with route logic
            return jsonify({"data": "protected"})
    """
    from flask import g
    
    # Step 1: Get session ID from cookie
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        current_app.logger.warning("Protected route access attempt without session cookie")
        return jsonify({
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Authentication required"
            }
        }), 401
    
    # Step 2: Validate session exists in memory
    session = sessions.get(session_id)
    
    if not session:
        current_app.logger.warning(f"Protected route access attempt with invalid session: {session_id}")
        return jsonify({
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid or expired session"
            }
        }), 401
    
    # Step 3-6: Dual-layer authorization check (users + approved_users)
    # Uses database utility function for consistent logic
    from .db import is_user_authorized
    
    google_sub = session.get("user_id")  # This is actually google_sub
    email = session.get("email")
    
    if not google_sub or not email:
        current_app.logger.error(f"Session missing required fields: {session_id}")
        return jsonify({
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid session data"
            }
        }), 401
    
    # Check both users.is_active and approved_users.is_active
    authorized, user = is_user_authorized(google_sub, email)
    
    if not authorized:
        # Generic 401 response (don't leak which check failed)
        current_app.logger.warning(f"Authorization check failed for user: {email}")
        return jsonify({
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Access denied"
            }
        }), 401
    
    # Authorization successful - store user in Flask g context for easy access
    g.current_user = user
    g.session = session
    
    return session


@auth_bp.route("/auth/google/login", methods=["GET"])
def google_login():
    """
    Initiate Google OAuth login flow.
    
    Generates a state token for CSRF protection and redirects the user
    to Google's OAuth consent screen.
    
    Returns:
        Redirect response to Google OAuth URL
    """
    # Validate required environment variables
    if not GOOGLE_CLIENT_ID:
        current_app.logger.error("GOOGLE_CLIENT_ID not configured")
        return jsonify({
            "error": {
                "code": "CONFIGURATION_ERROR",
                "message": "Google OAuth not configured. GOOGLE_CLIENT_ID is required."
            }
        }), 500
    
    # Generate state token for CSRF protection
    state = generate_state_token()
    state_tokens[state] = datetime.utcnow()
    
    # Build Google OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    # Construct the authorization URL
    auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    
    current_app.logger.info(f"Redirecting to Google OAuth: {auth_url}")
    return redirect(auth_url)


@auth_bp.route("/auth/denied", methods=["GET"])
def auth_denied():
    """
    Authorization denied endpoint.
    
    Redirects here when a user successfully authenticates with Google
    but their email is not in the approved_users allowlist or is not active.
    
    SECURITY NOTES:
    - Returns 403 Forbidden (user is authenticated but not authorized)
    - Generic message (doesn't reveal if email exists in system)
    - No session cookie is set
    - Logs attempt for security audit trail
    
    Returns:
        Redirect response to frontend with error parameter
    """
    # Log the denial (email may be in query param from callback redirect)
    email = request.args.get("email")
    if email:
        current_app.logger.warning(f"Authorization denied for email: {email}")
    else:
        current_app.logger.warning("Authorization denied for unknown email")
    
    # Redirect to frontend with error parameter
    # Frontend can show a friendly "Contact admin to request access" message
    return redirect(f"{FRONTEND_BASE_URL}?error=unauthorized&message=access_denied")


@auth_bp.route("/auth/google/callback", methods=["GET"])
def google_callback():
    """
    Handle Google OAuth callback.
    
    This endpoint:
    1. Validates the state token (CSRF protection)
    2. Exchanges the authorization code for tokens
    3. Verifies the ID token using python-jose
    4. Creates a session and stores user info
    5. Sets an HTTP-only cookie with the session ID
    6. Redirects to the frontend
    
    Query Parameters:
        code: Authorization code from Google
        state: State token for CSRF protection
        
    Returns:
        Redirect response to frontend with session cookie set
    """
    # Get authorization code and state from query parameters
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    
    # Handle OAuth errors from Google
    if error:
        # PRODUCTION: Don't log user-facing OAuth errors (e.g., "access_denied") as errors
        # Only log actual system errors. Consider sanitizing error messages for security.
        current_app.logger.error(f"Google OAuth error: {error}")
        return redirect(f"{FRONTEND_BASE_URL}?error={error}")
    
    # Validate required parameters
    if not code:
        current_app.logger.error("Missing authorization code in callback")
        return redirect(f"{FRONTEND_BASE_URL}?error=missing_code")
    
    if not state:
        current_app.logger.error("Missing state token in callback")
        return redirect(f"{FRONTEND_BASE_URL}?error=missing_state")
    
    # Validate state token (CSRF protection)
    if not validate_state_token(state):
        current_app.logger.error("Invalid or expired state token")
        return jsonify({
            "error": {
                "code": "INVALID_STATE",
                "message": "Invalid or expired state token. Possible CSRF attack."
            }
        }), 400
    
    # Validate required environment variables
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        current_app.logger.error("Google OAuth credentials not configured")
        return jsonify({
            "error": {
                "code": "CONFIGURATION_ERROR",
                "message": "Google OAuth not configured. GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required."
            }
        }), 500
    
    try:
        # Exchange authorization code for tokens
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        current_app.logger.info("Exchanging authorization code for tokens")
        token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        id_token = tokens.get("id_token")
        if not id_token:
            current_app.logger.error("No ID token in token response")
            return jsonify({
                "error": {
                    "code": "TOKEN_EXCHANGE_ERROR",
                    "message": "Failed to obtain ID token from Google"
                }
            }), 500
        
        # Verify ID token using python-jose
        try:
            # Fetch Google's public keys (JWKs) for token verification
            # PRODUCTION: Implement JWKs caching (e.g., cache for 1 hour, refresh on cache miss)
            # Google rotates keys infrequently, so caching reduces API calls and improves performance
            # Use Redis or in-memory cache with TTL (e.g., cachetools, Flask-Caching)
            # Example: cache_key = "google_jwks"; if cached: use cached, else: fetch and cache
            jwks_url = "https://www.googleapis.com/oauth2/v3/certs"
            current_app.logger.info("Fetching Google's public keys for token verification")
            jwks_response = requests.get(jwks_url, timeout=10)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
            
            # Get the token header to find the key ID (kid)
            unverified_header = jwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise JWTError("Token header missing key ID (kid)")
            
            # Find the matching key in the JWKs
            rsa_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Construct the RSA public key from the JWK
                    n = base64url_decode(key["n"].encode("utf-8"))
                    e = base64url_decode(key["e"].encode("utf-8"))
                    
                    # Convert to integers
                    n_int = int.from_bytes(n, "big")
                    e_int = int.from_bytes(e, "big")
                    
                    # Create RSA public key
                    public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key(default_backend())
                    rsa_key = public_key
                    break
            
            if not rsa_key:
                raise JWTError(f"Unable to find matching key for kid: {kid}")
            
            # Verify and decode the token
            # This verifies the signature, expiration, issuer, and audience
            decoded_token = jwt.decode(
                id_token,
                rsa_key,
                algorithms=["RS256"],
                audience=GOOGLE_CLIENT_ID,
                issuer="https://accounts.google.com",
                options={
                    "verify_at_hash": False
                }
            )
            
            # Extract user information from verified token
            user_info = {
                "user_id": decoded_token.get("sub"),
                "email": decoded_token.get("email"),
                "name": decoded_token.get("name"),
                "picture": decoded_token.get("picture"),
                "email_verified": decoded_token.get("email_verified", False)
            }
            
            # PRODUCTION: Be careful logging user emails - consider GDPR/privacy requirements
            # Optionally log only user_id or hash the email for logging
            current_app.logger.info(f"Successfully verified ID token for user: {user_info.get('email')}")
            
            # AUTHORIZATION CHECK: Verify email is in approved_users allowlist
            # This check happens AFTER authentication but BEFORE session creation
            # If user is not approved, redirect to /auth/denied (no session created)
            user_email = user_info.get("email")
            
            if not user_email:
                current_app.logger.error("ID token missing email claim")
                return redirect(f"{FRONTEND_BASE_URL}?error=missing_email")
            
            # Log email for debugging
            current_app.logger.info(f"OAuth callback: Checking authorization for email: {user_email}")
            
            # Check if database is configured
            if not current_app.config.get("SQLALCHEMY_DATABASE_URI"):
                current_app.logger.error("DATABASE_URL not configured - cannot check authorization")
                return jsonify({
                    "error": {
                        "code": "CONFIGURATION_ERROR",
                        "message": "Database not configured. DATABASE_URL is required."
                    }
                }), 500
            
            # Check if email is in approved_users table and is_active=True
            # Uses database utility function for consistent authorization logic
            from .db import is_email_approved, get_or_create_user
            
            if not is_email_approved(user_email):
                # Email not approved or not active - deny access
                # Redirect to /auth/denied (no session created)
                current_app.logger.warning(f"Authorization denied for email: {user_email}")
                return redirect(f"/auth/denied?email={user_email}")
            
            current_app.logger.info(f"Authorization approved for email: {user_email}")
            
            # User is approved - find or create user record in users table
            try:
                user = get_or_create_user(
                    google_sub=user_info["user_id"],
                    email=user_email,
                    name=user_info.get("name", "")
                )
            except Exception as e:
                current_app.logger.error(f"Failed to create/update user record: {str(e)}")
                return jsonify({
                    "error": {
                        "code": "DATABASE_ERROR",
                        "message": "Failed to create user account"
                    }
                }), 500
            
        except requests.RequestException as e:
            current_app.logger.error(f"Failed to fetch Google's public keys: {str(e)}")
            return jsonify({
                "error": {
                    "code": "TOKEN_VERIFICATION_ERROR",
                    "message": f"Failed to fetch Google's public keys: {str(e)}"
                }
            }), 500
        except JWTError as e:
            current_app.logger.error(f"ID token verification failed: {str(e)}")
            return jsonify({
                "error": {
                    "code": "TOKEN_VERIFICATION_ERROR",
                    "message": f"Failed to verify ID token: {str(e)}"
                }
            }), 401
        
        # Create session
        # PRODUCTION: Store sessions in Redis/database instead of in-memory dict
        # Add session expiration check (e.g., expire after 7 days of inactivity)
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "user_id": user_info["user_id"],  # Google sub (google_sub)
            "email": user_info["email"],
            "name": user_info.get("name", ""),
            "picture": user_info.get("picture", ""),
            "created_at": datetime.utcnow(),
            "db_user_id": str(user.id)  # Database user ID for reference
        }
        
        current_app.logger.info(f"Created session {session_id} for user {user_info['email']}")
        
        # Create redirect response
        response = make_response(redirect(f"{FRONTEND_BASE_URL}?auth=success"))
        
        # Set HTTP-only cookie with session ID
        # PRODUCTION CHANGES REQUIRED:
        # - secure=True (requires HTTPS)
        # - domain=".yourdomain.com" (if frontend/backend on different subdomains)
        # - samesite="None" (if frontend/backend on different domains, requires secure=True)
        # - Consider shorter max_age for production (e.g., 1-3 days instead of 7)
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            secure=False,  # PRODUCTION: Change to True (requires HTTPS)
            samesite="Lax",  # PRODUCTION: Use "None" if cross-domain, requires secure=True
            path="/",
            max_age=86400 * 7,  # PRODUCTION: Consider shorter expiration (e.g., 86400 * 1 for 1 day)
            # domain=None  # PRODUCTION: Set domain if needed (e.g., ".yourdomain.com")
        )
        
        return response
        
    except requests.RequestException as e:
        current_app.logger.error(f"Token exchange request failed: {str(e)}")
        return jsonify({
            "error": {
                "code": "TOKEN_EXCHANGE_ERROR",
                "message": f"Failed to exchange authorization code: {str(e)}"
            }
        }), 500
    except Exception as e:
        # PRODUCTION: Don't expose internal error details to users
        # Log full error details server-side, but return generic message to client
        current_app.logger.error(f"Unexpected error in OAuth callback: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"An unexpected error occurred: {str(e)}"  # PRODUCTION: Use generic message like "Authentication failed"
            }
        }), 500


@auth_bp.route("/me", methods=["GET"])
def get_user_info():
    """
    Get current user information from session cookie.
    
    PROTECTED ROUTE: Requires valid session and active authorization.
    
    Authorization checks:
    - Valid session cookie
    - User exists in users table with is_active=True
    - Email exists in approved_users table with is_active=True
    
    Returns:
        JSON response with user info if authorized
        401 if not authorized
        200 with logged_in=false if no session (allows frontend to check auth state)
    """
    # Check if session cookie exists
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        # No session cookie - return logged_in=false (not an error)
        return jsonify({"logged_in": False}), 200
    
    # Validate session and authorization
    session_data = get_current_user()
    
    # If get_current_user returns a tuple, it's an error response (401)
    if isinstance(session_data, tuple):
        # Clear invalid session cookie
        response = make_response(session_data)
        response.set_cookie("session_id", "", expires=0, path="/")
        return response
    
    # User is authorized - return user info
    # Include both session data and database user data
    from flask import g
    user = g.current_user
    
    return jsonify({
        "logged_in": True,
        "user": {
            "id": str(user.id),
            "user_id": session_data["user_id"],  # Google sub
            "email": session_data["email"],
            "name": session_data["name"],
            "picture": session_data.get("picture", ""),
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        }
    }), 200


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    """
    Log out the current user by deleting the session and clearing the cookie.
    
    Returns:
        JSON response confirming logout
    """
    # Get session ID from cookie
    session_id = request.cookies.get("session_id")
    
    if session_id and session_id in sessions:
        # Delete session
        user_email = sessions[session_id].get("email", "unknown")
        del sessions[session_id]
        current_app.logger.info(f"Logged out user: {user_email}")
    
    # Create response
    response = jsonify({"message": "Logged out successfully"})
    
    # Clear the cookie
    # PRODUCTION: Match cookie settings from login (secure=True, domain if needed)
    response.set_cookie(
        "session_id",
        "",
        expires=0,
        httponly=True,
        secure=False,  # PRODUCTION: Change to True
        samesite="Lax",  # PRODUCTION: Match login cookie setting
        path="/"
        # domain=None  # PRODUCTION: Set if domain was set during login
    )
    
    return response, 200

