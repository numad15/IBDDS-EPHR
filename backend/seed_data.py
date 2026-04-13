"""
Massive Database Seed Script

Seeds the database with:
- 100 patients with diverse health records
- 40 doctors across different specialties
- Access grants linking doctors to patients
- All records encrypted with IBE and protected by 3-of-5 threshold
"""

import os
import sys
import json
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.server import create_app
from src.utils.security import hash_password

# ==================== DATA POOLS ====================

FIRST_NAMES = [
    "Aarav", "Aditi", "Aisha", "Akash", "Amara", "Amir", "Ananya", "Arjun", "Avery", "Benjamin",
    "Carlos", "Charlotte", "Daniel", "Deepa", "Elena", "Ethan", "Fatima", "Gabriella", "Hannah", "Hassan",
    "Isabella", "James", "Jasmine", "Joshua", "Kavya", "Liam", "Lily", "Lucas", "Meera", "Mohammed",
    "Nadia", "Nathan", "Olivia", "Omar", "Priya", "Rahul", "Rebecca", "Rohan", "Sakura", "Samuel",
    "Sara", "Sophia", "Tanvi", "Thomas", "Uma", "Victor", "William", "Yuki", "Zara", "Zoe",
    "Aiden", "Brooke", "Caleb", "Diana", "Eric", "Fiona", "George", "Helen", "Ian", "Julia",
    "Kevin", "Laura", "Michael", "Nina", "Oscar", "Patricia", "Quinn", "Rachel", "Steven", "Tara",
    "Uma", "Vanessa", "Walter", "Xavier", "Yasmin", "Zachary", "Alice", "Brian", "Clara", "David",
    "Emily", "Frank", "Grace", "Henry", "Iris", "Jack", "Katherine", "Leo", "Maria", "Noah",
    "Olive", "Peter", "Rosa", "Simon", "Tina", "Umar", "Violet", "Wayne", "Xena", "Yolanda"
]

LAST_NAMES = [
    "Patel", "Sharma", "Johnson", "Williams", "Brown", "Garcia", "Martinez", "Chen", "Kim", "Singh",
    "Nguyen", "Ali", "Kumar", "Davis", "Rodriguez", "Wilson", "Anderson", "Thomas", "Jackson", "White",
    "Harris", "Martin", "Thompson", "Moore", "Taylor", "Lee", "Walker", "Hall", "Allen", "Young",
    "King", "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Rivera", "Campbell",
    "Mitchell", "Roberts", "Carter", "Turner", "Phillips", "Evans", "Edwards", "Collins", "Stewart", "Morris"
]

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

MEDICATIONS = [
    "Lisinopril", "Metformin", "Atorvastatin", "Levothyroxine", "Amlodipine",
    "Omeprazole", "Losartan", "Albuterol", "Gabapentin", "Hydrochlorothiazide",
    "Sertraline", "Metoprolol", "Pantoprazole", "Furosemide", "Montelukast",
    "Escitalopram", "Rosuvastatin", "Tamsulosin", "Prednisone", "Ibuprofen",
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Doxycycline", "Insulin Glargine",
    "Aspirin", "Warfarin", "Clopidogrel", "Duloxetine", "Venlafaxine"
]

ALLERGIES = [
    "Penicillin", "Sulfa drugs", "Aspirin", "Ibuprofen", "Codeine",
    "Latex", "Peanuts", "Shellfish", "Bee stings", "Egg",
    "Soy", "Wheat/Gluten", "Milk/Lactose", "Tree nuts", "Sesame",
    "Morphine", "Tetracycline", "ACE inhibitors", "NSAIDs", "Contrast dye",
    "None"
]

CONDITIONS = [
    "Hypertension", "Type 2 Diabetes", "Asthma", "GERD", "Hypothyroidism",
    "Depression", "Anxiety", "Osteoarthritis", "Chronic Back Pain", "Migraine",
    "High Cholesterol", "Obesity", "Sleep Apnea", "COPD", "Atrial Fibrillation",
    "Chronic Kidney Disease", "Rheumatoid Arthritis", "Psoriasis", "Epilepsy", "Anemia",
    "Heart Failure", "Coronary Artery Disease", "Osteoporosis", "Gout", "IBS",
    "Celiac Disease", "Crohn's Disease", "Lupus", "Multiple Sclerosis", "Parkinson's Disease"
]

