"""
API Routes

Defines all REST API endpoints for the IBDDS EPHR system:
- User registration & login
- EPHR record upload, listing, retrieval (with decryption)
- Access grant management
- Audit log retrieval
- System status
"""

from flask import Blueprint, request, jsonify
from ..utils.security import hash_password, verify_password, create_token
from .auth_handler import require_auth, require_role

api = Blueprint('api', __name__)

# The EPHR system instance is set by the server module
ephr_system = None


def init_routes(system):
    """Initialize routes with the EPHR system instance."""
    global ephr_system
    ephr_system = system


# ==================== AUTH ENDPOINTS ====================

@api.route('/register', methods=['POST'])
def register():
    """Register a new user (patient or doctor)."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', '').strip().lower()

    # Validation
    if not email or not password or not role:
        return jsonify({'error': 'Email, password, and role are required'}), 400
    if role not in ('patient', 'doctor'):
        return jsonify({'error': 'Role must be "patient" or "doctor"'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if '@' not in email:
        return jsonify({'error': 'Invalid email format'}), 400

    # Check if user exists
    existing = ephr_system.get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    # Register
    password_hash = hash_password(password)
    user_id = ephr_system.register_user(email, password_hash, role)

    return jsonify({
        'message': 'User registered successfully',
        'user_id': user_id,
        'email': email,
        'role': role
    }), 201


@api.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Look up user
    user = ephr_system.get_user_by_email(email)
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    if not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Create JWT
    token = create_token(user['id'], user['email'], user['role'])

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'role': user['role']
        }
    }), 200


# ==================== EPHR ENDPOINTS ====================

@api.route('/ephr/upload', methods=['POST'])
@require_auth
@require_role('patient')
def upload_record():
    """Upload and encrypt a new health record."""
    data = request.get_json()

    if not data or 'health_data' not in data:
        return jsonify({'error': 'health_data field is required'}), 400

    health_data = data['health_data']
    if not isinstance(health_data, dict):
        return jsonify({'error': 'health_data must be a JSON object'}), 400

    try:
        record_id = ephr_system.store_ephr(request.user['user_id'], health_data)
        return jsonify({
            'message': 'Record encrypted and stored successfully',
            'record_id': record_id,
            'encryption': 'IBE-BF',
            'threshold': f'{ephr_system.k}-of-{ephr_system.n}'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/ephr/records', methods=['GET'])
@require_auth
def list_records():
    """List records for the current user."""
    user = request.user

    try:
        if user['role'] == 'patient':
            records = ephr_system.get_patient_records(user['user_id'])
        else:
            records = ephr_system.get_accessible_records(user['user_id'])

        return jsonify({
            'records': records,
            'count': len(records)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/ephr/<record_id>', methods=['GET'])
@require_auth
def get_record(record_id):
    """Retrieve and decrypt a specific record (with access control)."""
    try:
        result = ephr_system.get_ephr(record_id, request.user['user_id'])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ACCESS GRANT ENDPOINTS ====================

@api.route('/access/grant', methods=['POST'])
@require_auth
@require_role('patient')
def grant_access():
    """Grant a doctor access to patient's records."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    accessor_email = data.get('accessor_email', '').strip().lower()
    access_types = data.get('access_types', ['read'])
    resource_fields = data.get('resource_fields', [])
    duration_days = data.get('duration_days', 30)

    if not accessor_email:
        return jsonify({'error': 'accessor_email is required'}), 400
    if not resource_fields:
        return jsonify({'error': 'resource_fields is required (list of field names)'}), 400

    try:
        grant_id = ephr_system.grant_access(
            patient_id=request.user['user_id'],
            accessor_email=accessor_email,
            access_types=access_types,
            resource_fields=resource_fields,
            duration_days=duration_days
        )

        return jsonify({
            'message': 'Access granted successfully',
            'grant_id': grant_id,
            'accessor_email': accessor_email,
            'resource_fields': resource_fields,
            'duration_days': duration_days
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/access/revoke', methods=['POST'])
@require_auth
@require_role('patient')
def revoke_access():
    """Revoke an access grant."""
    data = request.get_json()

    if not data or 'grant_id' not in data:
        return jsonify({'error': 'grant_id is required'}), 400

    grant_id = data['grant_id']

    try:
        success = ephr_system.revoke_access(grant_id, request.user['user_id'])
        if success:
            return jsonify({'message': 'Access revoked successfully'}), 200
        else:
            return jsonify({'error': 'Grant not found or already revoked'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/access/grants', methods=['GET'])
@require_auth
def list_grants():
    """List access grants (patient sees their grants, doctor sees grants to them)."""
    user = request.user

    try:
        if user['role'] == 'patient':
            grants = ephr_system.access_control.get_grants_for_patient(user['user_id'])
        else:
            grants = ephr_system.access_control.get_grants_for_accessor(user['user_id'])

        return jsonify({
            'grants': grants,
            'count': len(grants)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== AUDIT LOG ENDPOINTS ====================

@api.route('/audit', methods=['GET'])
@require_auth
def get_audit_logs():
    """Retrieve audit log entries."""
    user = request.user
    patient_id = request.args.get('patient_id', None)
    action = request.args.get('action', None)
    limit = int(request.args.get('limit', 100))

    try:
        # Patients can only see their own logs
        if user['role'] == 'patient':
            patient_id = user['user_id']

        logs = ephr_system.audit_log.get_logs(
            patient_id=patient_id,
            actor_id=None,
            action=action,
            limit=limit
        )

        return jsonify({
            'logs': logs,
            'count': len(logs)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== SYSTEM ENDPOINTS ====================

@api.route('/doctors', methods=['GET'])
@require_auth
def list_doctors():
    """List all registered doctors (for grant selection)."""
    try:
        doctors = ephr_system.get_doctors()
        return jsonify({
            'doctors': [
                {'id': d['id'], 'email': d['email']}
                for d in doctors
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/system/status', methods=['GET'])
@require_auth
def system_status():
    """Get system status including decryption cluster info."""
    try:
        cluster = ephr_system.get_cluster_status()
        return jsonify({
            'status': 'operational',
            'encryption': 'IBE-BF (Boneh-Franklin)',
            'threshold': f'{ephr_system.k}-of-{ephr_system.n}',
            'cluster': cluster
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
