"""
Integration tests for the Flask API endpoints.
Tests the full request/response cycle with authentication.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.server import create_app


@pytest.fixture
def app(tmp_path):
    """Create a test app with a temporary database."""
    # Create a temp config
    config = {
        "database": {"uri": "sqlite:///test.db", "path": str(tmp_path / "test.db")},
        "jwt": {"secret_key": "test-secret", "algorithm": "HS256", "expiration_hours": 1},
        "ibe": {"prime": 2147483647, "generator": 5, "hash_function": "sha256"},
        "threshold": {"n": 5, "k": 3},
        "logging": {"level": "ERROR", "format": "json", "file": ""},
        "server": {"host": "127.0.0.1", "port": 5000, "debug": False}
    }
    config_path = str(tmp_path / "config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f)

    app = create_app(config_path)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def patient_token(client):
    """Register and login a patient, return token."""
    client.post('/api/register', json={
        'email': 'patient@test.com', 'password': 'password123', 'role': 'patient'
    })
    resp = client.post('/api/login', json={
        'email': 'patient@test.com', 'password': 'password123'
    })
    return resp.get_json()['token']


@pytest.fixture
def doctor_token(client):
    """Register and login a doctor, return token."""
    client.post('/api/register', json={
        'email': 'doctor@test.com', 'password': 'password123', 'role': 'doctor'
    })
    resp = client.post('/api/login', json={
        'email': 'doctor@test.com', 'password': 'password123'
    })
    return resp.get_json()['token']


class TestAuthEndpoints:
    def test_register_patient(self, client):
        resp = client.post('/api/register', json={
            'email': 'new@test.com', 'password': 'password123', 'role': 'patient'
        })
        assert resp.status_code == 201
        assert 'user_id' in resp.get_json()

    def test_register_duplicate(self, client):
        client.post('/api/register', json={
            'email': 'dup@test.com', 'password': 'pass123', 'role': 'patient'
        })
        resp = client.post('/api/register', json={
            'email': 'dup@test.com', 'password': 'pass123', 'role': 'patient'
        })
        assert resp.status_code == 409

    def test_login_success(self, client):
        client.post('/api/register', json={
            'email': 'login@test.com', 'password': 'pass123', 'role': 'patient'
        })
        resp = client.post('/api/login', json={
            'email': 'login@test.com', 'password': 'pass123'
        })
        assert resp.status_code == 200
        assert 'token' in resp.get_json()

    def test_login_wrong_password(self, client):
        client.post('/api/register', json={
            'email': 'wp@test.com', 'password': 'correct', 'role': 'patient'
        })
        resp = client.post('/api/login', json={
            'email': 'wp@test.com', 'password': 'wrong'
        })
        assert resp.status_code == 401


class TestEPHREndpoints:
    def test_upload_record(self, client, patient_token):
        resp = client.post('/api/ephr/upload', 
            json={'health_data': {'name': 'Test', 'blood_type': 'A+'}},
            headers={'Authorization': f'Bearer {patient_token}'}
        )
        assert resp.status_code == 201
        assert 'record_id' in resp.get_json()

    def test_list_records(self, client, patient_token):
        client.post('/api/ephr/upload',
            json={'health_data': {'name': 'Test'}},
            headers={'Authorization': f'Bearer {patient_token}'}
        )
        resp = client.get('/api/ephr/records',
            headers={'Authorization': f'Bearer {patient_token}'}
        )
        assert resp.status_code == 200
        assert resp.get_json()['count'] >= 1

    def test_unauthorized_upload(self, client):
        resp = client.post('/api/ephr/upload', json={'health_data': {'name': 'Test'}})
        assert resp.status_code == 401


class TestAccessGrantEndpoints:
    def test_grant_access(self, client, patient_token, doctor_token):
        resp = client.post('/api/access/grant',
            json={
                'accessor_email': 'doctor@test.com',
                'access_types': ['read'],
                'resource_fields': ['blood_type'],
                'duration_days': 30
            },
            headers={'Authorization': f'Bearer {patient_token}'}
        )
        assert resp.status_code == 201

    def test_list_grants(self, client, patient_token, doctor_token):
        client.post('/api/access/grant',
            json={
                'accessor_email': 'doctor@test.com',
                'access_types': ['read'],
                'resource_fields': ['blood_type'],
                'duration_days': 30
            },
            headers={'Authorization': f'Bearer {patient_token}'}
        )
        resp = client.get('/api/access/grants',
            headers={'Authorization': f'Bearer {patient_token}'}
        )
        assert resp.status_code == 200
        assert resp.get_json()['count'] >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
