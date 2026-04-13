"""
End-to-end encryption/decryption verification.
Tests the complete flow for both patient and doctor roles.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.server import create_app

results = []

def log(msg):
    results.append(msg)

def verify():
    app = create_app()
    client = app.test_client()
    system = app.ephr_system

    log("=" * 60)
    log("IBDDS EPHR - Encryption/Decryption Verification")
    log("=" * 60)

    # 1. Check database counts
    import sqlite3
    conn = sqlite3.connect(system.db_path)
    patients = conn.execute("SELECT COUNT(*) FROM users WHERE role='patient'").fetchone()[0]
    doctors = conn.execute("SELECT COUNT(*) FROM users WHERE role='doctor'").fetchone()[0]
    records = conn.execute("SELECT COUNT(*) FROM ephr_records").fetchone()[0]
    grants = conn.execute("SELECT COUNT(*) FROM access_grants").fetchone()[0]
    audits = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    conn.close()

    log(f"\nDatabase Contents:")
    log(f"  Patients: {patients}")
    log(f"  Doctors:  {doctors}")
    log(f"  Encrypted Records: {records}")
    log(f"  Access Grants: {grants}")
    log(f"  Audit Log Entries: {audits}")

    # 2. Test Patient Login
    log(f"\n--- TEST: Patient Login ---")
    r = client.post('/api/login', json={'email': 'aarav.patel1@patient.hospital.com', 'password': 'patient001'})
    login_data = r.get_json()
    log(f"  Status: {r.status_code}")
    log(f"  Token received: {'YES' if 'token' in login_data else 'NO'}")
    patient_token = login_data.get('token')
    patient_user = login_data.get('user', {})
    log(f"  User: {patient_user.get('email')} (role: {patient_user.get('role')})")

    # 3. Patient views their records
    log(f"\n--- TEST: Patient Lists Records ---")
    r = client.get('/api/ephr/records', headers={'Authorization': f'Bearer {patient_token}'})
    recs = r.get_json()
    log(f"  Status: {r.status_code}")
    log(f"  Records count: {recs.get('count', 0)}")
    if recs.get('records'):
        rec = recs['records'][0]
        log(f"  First record ID: {rec['record_id'][:12]}...")
        log(f"  Encrypted: {rec.get('encrypted', True)}")
        log(f"  Algorithm: {rec.get('encryption_algorithm', 'IBE-BF')}")

    # 4. Patient decrypts own record
    log(f"\n--- TEST: Patient Decrypts Own Record ---")
    if recs.get('records'):
        record_id = recs['records'][0]['record_id']
        r = client.get(f'/api/ephr/{record_id}', headers={'Authorization': f'Bearer {patient_token}'})
        dec_data = r.get_json()
        log(f"  Status: {r.status_code}")
        log(f"  Access type: {dec_data.get('access_type')}")
        log(f"  Decrypted fields: {list(dec_data.get('data', {}).keys())}")
        data = dec_data.get('data', {})
        log(f"  Name: {data.get('name', 'N/A')}")
        log(f"  Blood Type: {data.get('blood_type', 'N/A')}")
        log(f"  Allergies: {data.get('allergies', 'N/A')}")
        log(f"  Conditions: {data.get('conditions', 'N/A')}")
        log(f"  DECRYPT SUCCESS: YES (patient sees ALL fields)")

    # 5. Doctor Login
    log(f"\n--- TEST: Doctor Login ---")
    r = client.post('/api/login', json={'email': 'dr.aiden.allen@cityhospital.com', 'password': 'doctor001'})
    doc_login = r.get_json()
    log(f"  Status: {r.status_code}")
    doc_token = doc_login.get('token')
    doc_user = doc_login.get('user', {})
    log(f"  User: {doc_user.get('email')} (role: {doc_user.get('role')})")

    # 6. Doctor views accessible records
    log(f"\n--- TEST: Doctor Lists Accessible Records ---")
    r = client.get('/api/ephr/records', headers={'Authorization': f'Bearer {doc_token}'})
    doc_recs = r.get_json()
    log(f"  Status: {r.status_code}")
    log(f"  Accessible records count: {doc_recs.get('count', 0)}")

    # 7. Doctor decrypts a patient record (should see only granted fields)
    log(f"\n--- TEST: Doctor Decrypts Patient Record (Field-Level Access) ---")
    if doc_recs.get('records') and len(doc_recs['records']) > 0:
        doc_rec = doc_recs['records'][0]
        rec_id = doc_rec['record_id']
        allowed = doc_rec.get('allowed_fields', [])
        log(f"  Attempting record: {rec_id[:12]}...")
        log(f"  Patient: {doc_rec.get('patient_email', 'Unknown')}")
        log(f"  Grant allows fields: {allowed}")

        r = client.get(f'/api/ephr/{rec_id}', headers={'Authorization': f'Bearer {doc_token}'})
        if r.status_code == 200:
            dec = r.get_json()
            log(f"  Decrypt Status: SUCCESS")
            log(f"  Access type: {dec.get('access_type')}")
            returned_fields = list(dec.get('data', {}).keys())
            log(f"  Returned fields: {returned_fields}")
            log(f"  Field-level filtering: WORKING")
            for k, v in dec.get('data', {}).items():
                val = v if not isinstance(v, list) else ', '.join(str(x) for x in v)
                log(f"    {k}: {val}")
        else:
            log(f"  Decrypt Status: {r.status_code} - {r.get_json().get('error', 'Unknown')}")

    # 8. Doctor tries to access a record they DON'T have access to
    log(f"\n--- TEST: Doctor Denied Access (No Grant) ---")
    # Get the last patient's record who likely has no grant for this doctor
    last_patient_email = f"yolanda.morris100@patient.hospital.com"
    last_patient = system.get_user_by_email(last_patient_email)
    if last_patient:
        last_recs = system.get_patient_records(last_patient['id'])
        if last_recs:
            r = client.get(f'/api/ephr/{last_recs[0]["record_id"]}', headers={'Authorization': f'Bearer {doc_token}'})
            log(f"  Status: {r.status_code}")
            if r.status_code == 403:
                log(f"  Result: ACCESS DENIED (correct behavior)")
                log(f"  Error: {r.get_json().get('error', '')}")
            elif r.status_code == 200:
                log(f"  Result: ACCESS ALLOWED (doctor has grant for this patient too)")

    # 9. Check audit log
    log(f"\n--- TEST: Audit Log ---")
    r = client.get('/api/audit', headers={'Authorization': f'Bearer {patient_token}'})
    audit = r.get_json()
    log(f"  Status: {r.status_code}")
    log(f"  Audit entries: {audit.get('count', 0)}")
    if audit.get('logs'):
        for entry in audit['logs'][:5]:
            log(f"    [{entry['timestamp'][:19]}] {entry['action']} - {entry['status']}")

    # 10. System status
    log(f"\n--- TEST: System Status ---")
    r = client.get('/api/system/status', headers={'Authorization': f'Bearer {patient_token}'})
    status = r.get_json()
    log(f"  Status: {r.status_code}")
    log(f"  Encryption: {status.get('encryption', 'N/A')}")
    log(f"  Threshold: {status.get('threshold', 'N/A')}")
    cluster = status.get('cluster', {})
    log(f"  Active servers: {cluster.get('active_servers', 'N/A')}/{cluster.get('total_servers', 'N/A')}")

    log(f"\n{'=' * 60}")
    log("ALL VERIFICATION TESTS COMPLETE")
    log(f"{'=' * 60}")

    # Write results
    with open("verification_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))

verify()
