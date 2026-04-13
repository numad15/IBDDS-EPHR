# Antigravity Prompt for IBDDS EPHR System

Identity-Based Distributed Decryption (IBDDS) is a secure **electronic personal health record (EPHR)** system combining Identity-Based Encryption (IBE) with threshold cryptography and fine-grained access control. In IBE, a user’s **identity (e.g. email address)** acts as a public key, eliminating traditional certificates【5†L125-L132】.  For example, implement the **Boneh–Franklin pairing-based IBE scheme** (circa 2001) to enable semantic-security encryption/decryption【7†L231-L237】.  In parallel, use a `(k,n)` threshold decryption setup (based on Shamir’s secret sharing) so that at least *k* out of *n* decryption servers must cooperate to recover any record; fewer than *k* shares yield no information【3†L137-L144】【9†L123-L131】. Patients control **fine-grained access grants** on their records – specifying which fields (e.g. blood type, allergies) a provider can see and for how long.  Every action (upload, access, decryption, grant, revoke) must be **audited** in a log for HIPAA compliance.  Below is a detailed prompt that, when fed to the Antigravity AI, will generate the complete IBDDS project code and design:

## Frontend Design
- **Framework & UI:** Build a responsive web frontend (for example, a React app with Material-UI or Bootstrap styling) with a professional healthcare theme (e.g. clean layout, blue/white color scheme).  
- **Authentication Pages:** Include **Register** and **Login** pages.  Users can register as *patients* or *doctors*.  After login, issue a JWT to authorize API requests.  
- **Patient Dashboard:** Once logged in, a patient sees a dashboard listing their encrypted EPHR records and existing access grants. Provide pages or modals for:
  - **Upload Record:** A form to input new health data (JSON or form fields like name, age, blood type, medications, allergies). Encrypt this data **client-side or via API** using the patient’s identity (email) as the IBE recipient.  Upon submission, POST to the backend (e.g. `/api/ephr/upload`). 
  - **Set Access Grant:** A form where the patient selects a provider (by email), chooses allowed fields (e.g. “blood_type”, “allergies”), sets a duration/expiration, and grants “read” access.  This issues a grant and POSTs to the backend (e.g. `/api/access/grant`).
  - **View Records:** A table or list of the patient’s records (record ID, creation date, metadata).  Each record entry has a “View Details” or “Download” button. Clicking it calls `/api/ephr/<record_id>` via REST with JWT; the server will handle decryption (by orchestrating threshold decryption servers) and return the plaintext fields (only those allowed). 
  - **Audit Log:** A page listing the patient’s audit trail entries (from the backend `/api/audit?patient_id=...`), showing actions (upload, grant, access, revoke) with timestamps and status. 
- **Doctor/Provider Dashboard:** After login, a doctor sees:
  - **Accessible Records:** A list of patients who have granted them access, with links to their specific fields.  The doctor can click a record to request decryption. The frontend should send `/api/ephr/<record_id>` (with JWT). The backend checks the grant and if allowed, performs distributed decryption (as below).
  - **Request Access:** (Optional) If implemented, a page where a doctor can request access to a patient’s records (triggering an access request workflow).
  - **Denied Access Handling:** If access is denied (no grant or expired), display an error message.
- **General UI Features:** Use forms with validation, clear buttons, and navigation menu (e.g. header nav bar). Provide **field-level masking**: only show data fields the user is permitted to see (fine-grained control【12†L27-L35】). Example: a patient might hide the billing or insurance fields from a doctor. Ensure each page calls the corresponding backend endpoints securely (use HTTPS in deployment).

