"""
Access Control Module

Fine-grained access control for EPHR records.
Enforces field-level permissions, temporal validity,
and role-based access policies.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone


class AccessControl:
    """
    Fine-grained access control for EPHR records.
    
    Manages access grants that specify:
    - Which fields a provider can see
    - What type of access is granted (read, write)
    - When the grant expires
    - Whether the grant has been revoked
    """

    def __init__(self, db_path):
        self.db_path = db_path

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def create_grant(self, patient_id, accessor_id, access_types, resource_fields,
                     duration_days=30):
        """
        Create a new access grant from patient to provider.
        
        Args:
            patient_id: Patient's user ID
            accessor_id: Doctor/provider's user ID
            access_types: List of access types (e.g., ['read'])
            resource_fields: List of allowed fields (e.g., ['blood_type', 'allergies'])
            duration_days: How long the grant is valid
            
        Returns:
            grant_id string
        """
        grant_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = datetime(
            now.year, now.month, now.day, now.hour, now.minute, now.second,
            tzinfo=timezone.utc
        )
        # Add duration
        from datetime import timedelta
        expires_at = now + timedelta(days=duration_days)

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO access_grants 
                   (grant_id, patient_id, accessor_id, access_types, resource_fields,
                    granted_at, expires_at, revoked, revoked_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (grant_id, patient_id, accessor_id,
                 json.dumps(access_types), json.dumps(resource_fields),
                 now.isoformat(), expires_at.isoformat(),
                 False, None)
            )
            conn.commit()
        finally:
            conn.close()

        return grant_id

    def check_access(self, patient_id, accessor_id, requested_type='read'):
        """
        Check if an accessor has a valid grant for a patient's records.
        
        Validates:
        1. Grant exists for the patient-accessor pair
        2. Grant is not revoked
        3. Grant has not expired
        4. Requested access type is allowed
        
        Returns:
            dict with 'allowed' bool and 'grant' details, or 'reason' if denied
        """
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            grants = conn.execute(
                """SELECT * FROM access_grants 
                   WHERE patient_id = ? AND accessor_id = ? AND revoked = 0
                   ORDER BY granted_at DESC""",
                (patient_id, accessor_id)
            ).fetchall()

            if not grants:
                return {
                    'allowed': False,
                    'reason': 'No active access grant found'
                }

            now = datetime.now(timezone.utc).isoformat()

            for grant in grants:
                # Check expiration
                if grant['expires_at'] and grant['expires_at'] < now:
                    continue

                # Check access type
                access_types = json.loads(grant['access_types'])
                if requested_type not in access_types:
                    continue

                # Grant is valid
                return {
                    'allowed': True,
                    'grant': {
                        'grant_id': grant['grant_id'],
                        'access_types': access_types,
                        'resource_fields': json.loads(grant['resource_fields']),
                        'expires_at': grant['expires_at']
                    }
                }

            return {
                'allowed': False,
                'reason': 'No valid grant (expired or wrong access type)'
            }
        finally:
            conn.close()

    def filter_fields(self, data, allowed_fields):
        """
        Filter record data to only include allowed fields.
        
        This is the core of fine-grained access control:
        only return the specific fields the grant permits.
        
        Args:
            data: Full health record data (dict)
            allowed_fields: List of field names the accessor can see
            
        Returns:
            Filtered dict containing only allowed fields
        """
        if not allowed_fields:
            return {}
        
        # 'all' means full access
        if 'all' in allowed_fields:
            return data

        return {k: v for k, v in data.items() if k in allowed_fields}

    def revoke_grant(self, grant_id, patient_id):
        """
        Revoke an access grant.
        
        Only the patient who created the grant can revoke it.
        """
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        try:
            result = conn.execute(
                """UPDATE access_grants 
                   SET revoked = 1, revoked_at = ?
                   WHERE grant_id = ? AND patient_id = ?""",
                (now, grant_id, patient_id)
            )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    def get_grants_for_patient(self, patient_id):
        """Get all grants created by a patient."""
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT ag.*, u.email as accessor_email 
                   FROM access_grants ag
                   LEFT JOIN users u ON ag.accessor_id = u.id
                   WHERE ag.patient_id = ?
                   ORDER BY ag.granted_at DESC""",
                (patient_id,)
            ).fetchall()

            return [
                {
                    'grant_id': row['grant_id'],
                    'accessor_id': row['accessor_id'],
                    'accessor_email': row['accessor_email'],
                    'access_types': json.loads(row['access_types']),
                    'resource_fields': json.loads(row['resource_fields']),
                    'granted_at': row['granted_at'],
                    'expires_at': row['expires_at'],
                    'revoked': bool(row['revoked']),
                    'revoked_at': row['revoked_at']
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_grants_for_accessor(self, accessor_id):
        """Get all grants where the user is the accessor (doctor)."""
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT ag.*, u.email as patient_email 
                   FROM access_grants ag
                   LEFT JOIN users u ON ag.patient_id = u.id
                   WHERE ag.accessor_id = ? AND ag.revoked = 0
                   ORDER BY ag.granted_at DESC""",
                (accessor_id,)
            ).fetchall()

            now = datetime.now(timezone.utc).isoformat()
            return [
                {
                    'grant_id': row['grant_id'],
                    'patient_id': row['patient_id'],
                    'patient_email': row['patient_email'],
                    'access_types': json.loads(row['access_types']),
                    'resource_fields': json.loads(row['resource_fields']),
                    'granted_at': row['granted_at'],
                    'expires_at': row['expires_at'],
                    'is_active': row['expires_at'] > now if row['expires_at'] else True
                }
                for row in rows
            ]
        finally:
            conn.close()
