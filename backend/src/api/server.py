"""
Flask Application Server

Configures and runs the Flask application with CORS,
blueprint registration, and EPHR system initialization.
"""

import os
import json
import sys

from flask import Flask
from flask_cors import CORS

from .routes import api, init_routes
from ..core.ephr_system import EPHRSystem


def create_app(config_path=None):
    """
    Application factory.
    
    Creates and configures the Flask app with:
    - CORS for frontend access
    - API blueprint registration
    - EPHR system initialization
    - Database setup and optional seeding
    """
    app = Flask(__name__)

    # Load configuration
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'system_config.json'
        )
    
    config_path = os.path.normpath(config_path)
    
    with open(config_path, 'r') as f:
        config = json.load(f)

    app.config['SECRET_KEY'] = config['jwt']['secret_key']
    app.config['DEBUG'] = config['server'].get('debug', False)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize EPHR system
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', config['database']['path'])
    db_path = os.path.normpath(db_path)

    k = config['threshold']['k']
    n = config['threshold']['n']

    ephr_system = EPHRSystem(db_path=db_path, k=k, n=n)

    # Register routes
    init_routes(ephr_system)
    app.register_blueprint(api, url_prefix='/api')

    # Health check route
    @app.route('/')
    def index():
        return {
            'name': 'IBDDS EPHR System',
            'version': '1.0.0',
            'description': 'Identity-Based Distributed Decryption for Secure EPHR Sharing',
            'api_prefix': '/api',
            'endpoints': {
                'register': 'POST /api/register',
                'login': 'POST /api/login',
                'upload_record': 'POST /api/ephr/upload',
                'list_records': 'GET /api/ephr/records',
                'get_record': 'GET /api/ephr/<record_id>',
                'grant_access': 'POST /api/access/grant',
                'revoke_access': 'POST /api/access/revoke',
                'list_grants': 'GET /api/access/grants',
                'audit_logs': 'GET /api/audit',
                'doctors': 'GET /api/doctors',
                'system_status': 'GET /api/system/status'
            }
        }

    # Store system reference on app for access in seed scripts
    app.ephr_system = ephr_system

    return app


def run_server():
    """Run the Flask development server."""
    config_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'config', 'system_config.json'
    )
    config_path = os.path.normpath(config_path)
    
    with open(config_path, 'r') as f:
        config = json.load(f)

    app = create_app(config_path)
    
    host = config['server'].get('host', '0.0.0.0')
    port = config['server'].get('port', 5000)
    debug = config['server'].get('debug', True)

    print(f"\n{'='*60}")
    print(f" IBDDS EPHR System - API Server")
    print(f" Running on http://{host}:{port}")
    print(f" Threshold: {config['threshold']['k']}-of-{config['threshold']['n']}")
    print(f" Encryption: IBE (Boneh-Franklin)")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
