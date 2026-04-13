# ðŸ›¡ï¸ IBDDS EPHR System

**Identity-Based Distributed Decryption Scheme for Secure Electronic Personal Health Record Sharing**

A full-stack web application combining Identity-Based Encryption (IBE) with threshold cryptography and fine-grained access control for secure health record management.

---

## ðŸŒŸ Features

- **Identity-Based Encryption (IBE)** â€” Boneh-Franklin scheme where email = public key
- **Threshold Decryption (3-of-5)** â€” Shamir's Secret Sharing ensures no single point of failure
- **Fine-Grained Access Control** â€” Patients grant doctors access to specific fields only
- **HIPAA-Compliant Audit Logging** â€” Every action is tracked and auditable
- **Role-Based Dashboards** â€” Separate Patient and Doctor interfaces
- **JWT Authentication** â€” Stateless, secure authentication

## ðŸ—ï¸ Architecture

```
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ crypto/             # IBE, Shamir's, Distributed Decryption
â”‚   â”‚   â”œâ”€â”€ core/               # EPHR system, Access Control, Audit
â”‚   â”‚   â”œâ”€â”€ api/                # Flask routes, auth, server
â”‚   â”‚   â””â”€â”€ utils/              # Security, logging utilities
â”‚   â”œâ”€â”€ config/                 # System configuration
â”‚   â”œâ”€â”€ tests/                  # Unit & integration tests
â”‚   â””â”€â”€ seed_data.py            # Database seeding
â”‚
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ pages/              # Login, Register, Patient/Doctor Dashboards
â”‚   â”‚   â”œâ”€â”€ services/           # API service layer
â”‚   â”‚   â””â”€â”€ index.css           # Premium dark design system
â”‚   â””â”€â”€ index.html
â”‚
â”œâ”€â”€ docker-compose.yml
â””â”€â”€ README.md
```

## ðŸš€ Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python seed_data.py              # Seed database with sample data
python -m src.api.server         # Start Flask API on port 5000
```

### Frontend Setup

```bash
cd frontend
npm install
# Optional: point SPA to a different backend
# echo "VITE_API_BASE=http://localhost:5000/api" > .env
npm run dev                      # Start Vite dev server on port 3000
```

### Default Credentials

| Role    | Email                  | Password    |
|---------|------------------------|-------------|
| Patient | patient@hospital.com   | patient123  |
| Doctor  | dr.smith@hospital.com  | doctor123   |
| Doctor  | dr.jones@hospital.com  | doctor123   |

## ðŸ” Security Architecture

### Identity-Based Encryption (IBE)
- User's email serves as their public key (no certificate infrastructure needed)
- Based on the simulated Boneh-Franklin pairing-based scheme
- Records are encrypted client-side before storage

### Threshold Decryption
- Master key is split into 5 shares using Shamir's Secret Sharing
- Minimum 3 shares required to decrypt (configurable)
- No single server can decrypt alone

### Access Control
- **Field-level granularity**: e.g., grant access to only `blood_type` and `allergies`
- **Temporal validity**: grants expire after a set duration
- **Revocable**: patients can revoke access at any time

## ðŸ“¡ API Endpoints

| Method | Endpoint              | Description                    | Auth  |
|--------|-----------------------|--------------------------------|-------|
| POST   | `/api/register`       | Register new user              | No    |
| POST   | `/api/login`          | Login, get JWT                 | No    |
| POST   | `/api/ephr/upload`    | Encrypt & store health record  | JWT   |
| GET    | `/api/ephr/records`   | List user's records            | JWT   |
| GET    | `/api/ephr/<id>`      | Decrypt & retrieve record      | JWT   |
| POST   | `/api/access/grant`   | Grant field-level access       | JWT   |
| POST   | `/api/access/revoke`  | Revoke an access grant         | JWT   |
| GET    | `/api/access/grants`  | List access grants             | JWT   |
| GET    | `/api/audit`          | Get audit log entries          | JWT   |
| GET    | `/api/doctors`        | List registered doctors        | JWT   |
| GET    | `/api/system/status`  | System & cluster status        | JWT   |

## ðŸ§ª Testing

```bash
cd backend
python -m pytest tests/ -v
```

## ðŸ³ Docker

```bash
docker-compose up --build
```

- Backend: http://localhost:5000
- Frontend: http://localhost:3000
- Compose builds the SPA with `VITE_API_BASE=http://backend:5000/api` so API calls reach the backend service.

## ðŸ“„ License

Academic project â€” for educational and research purposes.
