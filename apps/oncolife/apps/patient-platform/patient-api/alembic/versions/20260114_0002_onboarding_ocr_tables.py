"""Add onboarding and OCR tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-14

This migration adds tables for:
- providers: Normalized physician/clinic data from OCR
- oncology_profiles: Cancer diagnosis and treatment plan
- medications: Normalized medication list from referrals
- chemo_schedule: Specific chemotherapy appointment dates
- fax_ingestion_log: HIPAA audit trail for fax reception
- ocr_field_confidence: Per-field OCR accuracy scores
- ocr_confidence_thresholds: Configuration for field validation
- Updates to users table: Add emergency contact columns
- Updates to patient_referrals: Add complete OCR field coverage (if exists)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create onboarding and OCR tables."""
    
    # ==========================================================================
    # Update Users Table - Add emergency contact columns
    # ==========================================================================
    op.add_column('users', sa.Column('emergency_contact_name', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('emergency_contact_phone', sa.String(20), nullable=True))
    
    # ==========================================================================
    # Providers Table - Normalized physician/clinic data
    # ==========================================================================
    op.create_table(
        'providers',
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Physician Info
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('npi', sa.String(20), nullable=True),
        sa.Column('specialty', sa.String(100), nullable=True),
        sa.Column('credentials', sa.String(50), nullable=True),
        
        # Clinic Info
        sa.Column('clinic_name', sa.String(255), nullable=True),
        sa.Column('clinic_address', sa.Text(), nullable=True),
        sa.Column('clinic_city', sa.String(100), nullable=True),
        sa.Column('clinic_state', sa.String(50), nullable=True),
        sa.Column('clinic_zip', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('fax', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        
        # Metadata
        sa.Column('source', sa.String(50), server_default='ocr', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('provider_id'),
        sa.UniqueConstraint('npi'),
    )
    op.create_index('ix_providers_npi', 'providers', ['npi'])
    op.create_index('ix_providers_name', 'providers', ['full_name'])
    op.create_index('ix_providers_clinic', 'providers', ['clinic_name'])
    
    # ==========================================================================
    # Oncology Profiles Table - Cancer diagnosis and treatment plan
    # ==========================================================================
    op.create_table(
        'oncology_profiles',
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('referral_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Cancer Diagnosis
        sa.Column('cancer_type', sa.String(255), nullable=True),
        sa.Column('cancer_stage', sa.String(50), nullable=True),
        sa.Column('cancer_grade', sa.String(50), nullable=True),
        sa.Column('cancer_histology', sa.String(255), nullable=True),
        sa.Column('cancer_diagnosis_date', sa.Date(), nullable=True),
        sa.Column('cancer_icd10_code', sa.String(20), nullable=True),
        sa.Column('cancer_snomed_code', sa.String(50), nullable=True),
        
        # Biomarkers
        sa.Column('er_status', sa.String(50), nullable=True),
        sa.Column('pr_status', sa.String(50), nullable=True),
        sa.Column('her2_status', sa.String(50), nullable=True),
        sa.Column('ki67_percentage', sa.Float(), nullable=True),
        sa.Column('oncotype_score', sa.Integer(), nullable=True),
        
        # AJCC Staging
        sa.Column('ajcc_t_category', sa.String(10), nullable=True),
        sa.Column('ajcc_n_category', sa.String(10), nullable=True),
        sa.Column('ajcc_m_category', sa.String(10), nullable=True),
        sa.Column('ajcc_stage_group', sa.String(20), nullable=True),
        
        # Treatment Plan
        sa.Column('line_of_treatment', sa.String(100), nullable=True),
        sa.Column('treatment_goal', sa.String(100), nullable=True),
        sa.Column('chemo_plan_name', sa.Text(), nullable=True),
        sa.Column('chemo_regimen_description', sa.Text(), nullable=True),
        sa.Column('chemo_start_date', sa.Date(), nullable=True),
        sa.Column('chemo_end_date', sa.Date(), nullable=True),
        sa.Column('current_cycle', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_cycles', sa.Integer(), nullable=True),
        sa.Column('treatment_department', sa.String(255), nullable=True),
        sa.Column('treatment_status', sa.String(50), server_default='active', nullable=True),
        
        # Appointments
        sa.Column('next_chemo_date', sa.Date(), nullable=True),
        sa.Column('next_clinic_visit', sa.Date(), nullable=True),
        sa.Column('last_chemo_date', sa.Date(), nullable=True),
        
        # Clinical Data
        sa.Column('bmi', sa.Numeric(5, 2), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('ecog_status', sa.Integer(), nullable=True),
        
        # Medical History
        sa.Column('history_of_cancer', sa.Text(), nullable=True),
        sa.Column('past_medical_history', sa.Text(), nullable=True),
        sa.Column('past_surgical_history', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('manual_review_required', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('profile_id'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id'], ondelete='SET NULL'),
    )
    op.create_index('ix_oncology_profiles_patient', 'oncology_profiles', ['patient_id'])
    op.create_index('ix_oncology_profiles_provider', 'oncology_profiles', ['provider_id'])
    op.create_index('ix_oncology_profiles_referral', 'oncology_profiles', ['referral_uuid'])
    op.create_index('ix_oncology_profiles_cancer_type', 'oncology_profiles', ['cancer_type'])
    op.create_index('ix_oncology_profiles_next_chemo', 'oncology_profiles', ['next_chemo_date'])
    op.create_index('ix_oncology_profiles_status', 'oncology_profiles', ['treatment_status'])
    
    # ==========================================================================
    # Medications Table - Normalized medication list
    # ==========================================================================
    op.create_table(
        'medications',
        sa.Column('medication_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('oncology_profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('referral_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Drug Identification
        sa.Column('medication_name', sa.String(255), nullable=False),
        sa.Column('generic_name', sa.String(255), nullable=True),
        sa.Column('brand_name', sa.String(255), nullable=True),
        sa.Column('ndc_code', sa.String(20), nullable=True),
        sa.Column('rxnorm_code', sa.String(20), nullable=True),
        
        # Classification
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('drug_class', sa.String(100), nullable=True),
        
        # Dosing
        sa.Column('dose', sa.String(100), nullable=True),
        sa.Column('dose_unit', sa.String(50), nullable=True),
        sa.Column('dose_per_m2', sa.String(50), nullable=True),
        sa.Column('calculated_dose', sa.String(100), nullable=True),
        sa.Column('route', sa.String(50), nullable=True),
        sa.Column('frequency', sa.String(100), nullable=True),
        sa.Column('duration', sa.String(100), nullable=True),
        
        # Treatment Timing
        sa.Column('cycle_day', sa.String(50), nullable=True),
        sa.Column('cycles_planned', sa.Integer(), nullable=True),
        sa.Column('cycles_completed', sa.Integer(), server_default='0', nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        
        # Status
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('discontinued_reason', sa.Text(), nullable=True),
        sa.Column('discontinued_date', sa.Date(), nullable=True),
        
        # Data Source
        sa.Column('source', sa.String(50), server_default='ocr', nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('medication_id'),
        sa.ForeignKeyConstraint(['oncology_profile_id'], ['oncology_profiles.profile_id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "category IN ('chemotherapy', 'hormone_therapy', 'targeted_therapy', "
            "'immunotherapy', 'supportive', 'prophylactic', 'other')",
            name='medications_category_check'
        ),
    )
    op.create_index('ix_medications_patient', 'medications', ['patient_id'])
    op.create_index('ix_medications_profile', 'medications', ['oncology_profile_id'])
    op.create_index('ix_medications_category', 'medications', ['category'])
    op.create_index('ix_medications_active', 'medications', ['active'])
    op.create_index('ix_medications_name', 'medications', ['medication_name'])
    
    # ==========================================================================
    # Chemo Schedule Table - Specific chemotherapy appointment dates
    # ==========================================================================
    op.create_table(
        'chemo_schedule',
        sa.Column('schedule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('oncology_profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Appointment Details
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_time', sa.Time(), nullable=True),
        sa.Column('cycle_number', sa.Integer(), nullable=True),
        sa.Column('day_of_cycle', sa.Integer(), nullable=True),
        
        # Medications
        sa.Column('medications', postgresql.JSONB(), server_default='[]', nullable=True),
        
        # Status
        sa.Column('status', sa.String(50), server_default='scheduled', nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('source', sa.String(50), server_default='ocr', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('schedule_id'),
        sa.ForeignKeyConstraint(['oncology_profile_id'], ['oncology_profiles.profile_id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'missed')",
            name='chemo_schedule_status_check'
        ),
    )
    op.create_index('ix_chemo_schedule_patient', 'chemo_schedule', ['patient_id'])
    op.create_index('ix_chemo_schedule_date', 'chemo_schedule', ['scheduled_date'])
    op.create_index('ix_chemo_schedule_status', 'chemo_schedule', ['status'])
    
    # ==========================================================================
    # Fax Ingestion Log Table - HIPAA audit trail
    # ==========================================================================
    op.create_table(
        'fax_ingestion_log',
        sa.Column('fax_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Fax Reception
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('source_number', sa.String(20), nullable=True),
        sa.Column('destination_number', sa.String(20), nullable=True),
        
        # Provider Info
        sa.Column('fax_provider', sa.String(50), nullable=False),
        sa.Column('provider_fax_id', sa.String(255), nullable=True),
        sa.Column('provider_callback_url', sa.Text(), nullable=True),
        
        # Document Info
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        
        # S3 Storage
        sa.Column('s3_bucket', sa.String(255), nullable=True),
        sa.Column('s3_key', sa.String(500), nullable=True),
        sa.Column('s3_version_id', sa.String(255), nullable=True),
        
        # OCR Processing
        sa.Column('ocr_status', sa.String(50), server_default='pending', nullable=False),
        sa.Column('ocr_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ocr_duration_ms', sa.Integer(), nullable=True),
        sa.Column('textract_job_id', sa.String(255), nullable=True),
        sa.Column('overall_confidence', sa.Float(), nullable=True),
        
        # Manual Review
        sa.Column('manual_review_required', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('manual_review_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        
        # Error Handling
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        
        # Linked Records
        sa.Column('referral_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('patient_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        
        # HIPAA Audit
        sa.Column('webhook_ip_address', sa.String(50), nullable=True),
        sa.Column('webhook_signature_valid', sa.Boolean(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('fax_id'),
        sa.CheckConstraint(
            "ocr_status IN ('pending', 'processing', 'completed', 'failed', 'manual_review')",
            name='fax_ingestion_ocr_status_check'
        ),
    )
    op.create_index('ix_fax_ingestion_received', 'fax_ingestion_log', ['received_at'])
    op.create_index('ix_fax_ingestion_status', 'fax_ingestion_log', ['ocr_status'])
    op.create_index('ix_fax_ingestion_referral', 'fax_ingestion_log', ['referral_uuid'])
    op.create_index('ix_fax_ingestion_patient', 'fax_ingestion_log', ['patient_uuid'])
    op.create_index('ix_fax_ingestion_provider', 'fax_ingestion_log', ['fax_provider'])
    op.create_index('ix_fax_ingestion_review', 'fax_ingestion_log', ['manual_review_required'])
    
    # ==========================================================================
    # OCR Field Confidence Table - Per-field accuracy scores
    # ==========================================================================
    op.create_table(
        'ocr_field_confidence',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('fax_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('referral_uuid', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Field Identification
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('field_category', sa.String(50), nullable=False),
        
        # Extracted Values
        sa.Column('extracted_value', sa.Text(), nullable=True),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        
        # Confidence Scoring
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False),
        sa.Column('confidence_threshold', sa.Numeric(5, 4), nullable=False),
        
        # Review Status
        sa.Column('status', sa.String(50), server_default='pending', nullable=True),
        sa.Column('accepted', sa.Boolean(), nullable=True),
        
        # Manual Correction
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('corrected_value', sa.Text(), nullable=True),
        sa.Column('correction_reason', sa.Text(), nullable=True),
        
        # Source Location
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_location', postgresql.JSONB(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['fax_id'], ['fax_ingestion_log.fax_id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "field_category IN ('patient', 'physician', 'clinic', 'diagnosis', "
            "'treatment', 'medication', 'vitals', 'history', 'other')",
            name='ocr_field_category_check'
        ),
        sa.CheckConstraint(
            "status IN ('accepted', 'requires_review', 'rejected', 'corrected', 'pending')",
            name='ocr_field_status_check'
        ),
    )
    op.create_index('ix_ocr_confidence_fax', 'ocr_field_confidence', ['fax_id'])
    op.create_index('ix_ocr_confidence_referral', 'ocr_field_confidence', ['referral_uuid'])
    op.create_index('ix_ocr_confidence_field', 'ocr_field_confidence', ['field_name'])
    op.create_index('ix_ocr_confidence_status', 'ocr_field_confidence', ['status'])
    op.create_index('ix_ocr_confidence_category', 'ocr_field_confidence', ['field_category'])
    
    # ==========================================================================
    # OCR Confidence Thresholds Table - Configuration for field validation
    # ==========================================================================
    op.create_table(
        'ocr_confidence_thresholds',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('field_category', sa.String(50), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=True),
        
        # Thresholds
        sa.Column('auto_accept_threshold', sa.Numeric(5, 4), nullable=False),
        sa.Column('manual_review_threshold', sa.Numeric(5, 4), nullable=False),
        
        # Field Configuration
        sa.Column('is_required', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('validation_regex', sa.Text(), nullable=True),
        sa.Column('validation_type', sa.String(50), nullable=True),
        
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Insert default thresholds
    op.execute("""
        INSERT INTO ocr_confidence_thresholds (field_category, field_name, auto_accept_threshold, manual_review_threshold, is_required, validation_type, description)
        VALUES 
            ('patient', 'patient_first_name', 0.95, 0.80, true, 'text', 'Patient first name'),
            ('patient', 'patient_last_name', 0.95, 0.80, true, 'text', 'Patient last name'),
            ('patient', 'patient_dob', 0.98, 0.85, true, 'date', 'Patient date of birth'),
            ('patient', 'patient_email', 0.95, 0.85, true, 'email', 'Patient email address'),
            ('patient', 'patient_phone', 0.95, 0.85, true, 'phone', 'Patient phone number'),
            ('patient', 'patient_mrn', 0.98, 0.90, false, 'text', 'Medical record number'),
            ('physician', 'attending_physician_name', 0.90, 0.75, true, 'text', 'Attending physician name'),
            ('physician', 'attending_physician_npi', 0.98, 0.90, false, 'npi', 'Physician NPI number'),
            ('clinic', 'clinic_name', 0.90, 0.75, true, 'text', 'Clinic name'),
            ('clinic', 'clinic_phone', 0.90, 0.80, false, 'phone', 'Clinic phone number'),
            ('clinic', 'clinic_fax', 0.90, 0.80, false, 'phone', 'Clinic fax number'),
            ('clinic', 'clinic_address', 0.85, 0.70, false, 'text', 'Clinic address'),
            ('diagnosis', 'cancer_type', 0.90, 0.75, true, 'text', 'Cancer type/diagnosis'),
            ('diagnosis', 'cancer_stage', 0.92, 0.80, false, 'text', 'Cancer staging'),
            ('diagnosis', 'cancer_icd10_code', 0.95, 0.85, false, 'icd10', 'ICD-10 diagnosis code'),
            ('treatment', 'chemo_plan_name', 0.88, 0.70, false, 'text', 'Chemotherapy plan name'),
            ('treatment', 'chemo_start_date', 0.95, 0.85, false, 'date', 'Treatment start date'),
            ('treatment', 'chemo_end_date', 0.95, 0.85, false, 'date', 'Treatment end date'),
            ('treatment', 'total_cycles', 0.95, 0.85, false, 'number', 'Total planned cycles'),
            ('medication', 'medication_name', 0.90, 0.75, false, 'text', 'Medication name'),
            ('medication', 'dose', 0.92, 0.80, false, 'text', 'Medication dose'),
            ('medication', 'frequency', 0.88, 0.75, false, 'text', 'Medication frequency'),
            ('vitals', 'bmi', 0.95, 0.85, false, 'number', 'Body mass index'),
            ('vitals', 'height_cm', 0.95, 0.85, false, 'number', 'Height in cm'),
            ('vitals', 'weight_kg', 0.95, 0.85, false, 'number', 'Weight in kg'),
            ('vitals', 'blood_pressure', 0.90, 0.80, false, 'text', 'Blood pressure reading')
    """)


def downgrade() -> None:
    """Drop onboarding and OCR tables."""
    op.drop_table('ocr_confidence_thresholds')
    op.drop_table('ocr_field_confidence')
    op.drop_table('fax_ingestion_log')
    op.drop_table('chemo_schedule')
    op.drop_table('medications')
    op.drop_table('oncology_profiles')
    op.drop_table('providers')
    
    # Remove columns from users table
    op.drop_column('users', 'emergency_contact_phone')
    op.drop_column('users', 'emergency_contact_name')
