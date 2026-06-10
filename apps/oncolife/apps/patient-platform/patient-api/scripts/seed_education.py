"""
Education Content Seeding Script.

This script seeds the database with:
1. Symptom catalog (from existing symptom definitions)
2. Mandatory disclaimer
3. Sample education documents (for development)

Production Use:
- Run once during initial deployment
- Education documents should be loaded from S3/clinician sources
- Disclaimer should never be modified after seeding

Usage:
    python scripts/seed_education.py
    
    # Or with environment:
    DATABASE_URL=postgresql://... python scripts/seed_education.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models.education import (
    Symptom,
    EducationDocument,
    Disclaimer,
    CareTeamHandout,
    get_default_disclaimer,
    get_symptom_catalog,
    Base,
)
from core.config import settings


def create_db_session():
    """Create database session."""
    database_url = os.getenv("DATABASE_URL", str(settings.patient_database_url))
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine


def seed_symptoms(session):
    """Seed symptom catalog."""
    print("Seeding symptoms...")
    
    catalog = get_symptom_catalog()
    
    for i, symptom_data in enumerate(catalog):
        existing = session.query(Symptom).filter(
            Symptom.code == symptom_data["code"]
        ).first()
        
        if not existing:
            symptom = Symptom(
                code=symptom_data["code"],
                name=symptom_data["name"],
                category=symptom_data["category"],
                display_order=i,
                active=True,
            )
            session.add(symptom)
            print(f"  Added: {symptom_data['code']} - {symptom_data['name']}")
        else:
            print(f"  Exists: {symptom_data['code']}")
    
    session.commit()
    print(f"Symptoms seeded: {len(catalog)}")


def seed_disclaimer(session):
    """Seed mandatory disclaimer."""
    print("Seeding disclaimer...")
    
    disclaimer_data = get_default_disclaimer()
    
    existing = session.query(Disclaimer).filter(
        Disclaimer.id == disclaimer_data["id"]
    ).first()
    
    if not existing:
        disclaimer = Disclaimer(
            id=disclaimer_data["id"],
            text=disclaimer_data["text"],
            active=disclaimer_data["active"],
            version=disclaimer_data["version"],
        )
        session.add(disclaimer)
        session.commit()
        print(f"  Added: {disclaimer_data['id']}")
    else:
        print(f"  Exists: {disclaimer_data['id']}")


def seed_care_team_handout(session):
    """Seed care team handout."""
    print("Seeding care team handout...")
    
    existing = session.query(CareTeamHandout).filter(
        CareTeamHandout.is_current == True
    ).first()
    
    if not existing:
        handout = CareTeamHandout(
            title="Care Team Information",
            inline_summary="""
• Your oncology care team is here to help you
• Call us if you experience any concerning symptoms
• We are available 24/7 for urgent concerns
• Follow your treatment plan as prescribed
• Keep all appointments and lab work dates
• Let us know about any new medications
""".strip(),
            s3_pdf_path="care-team/care_team_handout_v1.pdf",
            s3_text_path="care-team/care_team_handout_v1.txt",
            version=1,
            is_current=True,
            source_document_id="CTH-001",
            approved_by="Clinical Team",
            approved_date=date.today(),
        )
        session.add(handout)
        session.commit()
        print("  Added care team handout v1")
    else:
        print(f"  Exists: v{existing.version}")


def seed_sample_education_documents(session):
    """Seed sample education documents for development."""
    print("Seeding sample education documents...")
    
    sample_docs = [
        {
            "symptom_code": "FEVER-101",
            "title": "Managing Fever During Chemotherapy",
            "inline_text": """
• Fever during chemotherapy is serious - call your care team immediately
• Take your temperature if you feel warm or have chills
• A fever of 100.4°F (38°C) or higher needs immediate attention
• Do not take fever-reducing medication without consulting your care team
• Keep a thermometer at home and know how to use it
""".strip(),
            "s3_pdf_path": "symptoms/fever/fever_v1.pdf",
            "source_document_id": "EDU-FEVER-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "NAUSEA-101",
            "title": "Coping with Nausea",
            "inline_text": """
• Take anti-nausea medications as prescribed
• Eat small, frequent meals throughout the day
• Avoid strong odors and greasy foods
• Stay hydrated with small sips of clear fluids
• Ginger tea or ginger candy may help settle your stomach
• Eat bland foods like crackers, toast, or rice
""".strip(),
            "s3_pdf_path": "symptoms/nausea/nausea_v1.pdf",
            "source_document_id": "EDU-NAUSEA-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "FATIGUE-101",
            "title": "Managing Cancer-Related Fatigue",
            "inline_text": """