## Backend Architecture
- **Tech Stack:** Use **Python 3** with the **Flask** web framework for the REST API. Organize the code into modules mirroring the project spec:
  - `src/crypto/` for cryptography: 
    - `identity_based_encryption.py`: Implement Boneh–Franklin IBE (setup, extract key, encrypt, decrypt). Use Python’s `cryptography` library or similar. You may simulate pairings by hashing concatenated points as in reference code.
    - `shamir_secret_sharing.py`: Implement (k,n)-threshold secret sharing over a prime field (generate polynomial, distribute shares, Lagrange interpolation). Follow Shamir’s scheme【3†L137-L144】.
    - `distributed_decryption.py`: Manage a cluster of *n* decryption servers. Each server holds one share of the IBE private key; upon a decrypt request, *k* servers compute partial decryptions and return shares, which the coordinator combines.
  - `src/core/` for application logic:
    - `ephr_system.py`: Core class managing EPHR records, access grants, audit logs. Methods for `store_ephr()`, `get_ephr()`, `grant_access()`, `check_access()`, `revoke_access()`, `decrypt_with_distribution()`, and audit logging. See **IBDDS core example** above for dataclasses `EPHRRecord`, `AccessGrant`, `AuditLogEntry` and SQLite schemas.
    - `access_control.py`: (If separate) enforce fine-grained policies (check grant’s fields and types).
    - `audit_log.py`: Manage logging entries (storing them to DB after each action).
  - `src/api/` for the REST API:
    - `server.py`: Flask app configuration, blueprint registration.
    - `auth_handler.py`: JWT authentication (login endpoint, token verification for protected routes).
    - `routes.py`: Define endpoints:
      - `POST /api/register` – create patient/doctor user (hash password, store user).
      - `POST /api/login` – verify credentials, return JWT.
      - `POST /api/ephr/upload` – accept JSON health data (from a patient), encrypt with IBE under patient’s identity, store ciphertext in DB (`ephr_records`).
      - `GET  /api/ephr/records` – list record IDs for current user (if patient, their own records; if doctor, records they have access to).
      - `GET  /api/ephr/<id>` – retrieve/decrypt a specific record. Backend should verify JWT, check if accessor has an active grant for that record’s patient and fields, then perform distributed decryption and return plaintext (only allowed fields).
      - `POST /api/access/grant` – create a new grant (patient grants doctor). Store in `access_grants` table.
      - `POST /api/access/revoke` – revoke an existing grant.
      - `GET  /api/audit` – retrieve audit log entries (support query by patient ID, accessor, or all for admin).
  - `src/utils/`:
    - `security.py`: Utilities for password hashing, JWT token creation/verification (e.g. use PyJWT and secure secret key).
    - `logger.py`: Configure Python logging to file (JSON format preferred as in config). 
- **Authentication & Authorization:** Use JWT tokens (with a strong secret from config) for stateless auth. Protect all record/grant endpoints so only authenticated patients/doctors can use them. Validate user roles so that, for example, only a patient can call `/api/access/grant` for their own records, and only the doctor they designated can decrypt.
- **Example Data Flow:** Follow the system diagrams (similar to the Visual Guide):  
  1. **Setup**: On server start, run IBE setup to create master public parameters and master secret. Perform Shamir setup to generate n shares of the decryption key (e.g. a (k=3, n=5) scheme) and assign to simulated servers.  
  2. **Patient Upload**: Patient app encrypts their data under IBE and sends to `/api/ephr/upload`. Backend stores ciphertext blob and metadata, and logs `record_encrypted_and_stored`.  
  3. **Grant Access**: Patient uses `/api/access/grant` to allow a doctor specific fields and duration. Backend checks validity (e.g. self-grant, not expired), stores in DB, logs `access_granted`.  
  4. **Access & Decrypt**: Doctor calls `/api/ephr/<id>` with JWT. Backend calls `check_access()`: verifies a valid grant (not revoked/expired, matching fields/type). If approved, the distributed decryption protocol runs: it fetches the ciphertext from DB, requests *k* shares from decryption nodes (or simulates them locally), Lagrange-combines them to recover the IBE private key effect, then decrypts to plaintext. Only fields granted are returned. Log `access_checked` and `record_decrypted`. 

