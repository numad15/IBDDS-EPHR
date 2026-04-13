"""
Unit tests for access control and audit logging.
"""

import pytest
import os
import sys
import sqlite3
import json
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.access_control import AccessControl
from src.core.audit_log import AuditLog


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database for testing."""
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE access_grants (
            grant_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            accessor_id TEXT NOT NULL,
            access_types TEXT NOT NULL,
            resource_fields TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            expires_at TEXT,
            revoked INTEGER DEFAULT 0,
            revoked_at TEXT
        );

        CREATE TABLE audit_logs (
            entry_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            actor_id TEXT,
            patient_id TEXT,
            resource_id TEXT,
            status TEXT DEFAULT 'success',
            details TEXT
        );

        INSERT INTO users VALUES ('patient1', 'patient@test.com', 'hash', 'patient', '2024-01-01');
        INSERT INTO users VALUES ('doctor1', 'doctor@test.com', 'hash', 'doctor', '2024-01-01');
    """)
    conn.commit()
    conn.close()
    return path


class TestAccessControl:
    def test_create_grant(self, db_path):
        ac = AccessControl(db_path)
        grant_id = ac.create_grant(
            patient_id='patient1',
            accessor_id='doctor1',
            access_types=['read'],
            resource_fields=['blood_type', 'allergies'],
            duration_days=30
        )
        assert grant_id is not None

    def test_check_access_valid_grant(self, db_path):
        ac = AccessControl(db_path)
        ac.create_grant('patient1', 'doctor1', ['read'], ['blood_type'], 30)
        
        result = ac.check_access('patient1', 'doctor1', 'read')
        assert result['allowed'] is True
        assert 'blood_type' in result['grant']['resource_fields']

    def test_check_access_no_grant(self, db_path):
        ac = AccessControl(db_path)
        result = ac.check_access('patient1', 'doctor1', 'read')
        assert result['allowed'] is False

    def test_revoke_grant(self, db_path):
        ac = AccessControl(db_path)
        grant_id = ac.create_grant('patient1', 'doctor1', ['read'], ['blood_type'], 30)
        
        success = ac.revoke_grant(grant_id, 'patient1')
        assert success is True
        
        result = ac.check_access('patient1', 'doctor1', 'read')
        assert result['allowed'] is False

    def test_filter_fields(self, db_path):
        ac = AccessControl(db_path)
        data = {
            'name': 'John Doe',
            'blood_type': 'O+',
            'allergies': ['Penicillin'],
            'insurance': 'BlueCross'
        }
        filtered = ac.filter_fields(data, ['blood_type', 'allergies'])
        assert 'blood_type' in filtered
        assert 'allergies' in filtered
        assert 'name' not in filtered
        assert 'insurance' not in filtered

    def test_filter_fields_all(self, db_path):
        ac = AccessControl(db_path)
        data = {'a': 1, 'b': 2, 'c': 3}
        filtered = ac.filter_fields(data, ['all'])
        assert filtered == data


class TestAuditLog:
    def test_log_action(self, db_path):
        log = AuditLog(db_path)
        entry_id = log.log_action(
            action='test_action',
            actor_id='patient1',
            patient_id='patient1',
            status='success'
        )
        assert entry_id is not None

    def test_get_logs(self, db_path):
        log = AuditLog(db_path)
        log.log_action('action1', 'patient1', 'patient1')
        log.log_action('action2', 'doctor1', 'patient1')
        
        logs = log.get_logs(patient_id='patient1')
        assert len(logs) == 2

    def test_get_logs_by_action(self, db_path):
        log = AuditLog(db_path)
        log.log_action('upload', 'patient1')
        log.log_action('access', 'doctor1')
        
        logs = log.get_logs(action='upload')
        assert len(logs) == 1
        assert logs[0]['action'] == 'upload'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
