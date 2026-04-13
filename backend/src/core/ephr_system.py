"""
EPHR System - Core Module

Central class managing Electronic Personal Health Records.
Coordinates encryption, access control, audit logging,
and distributed decryption operations.
"""

import uuid
import json
import sqlite3
import os
from datetime import datetime, timezone

from ..crypto.identity_based_encryption import IdentityBasedEncryption, IBECiphertext
from ..crypto.distributed_decryption import DecryptionCoordinator
from .access_control import AccessControl
from .audit_log import AuditLog


class EPHRSystem:
    """
    Core EPHR management system.
    
    Handles:
    - Record storage with IBE encryption
    - Access grant management
    - Distributed threshold decryption
    - Audit logging of all operations
    """

    def __init__(self, db_path, k=3, n=5):
        self.db_path = db_path
        self.k = k
        self.n = n

        # Initialize subsystems
        self.ibe = IdentityBasedEncryption()
        self.access_control = AccessControl(db_path)
        self.audit_log = AuditLog(db_path)

        # Setup IBE and distributed decryption
        key_file = os.path.join(os.path.dirname(db_path), 'master_key.json')
        if os.path.exists(key_file):
            import json
            from ..crypto.identity_based_encryption import IBEParams, IBEMasterSecret
            with open(key_file, 'r') as f:
                data = json.load(f)
            self.params = IBEParams.from_dict(data['params'])
            self.master_secret = IBEMasterSecret.from_dict(data['secret'])
        else:
            self.params, self.master_secret = self.ibe.setup()
            import json
            with open(key_file, 'w') as f:
                json.dump({
                    'params': self.params.to_dict(),
                    'secret': self.master_secret.to_dict()
                }, f)

        self.ibe.params = self.params
        self.ibe.master_secret = self.master_secret
        
        self.coordinator = DecryptionCoordinator(k, n, self.ibe)
        self.coordinator.initialize_servers(self.master_secret.secret)

        # Initialize database

        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('patient', 'doctor')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ephr_records (
                    record_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    ciphertext TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    encrypted INTEGER DEFAULT 1,
                    encryption_algorithm TEXT DEFAULT 'IBE-BF',
                    metadata TEXT,
                    FOREIGN KEY (patient_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS access_grants (
                    grant_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    accessor_id TEXT NOT NULL,
                    access_types TEXT NOT NULL,
                    resource_fields TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    expires_at TEXT,
                    revoked INTEGER DEFAULT 0,
                    revoked_at TEXT,
                    FOREIGN KEY (patient_id) REFERENCES users(id),
                    FOREIGN KEY (accessor_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor_id TEXT,
                    patient_id TEXT,
                    resource_id TEXT,
                    status TEXT DEFAULT 'success',
                    details TEXT
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def register_user(self, email, password_hash, role):
        """Register a new user (patient or doctor)."""
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, email, password_hash, role, now)
            )
            conn.commit()
        finally:
            conn.close()

        self.audit_log.log_action(
            action='user_registered',
            actor_id=user_id,
            status='success',
            details={'email': email, 'role': role}
        )

        return user_id

    def get_user_by_email(self, email):
        """Look up a user by email."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_user_by_id(self, user_id):
        """Look up a user by ID."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def store_ephr(self, patient_id, health_data):
        """
        Encrypt and store a new EPHR record.
        
        Args:
            patient_id: Patient's user ID
            health_data: Dict of health data fields
            
        Returns:
            record_id
        """
        # Get patient's email (identity for IBE)
        patient = self.get_user_by_id(patient_id)
        if not patient:
            raise ValueError("Patient not found")

        identity = patient['email']

        # Extract private key for encryption
        private_key = self.ibe.extract_key(identity)

        # Serialize health data
        plaintext = json.dumps(health_data)

        # Encrypt using IBE
        ciphertext = self.ibe.encrypt_with_key(private_key, plaintext)

        # Store in database
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        metadata = {
            'fields': list(health_data.keys()),
            'field_count': len(health_data),
            'encryption_algorithm': 'IBE-BF',
            'threshold': f'{self.k}-of-{self.n}'
        }

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO ephr_records 
                   (record_id, patient_id, ciphertext, created_at, updated_at,
                    encrypted, encryption_algorithm, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (record_id, patient_id, ciphertext.serialize(), now, now,
                 1, 'IBE-BF', json.dumps(metadata))
            )
            conn.commit()
        finally:
            conn.close()

        # Audit log
        self.audit_log.log_action(
            action='record_encrypted_and_stored',
            actor_id=patient_id,
            patient_id=patient_id,
            resource_id=record_id,
            status='success',
            details={'fields': list(health_data.keys())}
        )

        return record_id

    def get_ephr(self, record_id, accessor_id):
        """
        Retrieve and decrypt an EPHR record with access control.
        
        Args:
            record_id: Record to retrieve
            accessor_id: ID of the user requesting access
            
        Returns:
            Dict with record data (filtered by access grant fields)
        """
        # Get the record
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            record = conn.execute(
                "SELECT * FROM ephr_records WHERE record_id = ?", (record_id,)
            ).fetchone()
        finally:
            conn.close()

        if not record:
            raise ValueError("Record not found")

        patient_id = record['patient_id']

        # If accessor is the patient, full access
        if accessor_id == patient_id:
            ciphertext = IBECiphertext.deserialize(record['ciphertext'])
            patient = self.get_user_by_id(patient_id)
            private_key = self.ibe.extract_key(patient['email'])
            plaintext = self.ibe.decrypt(private_key, ciphertext)
            health_data = json.loads(plaintext.decode('utf-8'))

            self.audit_log.log_action(
                action='record_decrypted',
                actor_id=accessor_id,
                patient_id=patient_id,
                resource_id=record_id,
                status='success',
                details={'access_type': 'owner'}
            )

            return {
                'record_id': record['record_id'],
                'patient_id': patient_id,
                'data': health_data,
                'created_at': record['created_at'],
                'metadata': json.loads(record['metadata']) if record['metadata'] else None,
                'access_type': 'owner'
            }

        # Check access grant
        access_result = self.access_control.check_access(patient_id, accessor_id)

        self.audit_log.log_action(
            action='access_checked',
            actor_id=accessor_id,
            patient_id=patient_id,
            resource_id=record_id,
            status='success' if access_result['allowed'] else 'denied',
            details=access_result
        )

        if not access_result['allowed']:
            raise PermissionError(
                f"Access denied: {access_result.get('reason', 'No valid grant')}"
            )

        # Decrypt using distributed decryption
        ciphertext_dict = json.loads(record['ciphertext'])
        patient = self.get_user_by_id(patient_id)

        ciphertext = IBECiphertext.from_dict(ciphertext_dict)
        plaintext = self.coordinator.combine_and_decrypt(ciphertext, patient['email'])
        health_data = json.loads(plaintext.decode('utf-8'))

        # Filter fields based on grant
        allowed_fields = access_result['grant']['resource_fields']
        filtered_data = self.access_control.filter_fields(health_data, allowed_fields)

        self.audit_log.log_action(
            action='record_decrypted',
            actor_id=accessor_id,
            patient_id=patient_id,
            resource_id=record_id,
            status='success',
            details={
                'access_type': 'grant',
                'grant_id': access_result['grant']['grant_id'],
                'fields_returned': list(filtered_data.keys())
            }
        )

        return {
            'record_id': record['record_id'],
            'patient_id': patient_id,
            'data': filtered_data,
            'created_at': record['created_at'],
            'metadata': json.loads(record['metadata']) if record['metadata'] else None,
            'access_type': 'grant',
            'allowed_fields': allowed_fields
        }

    def get_patient_records(self, patient_id):
        """List all records for a patient (metadata only, no decryption)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT record_id, patient_id, created_at, updated_at, encrypted, encryption_algorithm, metadata FROM ephr_records WHERE patient_id = ? ORDER BY created_at DESC",
                (patient_id,)
            ).fetchall()

            return [
                {
                    'record_id': row['record_id'],
                    'patient_id': row['patient_id'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'encrypted': bool(row['encrypted']),
                    'encryption_algorithm': row['encryption_algorithm'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_accessible_records(self, accessor_id):
        """Get all records a doctor has access to (via grants)."""
        grants = self.access_control.get_grants_for_accessor(accessor_id)
        
        records = []
        for grant in grants:
            if not grant['is_active']:
                continue
            
            patient_id = grant['patient_id']
            patient_records = self.get_patient_records(patient_id)
            
            for rec in patient_records:
                rec['grant_id'] = grant['grant_id']
                rec['patient_email'] = grant['patient_email']
                rec['allowed_fields'] = grant['resource_fields']
                records.append(rec)

        return records

    def grant_access(self, patient_id, accessor_email, access_types, resource_fields,
                     duration_days=30):
        """
        Grant access from a patient to a doctor.
        
        Args:
            patient_id: Patient's user ID
            accessor_email: Doctor's email
            access_types: List of access types
            resource_fields: List of fields the doctor can see
            duration_days: Grant duration
        """
        # Look up accessor by email
        accessor = self.get_user_by_email(accessor_email)
        if not accessor:
            raise ValueError(f"User with email {accessor_email} not found")
        if accessor['role'] != 'doctor':
            raise ValueError("Can only grant access to doctors")
        if accessor['id'] == patient_id:
            raise ValueError("Cannot grant access to yourself")

        grant_id = self.access_control.create_grant(
            patient_id=patient_id,
            accessor_id=accessor['id'],
            access_types=access_types,
            resource_fields=resource_fields,
            duration_days=duration_days
        )

        self.audit_log.log_action(
            action='access_granted',
            actor_id=patient_id,
            patient_id=patient_id,
            resource_id=grant_id,
            status='success',
            details={
                'accessor_email': accessor_email,
                'access_types': access_types,
                'resource_fields': resource_fields,
                'duration_days': duration_days
            }
        )

        return grant_id

    def revoke_access(self, grant_id, patient_id):
        """Revoke an access grant."""
        success = self.access_control.revoke_grant(grant_id, patient_id)

        self.audit_log.log_action(
            action='access_revoked',
            actor_id=patient_id,
            patient_id=patient_id,
            resource_id=grant_id,
            status='success' if success else 'error',
            details={'grant_id': grant_id}
        )

        return success

    def get_doctors(self):
        """Get all registered doctors."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, email, role, created_at FROM users WHERE role = 'doctor'"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_cluster_status(self):
        """Get status of the decryption server cluster."""
        return self.coordinator.get_cluster_status()