## Database Schema
- Use a relational database (SQLite for simplicity, or PostgreSQL). Define these tables (via SQLAlchemy ORM or raw SQL):
  - **Users**: `(id, email, password_hash, role)` where `role` ∈ {“patient”, “doctor”}. Emails are unique IDs.
  - **ephr_records**: `(record_id TEXT PK, patient_id FK -> Users, ciphertext BLOB, created_at, updated_at, encrypted BOOL, encryption_algorithm TEXT, metadata JSON)`. Store the IBE ciphertext parts (U, θ) in one BLOB or separate columns.
  - **access_grants**: `(grant_id TEXT PK, patient_id FK, accessor_id FK (doctor), access_types JSON, resource_fields JSON, granted_at, expires_at, revoked BOOL, revoked_at)`. Access types could be JSON ["read"], etc., resource_fields e.g. ["blood_type","allergies"].
  - **audit_logs**: `(entry_id TEXT PK, timestamp, action, actor_id, patient_id, resource_id, status, details JSON)`. Record every action (upload, grant, check, revoke).
  - **(Optional) MasterKeys**: Store IBE system parameters (public) and Shamir shares (securely).
- **Seed Data:** Include an initial script or migration to populate:
  - A sample patient (e.g. `patient@hospital.com`, password), and a sample doctor (e.g. `dr.smith@hospital.com`).
  - Encrypt a sample health record for the patient (e.g. `{"name":"John Doe","age":45,"blood_type":"O+","allergies":["Penicillin"]}`) and insert into `ephr_records`.
  - Create an example access grant (blood type and allergies) from patient to doctor, valid for e.g. 30 days.
  - These can be in a seed SQL script or JSON file loaded on startup.
- **Data Access Libraries:** Use Flask SQLAlchemy or peewee for ORM, or use raw `sqlite3` calls as in the example code. Ensure to `commit()` after inserts.

## Security and Cryptography
- **IBE Implementation:** In `src/crypto/identity_based_encryption.py`, implement the four Boneh-Franklin algorithms (Setup, Extract, Encrypt, Decrypt). The public parameters include generators in G1/G2 and hashes H1–H4. For example, you may simulate curve points and pairings by hashing (per the reference)【7†L231-L237】. On `Encrypt(patientID, plaintext)`, hash the patient’s email to a curve point Q_ID, choose random `r`, compute `U = rP`, compute pairing `g_ID^r = e(Q_ID, P_pub)^r`, derive one-time pad `θ = H3(H2(g_ID^r)) XOR plaintext`.  Store `(U,θ)`. On `Decrypt(privateKey, (U,θ))`, compute `g_ID = e(d_ID, U)` and recover plaintext by XOR. Always validate an authentication tag (e.g. H4) to detect tampering.
- **Threshold Decryption:** In `src/crypto/distributed_decryption.py`, implement a `(k,n)` threshold decryption. During system init, use Shamir’s Secret Sharing to split the master decryption key `d_ID` into `n` shares `s_i`【3†L137-L144】. Assign each share to a virtual “server.” On decrypt request, gather any *k* partial decryptions: each server computes `R_i = U^(s_i)` and returns it. Combine via Lagrange interpolation: `R = ∏(R_i^λ_i)` where λ_i are computed mod p, to recover `U^d_ID`. Finally derive plaintext as above. Verify zero-knowledge proofs if implementing (optional for a demo). Ensure *any* set of *k* shares works, but `<k` gives no info【3†L137-L144】.
- **Fine-Grained Access Control:** Before decrypting or returning data, enforce policies per the grant:
  - Check the grant exists for `patient_id = record.patient_id` and `accessor_id = current_user`.
  - Verify `now < expires_at` and `revoked == false`.
  - Confirm the requested access type (“read”) is in `access_types`.
  - When returning the record, filter out any JSON fields not in `resource_fields`. For example, if a doctor was only granted “blood_type” and “allergies,” omit all other fields from the response. This field-level filtering satisfies **fine-grained access control**【12†L27-L35】.
