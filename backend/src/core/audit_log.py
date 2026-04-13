"""
Audit Log Module

Manages audit trail entries for HIPAA compliance.
Every action on health records (upload, access, grant, revoke)
is logged with actor, patient, resource, timestamp, and status.
"""

import uuid
import sqlite3
from datetime import datetime, timezone
import json


class AuditLog:
    """Audit logging system for tracking all EPHR operations."""

    def __init__(self, db_path):
        self.db_path = db_path

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def log_action(self, action, actor_id, patient_id=None, resource_id=None,
                   status='success', details=None):
        """
        Record an audit log entry.
        
        Args:
            action: Action type (e.g., 'record_encrypted_and_stored', 'access_granted')
            actor_id: ID of the user performing the action
            patient_id: ID of the patient whose data is affected
            resource_id: ID of the specific resource (record/grant)
            status: 'success', 'denied', or 'error'
            details: Additional JSON-serializable details
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO audit_logs 
                   (entry_id, timestamp, action, actor_id, patient_id, resource_id, status, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, timestamp, action, actor_id, patient_id, resource_id,
                 status, json.dumps(details) if details else None)
            )
            conn.commit()
        finally:
            conn.close()

        return entry_id

    def get_logs(self, patient_id=None, actor_id=None, action=None, limit=100):
        """
        Retrieve audit log entries with optional filtering.
        
        Args:
            patient_id: Filter by patient
            actor_id: Filter by actor
            action: Filter by action type
            limit: Maximum entries to return
        """
        conn = self._get_conn()
        try:
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if patient_id:
                query += " AND patient_id = ?"
                params.append(patient_id)
            if actor_id:
                query += " AND actor_id = ?"
                params.append(actor_id)
            if action:
                query += " AND action = ?"
                params.append(action)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            return [
                {
                    'entry_id': row['entry_id'],
                    'timestamp': row['timestamp'],
                    'action': row['action'],
                    'actor_id': row['actor_id'],
                    'patient_id': row['patient_id'],
                    'resource_id': row['resource_id'],
                    'status': row['status'],
                    'details': json.loads(row['details']) if row['details'] else None
                }
                for row in rows
            ]
        finally:
            conn.close()