INSURANCE_PROVIDERS = [
    "BlueCross BlueShield", "Aetna", "UnitedHealth", "Cigna", "Humana",
    "Kaiser Permanente", "Anthem", "Centene", "Molina Healthcare", "WellCare",
    "Amerihealth", "Highmark", "Independence Blue Cross", "Medica", "Priority Health"
]

DOCTOR_SPECIALTIES = [
    "General Practice", "Internal Medicine", "Cardiology", "Endocrinology", "Neurology",
    "Pulmonology", "Gastroenterology", "Rheumatology", "Dermatology", "Orthopedics",
    "Oncology", "Nephrology", "Psychiatry", "Ophthalmology", "Urology",
    "Pediatrics", "Geriatrics", "Hematology", "Immunology", "Emergency Medicine"
]

HOSPITAL_DOMAINS = [
    "cityhospital.com", "metrohealth.org", "regionalmed.com", "university-medical.edu",
    "communityhealth.org", "generalhospital.com", "medcenter.org", "healthsystem.com",
    "apollohealth.com", "medplus.org"
]

EMERGENCY_CONTACTS = [
    "Spouse", "Parent", "Sibling", "Child", "Friend", "Partner", "Guardian", "Neighbor"
]

# Demo accounts that match the README quick-start credentials
DEMO_USERS = [
    {"email": "patient@hospital.com", "password": "patient123", "role": "patient", "name": "Demo Patient"},
    {"email": "dr.smith@hospital.com", "password": "doctor123", "role": "doctor", "name": "Dr. Smith"},
    {"email": "dr.jones@hospital.com", "password": "doctor123", "role": "doctor", "name": "Dr. Jones"},
]


def ensure_demo_accounts(system, results):
    """Create baseline demo users/records so the app has data immediately."""
    log("Ensuring demo accounts exist...")
    for demo in DEMO_USERS:
        try:
            existing = system.get_user_by_email(demo["email"])
            if existing:
                user_id = existing["id"]
            else:
                user_id = system.register_user(
                    demo["email"], hash_password(demo["password"]), demo["role"]
                )
            results["demo_users"].append({
                "id": user_id,
                "email": demo["email"],
                "password": demo["password"],
                "role": demo["role"],
                "name": demo["name"]
            })
        except Exception as e:
            results["errors"].append(f"Demo user {demo['email']}: {e}")

    # Add a simple health record for the demo patient and grant access to Dr. Smith
    demo_patient = system.get_user_by_email("patient@hospital.com")
    if demo_patient:
        try:
            existing_records = system.get_patient_records(demo_patient["id"])
            if not existing_records:
                sample_record = {
                    "name": "Demo Patient",
                    "age": 32,
                    "blood_type": "O+",
                    "allergies": ["Peanuts"],
                    "conditions": ["Hypertension"],
                    "medications": ["Lisinopril"],
                    "last_checkup": "2026-03-10"
                }
                record_id = system.store_ephr(demo_patient["id"], sample_record)
                results["records"].append({
                    "record_id": record_id,
                    "patient_id": demo_patient["id"],
                    "patient_email": demo_patient["email"],
                    "fields": list(sample_record.keys())
                })
        except Exception as e:
            results["errors"].append(f"Demo patient record: {e}")

        # Grant demo doctor access if not already granted
        demo_doctor = system.get_user_by_email("dr.smith@hospital.com")
        if demo_doctor:
            try:
                existing_grants = system.access_control.get_grants_for_patient(demo_patient["id"])
                already = any(g.get("accessor_email") == demo_doctor["email"] for g in existing_grants)
                if not already:
                    grant_id = system.grant_access(
                        patient_id=demo_patient["id"],
                        accessor_email=demo_doctor["email"],
                        access_types=["read"],
                        resource_fields=["name", "blood_type", "allergies", "conditions", "medications"],
                        duration_days=365
                    )
                    results["grants"].append({
                        "grant_id": grant_id,
                        "patient": demo_patient["email"],
                        "doctor": demo_doctor["email"],
                        "fields": ["name", "blood_type", "allergies", "conditions", "medications"],
                        "duration_days": 365
                    })
            except Exception as e:
                results["errors"].append(f"Demo grant: {e}")