- **Audit Logging:** In each core method (`store_ephr`, `grant_access`, `check_access`, `revoke_access`), log an entry. Include `actor_id` (who performed it), `patient_id`, `resource_id` (record or grant), `action` (“record_encrypted_and_stored”, “access_granted”, “access_check”, etc.), `status` (success/denied), and any details (e.g. reason for denial). Store these in the `audit_logs` table. This ensures HIPAA-compliant logging of all sensitive events.
- **Security Best Practices:** Store passwords securely (use salted hashing, e.g. bcrypt). Protect JWT secret (do not hard-code). Use HTTPS in deployment. Sanitize all inputs. Follow [OWASP guidelines](https://owasp.org) for web security.

## Deployment & Miscellaneous
- **Environment & Config:** Use a `config/system_config.json` to hold parameters: database URI, JWT secret, IBE parameters (prime p, generator P, public key), threshold values (n,k), and logging config. Provide a template in the repo.
- **Containerization:** Include a `Dockerfile` (e.g. based on `python:3.10`) that installs dependencies from `requirements.txt` and runs the Flask server. Provide a `docker-compose.yml` to launch the API and a database (if using Postgres). Ensure volumes for persistent storage and a restart policy.
- **Testing:** Write unit tests (using `pytest`) for key functionality: IBE encryption/decryption correctness, Shamir share reconstruction, access control logic. Place tests in a `tests/` folder (`test_crypto.py`, `test_access_control.py`, `test_integration.py`). Use these to validate the implementation. 
- **Documentation:** Prepare a `README.md` summarizing features and setup instructions. Document API endpoints (or generate via Swagger). Include comments in code for clarity. Optionally add an `API_DOCUMENTATION.md` under `docs/`.

**Full Prompt:** Using the above details, instruct Antigravity with a single comprehensive prompt. For example:

```
Build a complete "Identity-Based Distributed Decryption Scheme (IBDDS) for Secure EPHR Sharing" web application. Use **Python/Flask** for the backend API and a modern **React** (or similar) front end. The system must use **Identity-Based Encryption (IBE)** (Boneh-Franklin scheme) so that a user’s email is their public key【5†L125-L132】【7†L231-L237】. Implement a **(k,n) threshold cryptosystem**: split each patient’s IBE private key with Shamir’s secret sharing and require k servers to collaborate to decrypt【3†L137-L144】【9†L123-L131】. 

Front-end: Design pages for user registration/login (roles patient/doctor), patient dashboard (upload record, manage grants, view records), and doctor dashboard (view granted patient fields). Use form validation and display data only for allowed fields (fine-grained access control【12†L27-L35】). Example: Patient can grant Dr. Smith read access to "blood_type" and "allergies" fields of her EPHR, which should be the only fields Dr. Smith sees. Provide a user-friendly UI with navigation, forms to enter JSON health data, select fields, set durations, and tables for records and audit logs. 

Back-end: Implement these models and endpoints:
- **Users table:** (id, email, hashed_password, role).
- **ephr_records:** (record_id, patient_id, ciphertext, created_at, updated_at, metadata).
- **access_grants:** (grant_id, patient_id, accessor_id, access_types, resource_fields, granted_at, expires_at, revoked).
- **audit_logs:** (entry_id, timestamp, action, actor_id, patient_id, resource_id, status, details).
Use Flask routes to support `/register`, `/login` (return JWT), `/api/ephr/upload` (encrypt & store), `/api/ephr/<id>` (decrypt and return allowed data), `/api/access/grant`, `/api/access/revoke`, and `/api/audit`. Use JWT auth to protect routes. 

Crypto: In Python, code the IBE scheme (setup, extract keys, encrypt, decrypt) and Shamir's secret sharing (split and combine). On record upload, encrypt the patient’s data under their identity; on access, verify grants then run threshold decryption (using any k of n shares) to recover the record【3†L137-L144】. Enforce that no single server can decrypt alone. 

Ensure audit logging of every action for HIPAA compliance. Include deployment setup: a Dockerfile, docker-compose (with the Flask app and database), and environment configuration (use secure JWT secret, set threshold parameters, etc.). 

Finally, seed the database with one sample patient (with an example EPHR record) and one doctor with a grant, so the app has initial data. Provide unit tests for encryption, decryption, and access logic. 
```

This prompt includes all details: **frontend pages and design**, **backend modules and endpoints**, **database schema**, **cryptography implementation (IBE & threshold)**, **access control and logging**, and **deployment** (Docker). When given to Antigravity, it should produce a fully structured project as specified above. 

**Sources:** We drew on standard IBE and threshold cryptography concepts【5†L125-L132】【7†L231-L237】【3†L137-L144】【9†L123-L131】 and fine-grained PHI access control practices【12†L27-L35】 to guide the implementation. Each requirement above is grounded in the project’s design specification and these cryptographic principles.