• Fatigue is one of the most common side effects of chemotherapy
• Balance rest with light activity - short walks can help
• Prioritize your most important activities for when you have energy
• Accept help from family and friends
• Stay hydrated and eat nutritious foods
• Talk to your care team if fatigue is severe
""".strip(),
            "s3_pdf_path": "symptoms/fatigue/fatigue_v1.pdf",
            "source_document_id": "EDU-FATIGUE-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "BLEED-103",
            "title": "Bleeding and Bruising During Treatment",
            "inline_text": """
• Report any unusual bleeding or bruising to your care team
• Use a soft toothbrush and electric razor
• Avoid activities that could cause injury
• Be careful with sharp objects
• If bleeding occurs, apply gentle pressure
• Call immediately for heavy or uncontrolled bleeding
""".strip(),
            "s3_pdf_path": "symptoms/bleeding/bleeding_v1.pdf",
            "source_document_id": "EDU-BLEED-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "PAIN-101",
            "title": "Managing Pain During Treatment",
            "inline_text": """
• Pain should be reported to your care team
• Take pain medications as prescribed
• Keep a pain diary to track patterns
• Non-medication approaches can help: relaxation, heat/cold
• Don't wait until pain is severe to take medication
• Changes in pain should be reported promptly
""".strip(),
            "s3_pdf_path": "symptoms/pain/pain_v1.pdf",
            "source_document_id": "EDU-PAIN-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "DIARRHEA-101",
            "title": "Managing Diarrhea",
            "inline_text": """
• Stay hydrated with clear fluids
• Eat bland, low-fiber foods
• Avoid dairy, caffeine, and fatty foods
• Take anti-diarrhea medication as directed
• Report severe or persistent diarrhea immediately
• Watch for signs of dehydration
""".strip(),
            "s3_pdf_path": "symptoms/diarrhea/diarrhea_v1.pdf",
            "source_document_id": "EDU-DIARRHEA-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "CONSTIPATION-101",
            "title": "Preventing and Managing Constipation",
            "inline_text": """
• Drink plenty of fluids throughout the day
• Eat high-fiber foods when tolerated
• Stay as active as possible
• Take stool softeners as prescribed
• Don't strain during bowel movements
• Report if no bowel movement for 3+ days
""".strip(),
            "s3_pdf_path": "symptoms/constipation/constipation_v1.pdf",
            "source_document_id": "EDU-CONSTIPATION-001",
            "approved_by": "Dr. Clinical Review",
        },
        {
            "symptom_code": "MOUTH-101",
            "title": "Caring for Mouth Sores",
            "inline_text": """
• Rinse mouth gently with salt water or baking soda rinse
• Use a soft-bristled toothbrush
• Avoid spicy, acidic, or rough foods
• Keep lips moisturized
• Avoid alcohol-based mouthwashes
• Report severe mouth sores to your care team
""".strip(),
            "s3_pdf_path": "symptoms/mouth/mouth_v1.pdf",
            "source_document_id": "EDU-MOUTH-001",
            "approved_by": "Dr. Clinical Review",
        },
    ]
    
    for doc_data in sample_docs:
        # Check if symptom exists first
        symptom = session.query(Symptom).filter(
            Symptom.code == doc_data["symptom_code"]
        ).first()
        
        if not symptom:
            print(f"  Skipping {doc_data['symptom_code']} - symptom not found")
            continue
        
        existing = session.query(EducationDocument).filter(
            EducationDocument.source_document_id == doc_data["source_document_id"]
        ).first()
        
        if not existing:
            doc = EducationDocument(
                symptom_code=doc_data["symptom_code"],
                title=doc_data["title"],
                inline_text=doc_data["inline_text"],
                s3_pdf_path=doc_data["s3_pdf_path"],
                s3_text_path=doc_data["s3_pdf_path"].replace(".pdf", ".txt"),
                source_document_id=doc_data["source_document_id"],
                version=1,
                approved_by=doc_data["approved_by"],
                approved_date=date.today(),
                status="active",
                priority=0,
            )
            session.add(doc)
            print(f"  Added: {doc_data['title']}")
        else:
            print(f"  Exists: {doc_data['source_document_id']}")
    
    session.commit()
    print(f"Education documents seeded: {len(sample_docs)}")


def create_tables(engine):
    """Create all education tables."""
    print("Creating education tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


def main():
    """Main seeding function."""
    print("=" * 60)
    print("OncoLife Education Content Seeder")
    print("=" * 60)
    
    session, engine = create_db_session()
    
    try:
        # Create tables if they don't exist
        create_tables(engine)
        
        # Seed in order
        seed_symptoms(session)
        seed_disclaimer(session)
        seed_care_team_handout(session)
        seed_sample_education_documents(session)
        
        print("=" * 60)
        print("Seeding complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()