def generate_patient_data(index, first_name, last_name):
    """Generate realistic health data for a patient."""
    age = random.randint(18, 85)
    num_meds = random.randint(0, 5)
    num_allergies = random.randint(0, 3)
    num_conditions = random.randint(0, 4)

    meds = random.sample(MEDICATIONS, min(num_meds, len(MEDICATIONS)))
    allergy_list = random.sample(ALLERGIES, min(num_allergies, len(ALLERGIES)))
    if "None" in allergy_list and len(allergy_list) > 1:
        allergy_list.remove("None")
    condition_list = random.sample(CONDITIONS, min(num_conditions, len(CONDITIONS)))

    insurance = random.choice(INSURANCE_PROVIDERS)
    policy_num = f"POL{random.randint(100000, 999999)}"

    contact_rel = random.choice(EMERGENCY_CONTACTS)
    contact_name = f"{random.choice(FIRST_NAMES)} {last_name}"
    contact_phone = f"({random.randint(200,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}"

    return {
        "name": f"{first_name} {last_name}",
        "age": age,
        "blood_type": random.choice(BLOOD_TYPES),
        "medications": meds if meds else ["None"],
        "allergies": allergy_list if allergy_list else ["None"],
        "conditions": condition_list if condition_list else ["Healthy"],
        "emergency_contact": f"{contact_name} ({contact_rel}) - {contact_phone}",
        "insurance": f"{insurance} - {policy_num}",
        "weight_kg": round(random.uniform(45.0, 120.0), 1),
        "height_cm": random.randint(150, 195),
        "heart_rate_bpm": random.randint(55, 100),
        "blood_pressure": f"{random.randint(90, 160)}/{random.randint(60, 100)}",
        "last_checkup": f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    }


