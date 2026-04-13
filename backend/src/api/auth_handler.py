"""
Authentication Handler

JWT-based authentication middleware for Flask routes.
Provides decorators and utilities for protecting API endpoints.
"""

from functools import wraps
from flask import request, jsonify
from ..utils.security import validate_token


def require_auth(f):
    """
    Decorator to require JWT authentication on a route.
    
    Extracts the token from the Authorization header,
    validates it, and passes user info to the route handler.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'No valid token provided'
            }), 401

        # Validate token
        user_info = validate_token(token)
        if not user_info:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': 'Please login again'
            }), 401

        # Pass user info to the route handler
        request.user = user_info
        return f(*args, **kwargs)

    return decorated


def require_role(role):
    """
    Decorator to require a specific role (patient or doctor).
    Must be used after @require_auth.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if request.user['role'] != role:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This action requires {role} role'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator
