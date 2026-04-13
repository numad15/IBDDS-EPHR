"""
Security Utilities

Password hashing (bcrypt) and JWT token management for authentication.
"""

import bcrypt
import jwt
import json
import os
from datetime import datetime, timedelta, timezone


# Load config
_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'system_config.json')
with open(os.path.normpath(_config_path), 'r') as f:
    _config = json.load(f)

JWT_SECRET = _config['jwt']['secret_key']
JWT_ALGORITHM = _config['jwt']['algorithm']
JWT_EXPIRATION_HOURS = _config['jwt']['expiration_hours']


def hash_password(password):
    """Hash a password using bcrypt with automatic salt generation."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id, email, role):
    """
    Create a JWT token for an authenticated user.
    
    Payload includes:
    - user_id: Unique user identifier
    - email: User's email (also their IBE identity)
    - role: 'patient' or 'doctor'
    - exp: Expiration timestamp
    - iat: Issued-at timestamp
    """
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'iat': now,
        'exp': now + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """
    Decode and validate a JWT token.
    
    Returns the payload dict if valid.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def validate_token(token):
    """
    Validate a JWT token and return user info.
    
    Returns:
        dict with user_id, email, role if valid
        None if invalid
    """
    try:
        payload = decode_token(token)
        return {
            'user_id': payload['user_id'],
            'email': payload['email'],
            'role': payload['role']
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