def seed_massive_database():
    """Seed the database with demo accounts plus 100 patients and 40 doctors."""
    app = create_app()
    system = app.ephr_system

    results = {
        "patients": [],
        "doctors": [],
        "records": [],
        "grants": [],
        "demo_users": [],
        "errors": []
    }

    # Ensure quick-start demo accounts and sample data
    ensure_demo_accounts(system, results)

    # ==================== CREATE 100 PATIENTS ====================
    log("Creating 100 patients...")
    for i in range(100):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[i % len(LAST_NAMES)]
        email = f"{first.lower()}.{last.lower()}{i+1}@patient.hospital.com"
        password = f"patient{i+1:03d}"

        try:
            existing = system.get_user_by_email(email)
            if existing:
                patient_id = existing['id']
            else:
                patient_id = system.register_user(email, hash_password(password), "patient")

            results["patients"].append({
                "id": patient_id,
                "email": email,
                "password": password,
                "name": f"{first} {last}"
            })

            if (i + 1) % 10 == 0:
                log(f"  Created {i+1}/100 patients")
        except Exception as e:
            results["errors"].append(f"Patient {email}: {e}")

    # ==================== CREATE 40 DOCTORS ====================
    log("Creating 40 doctors...")
    for i in range(40):
        first = FIRST_NAMES[(i + 50) % len(FIRST_NAMES)]
        last = LAST_NAMES[(i + 25) % len(LAST_NAMES)]
        specialty = DOCTOR_SPECIALTIES[i % len(DOCTOR_SPECIALTIES)]
        domain = HOSPITAL_DOMAINS[i % len(HOSPITAL_DOMAINS)]
        email = f"dr.{first.lower()}.{last.lower()}@{domain}"
        password = f"doctor{i+1:03d}"

        try:
            existing = system.get_user_by_email(email)
            if existing:
                doctor_id = existing['id']
            else:
                doctor_id = system.register_user(email, hash_password(password), "doctor")

            results["doctors"].append({
                "id": doctor_id,
                "email": email,
                "password": password,
                "name": f"Dr. {first} {last}",
                "specialty": specialty
            })

            if (i + 1) % 10 == 0:
                log(f"  Created {i+1}/40 doctors")
        except Exception as e:
            results["errors"].append(f"Doctor {email}: {e}")

    # ==================== CREATE HEALTH RECORDS FOR ALL PATIENTS ====================
    log("Creating encrypted health records for all 100 patients...")
    for i, patient in enumerate(results["patients"]):
        try:
            first = patient["name"].split()[0]
            last = patient["name"].split()[-1]
            health_data = generate_patient_data(i, first, last)
            
            # Check if records already exist
            existing_records = system.get_patient_records(patient["id"])
            if existing_records:
                record_id = existing_records[0]["record_id"]
            else:
                record_id = system.store_ephr(patient["id"], health_data)

            results["records"].append({
                "record_id": record_id,
                "patient_id": patient["id"],
                "patient_email": patient["email"],
                "fields": list(health_data.keys())
            })

            if (i + 1) % 20 == 0:
                log(f"  Encrypted {i+1}/100 records (IBE + 3-of-5 threshold)")
        except Exception as e:
            results["errors"].append(f"Record for {patient['email']}: {e}")

    # ==================== CREATE ACCESS GRANTS ====================
    log("Creating access grants (doctors <-> patients)...")
    
    # Field combinations for different grant types
    FIELD_SETS = [
        ["blood_type", "allergies"],
        ["blood_type", "allergies", "medications"],
        ["name", "age", "blood_type", "conditions"],
        ["blood_type", "medications", "conditions", "allergies"],
        ["name", "age", "blood_type", "medications", "allergies", "conditions"],
        ["blood_type", "heart_rate_bpm", "blood_pressure"],
        ["name", "blood_type", "allergies", "emergency_contact"],
        ["all"],  # full access
    ]

    DURATION_OPTIONS = [7, 14, 30, 60, 90, 180, 365]
    
    grant_count = 0

    # Strategy: Each doctor gets 5-15 patient grants
    for doc_idx, doctor in enumerate(results["doctors"]):
        num_patients = random.randint(5, 15)
        patient_indices = random.sample(range(len(results["patients"])), min(num_patients, len(results["patients"])))

        for pat_idx in patient_indices:
            patient = results["patients"][pat_idx]
            fields = random.choice(FIELD_SETS)
            duration = random.choice(DURATION_OPTIONS)

            try:
                grant_id = system.grant_access(
                    patient_id=patient["id"],
                    accessor_email=doctor["email"],
                    access_types=["read"],
                    resource_fields=fields,
                    duration_days=duration
                )
                results["grants"].append({
                    "grant_id": grant_id,
                    "patient": patient["email"],
                    "doctor": doctor["email"],
                    "fields": fields,
                    "duration_days": duration
                })
                grant_count += 1
            except Exception as e:
                results["errors"].append(f"Grant {patient['email']}->{doctor['email']}: {e}")

        if (doc_idx + 1) % 10 == 0:
            log(f"  Processed grants for {doc_idx+1}/40 doctors ({grant_count} grants total)")

    # ==================== SUMMARY ====================
    log("")
    log("=" * 60)
    log(" SEED COMPLETE!")
    log("=" * 60)
    log(f" Demo users ensured: {len(results['demo_users'])}")
    log(f" Patients created:  {len(results['patients'])}")
    log(f" Doctors created:   {len(results['doctors'])}")
    log(f" Records encrypted: {len(results['records'])}")
    log(f" Access grants:     {len(results['grants'])}")
    log(f" Errors:            {len(results['errors'])}")
    log("=" * 60)

    # Write detailed results to file
    summary = {
        "total_demo_users": len(results["demo_users"]),
        "total_patients": len(results["patients"]),
        "total_doctors": len(results["doctors"]),
        "total_records": len(results["records"]),
        "total_grants": len(results["grants"]),
        "total_errors": len(results["errors"]),
        "sample_patients": results["patients"][:5],
        "sample_doctors": results["doctors"][:5],
        "demo_users": results["demo_users"],
        "errors": results["errors"][:20]
    }

    with open("seed_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    log(f" Results written to seed_results.json")

    # Write credentials file for easy reference
    with open("credentials.txt", "w", encoding="utf-8") as f:
        f.write("IBDDS EPHR System - Login Credentials\n")
        f.write("=" * 60 + "\n\n")

        f.write("DEMO USERS:\n")
        f.write("-" * 40 + "\n")
        for u in results["demo_users"]:
            f.write(f"  {u['email']} / {u['password']} ({u['role']})\n")
        f.write("\n")

        f.write("PATIENTS (100):\n")
        f.write("-" * 40 + "\n")
        for p in results["patients"]:
            f.write(f"  {p['email']} / {p['password']}\n")
        f.write(f"\nDOCTORS (40):\n")
        f.write("-" * 40 + "\n")
        for d in results["doctors"]:
            f.write(f"  {d['email']} / {d['password']} ({d['specialty']})\n")

    log(f" Credentials written to credentials.txt")
    return results


def log(msg):
    """Log to both console and file."""
    with open("seed_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


if __name__ == "__main__":
    try:
        # Clear log
        with open("seed_log.txt", "w") as f:
            f.write("")
        seed_massive_database()
    except Exception as e:
        import traceback
        with open("seed_trace.log", "w") as f:
            traceback.print_exc(file=f)
        sys.exit(1)
