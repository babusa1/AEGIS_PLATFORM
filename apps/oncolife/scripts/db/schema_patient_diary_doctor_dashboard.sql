-- =============================================================================
-- OncoLife Database Schema - Complete Schema Update
-- =============================================================================
-- Run this script to add tables for:
-- 
-- PATIENT DATABASE (oncolife_patient):
-- 1. Patient Questions ("Questions to Ask Doctor")
-- 2. Providers (normalized physician/clinic data from OCR)
-- 3. Oncology Profiles (cancer/treatment/chemo timeline)
-- 4. Medications (normalized drug list from referrals)
-- 5. Fax Ingestion Log (HIPAA audit trail)
-- 6. OCR Field Confidence (per-field accuracy scores)
-- 7. Patient Info Updates (emergency contacts)
-- 8. Patient Referrals Updates (complete OCR field coverage)
--
-- DOCTOR DATABASE (oncolife_doctor):
-- 9. Symptom Time Series (analytics)
-- 10. Treatment Events (timeline overlays)
-- 11. Physician Reports (weekly reports)
-- 12. Audit Logs (HIPAA compliance)
--
-- Execute against the appropriate database:
-- - Patient tables: Run against oncolife_patient database
-- - Doctor tables: Run against oncolife_doctor database
--
-- Last Updated: January 2026
-- =============================================================================

-- =============================================================================
-- PATIENT DATABASE TABLES (oncolife_patient)
-- =============================================================================

-- Patient Questions - "Questions to Ask Doctor" feature
CREATE TABLE IF NOT EXISTS patient_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_uuid UUID NOT NULL,
    question_text TEXT NOT NULL,
    share_with_physician BOOLEAN DEFAULT false NOT NULL,
    is_answered BOOLEAN DEFAULT false NOT NULL,
    category VARCHAR(50) DEFAULT 'other',
    is_deleted BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for patient_questions
CREATE INDEX IF NOT EXISTS ix_patient_questions_patient 
    ON patient_questions(patient_uuid);
CREATE INDEX IF NOT EXISTS ix_patient_questions_shared 
    ON patient_questions(share_with_physician);
CREATE INDEX IF NOT EXISTS ix_patient_questions_created 
    ON patient_questions(created_at DESC);

-- Add comment
COMMENT ON TABLE patient_questions IS 'Patient questions to ask their doctor (opt-in sharing)';


-- =============================================================================
-- PATIENT INFO UPDATES - Add emergency contact columns
-- =============================================================================

ALTER TABLE patient_info 
ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(200),
ADD COLUMN IF NOT EXISTS emergency_contact_phone VARCHAR(20);

COMMENT ON COLUMN patient_info.emergency_contact_name IS 'Emergency contact full name';
COMMENT ON COLUMN patient_info.emergency_contact_phone IS 'Emergency contact phone number';


-- =============================================================================
-- PATIENT REFERRALS UPDATES - Complete OCR field coverage
-- =============================================================================

-- Add missing columns to patient_referrals if they don't exist
-- These capture all fields from the faxed referral form

-- Physician/Clinic Details
ALTER TABLE patient_referrals 
ADD COLUMN IF NOT EXISTS referring_clinic VARCHAR(255),
ADD COLUMN IF NOT EXISTS referring_ehr VARCHAR(100),
ADD COLUMN IF NOT EXISTS attending_physician_npi VARCHAR(20),
ADD COLUMN IF NOT EXISTS clinic_address TEXT,
ADD COLUMN IF NOT EXISTS clinic_city VARCHAR(100),
ADD COLUMN IF NOT EXISTS clinic_state VARCHAR(50),
ADD COLUMN IF NOT EXISTS clinic_zip VARCHAR(20),
ADD COLUMN IF NOT EXISTS clinic_phone VARCHAR(20),
ADD COLUMN IF NOT EXISTS clinic_fax VARCHAR(20);

-- Cancer Diagnosis Details
ALTER TABLE patient_referrals 
ADD COLUMN IF NOT EXISTS cancer_diagnosis_date DATE,
ADD COLUMN IF NOT EXISTS cancer_icd10_code VARCHAR(20),
ADD COLUMN IF NOT EXISTS cancer_snomed_code VARCHAR(50),
ADD COLUMN IF NOT EXISTS cancer_histology VARCHAR(255),
ADD COLUMN IF NOT EXISTS cancer_grade VARCHAR(50);

-- Treatment Details
ALTER TABLE patient_referrals 
ADD COLUMN IF NOT EXISTS chemo_regimen TEXT,
ADD COLUMN IF NOT EXISTS treatment_department VARCHAR(255),
ADD COLUMN IF NOT EXISTS treatment_goal VARCHAR(100),
ADD COLUMN IF NOT EXISTS line_of_treatment VARCHAR(100),
ADD COLUMN IF NOT EXISTS treatment_status VARCHAR(50);

-- Vitals (expanded)
ALTER TABLE patient_referrals 
ADD COLUMN IF NOT EXISTS pulse INTEGER,
ADD COLUMN IF NOT EXISTS temperature_f FLOAT,
ADD COLUMN IF NOT EXISTS spo2 INTEGER,
ADD COLUMN IF NOT EXISTS ecog_performance_status INTEGER;

-- Social/Behavioral
ALTER TABLE patient_referrals 
ADD COLUMN IF NOT EXISTS tobacco_use VARCHAR(50),
ADD COLUMN IF NOT EXISTS alcohol_use VARCHAR(100),
ADD COLUMN IF NOT EXISTS drug_use VARCHAR(100),
ADD COLUMN IF NOT EXISTS social_drivers JSONB DEFAULT '{}';

-- Medical History (JSONB for structured storage)
ALTER TABLE patient_referrals 
ADD COLUMN IF NOT EXISTS history_of_cancer TEXT,
ADD COLUMN IF NOT EXISTS lab_results JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS family_history JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS genetic_testing TEXT,
ADD COLUMN IF NOT EXISTS allergies TEXT;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_referrals_clinic ON patient_referrals(referring_clinic);
CREATE INDEX IF NOT EXISTS idx_referrals_physician ON patient_referrals(attending_physician_name);
CREATE INDEX IF NOT EXISTS idx_referrals_diagnosis_date ON patient_referrals(cancer_diagnosis_date);


-- =============================================================================
-- PROVIDERS TABLE - Normalized physician/clinic data
-- =============================================================================

CREATE TABLE IF NOT EXISTS providers (
    provider_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Physician Info
    full_name VARCHAR(255) NOT NULL,
    npi VARCHAR(20) UNIQUE,
    specialty VARCHAR(100),
    credentials VARCHAR(50),  -- MD, DO, NP, etc.
    
    -- Clinic Info
    clinic_name VARCHAR(255),
    clinic_address TEXT,
    clinic_city VARCHAR(100),
    clinic_state VARCHAR(50),
    clinic_zip VARCHAR(20),
    phone VARCHAR(20),
    fax VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(255),
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'ocr',  -- ocr, manual, ehr_sync
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_providers_npi ON providers(npi);
CREATE INDEX IF NOT EXISTS idx_providers_name ON providers(full_name);
CREATE INDEX IF NOT EXISTS idx_providers_clinic ON providers(clinic_name);

COMMENT ON TABLE providers IS 'Normalized physician and clinic data extracted from referrals';


-- =============================================================================
-- ONCOLOGY PROFILES TABLE - Cancer diagnosis and treatment plan
-- =============================================================================

CREATE TABLE IF NOT EXISTS oncology_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,  -- References patient_info(uuid)
    provider_id UUID REFERENCES providers(provider_id),
    referral_uuid UUID,  -- References patient_referrals(uuid)
    
    -- Cancer Diagnosis
    cancer_type VARCHAR(255),
    cancer_stage VARCHAR(50),
    cancer_grade VARCHAR(50),
    cancer_histology VARCHAR(255),
    cancer_diagnosis_date DATE,
    cancer_icd10_code VARCHAR(20),
    cancer_snomed_code VARCHAR(50),
    
    -- Biomarkers (for breast cancer, etc.)
    er_status VARCHAR(50),  -- Positive, Negative, Unknown
    pr_status VARCHAR(50),
    her2_status VARCHAR(50),
    ki67_percentage FLOAT,
    oncotype_score INTEGER,
    
    -- AJCC Staging Details
    ajcc_t_category VARCHAR(10),
    ajcc_n_category VARCHAR(10),
    ajcc_m_category VARCHAR(10),
    ajcc_stage_group VARCHAR(20),
    
    -- Treatment Plan
    line_of_treatment VARCHAR(100),
    treatment_goal VARCHAR(100),
    chemo_plan_name TEXT,
    chemo_regimen_description TEXT,
    chemo_start_date DATE,
    chemo_end_date DATE,
    current_cycle INTEGER DEFAULT 0,
    total_cycles INTEGER,
    treatment_department VARCHAR(255),
    treatment_status VARCHAR(50) DEFAULT 'active',
    
    -- Upcoming Appointments (for ChemoTimeline component)
    next_chemo_date DATE,
    next_clinic_visit DATE,
    last_chemo_date DATE,
    
    -- Clinical Data (hidden from patient view)
    bmi DECIMAL(5,2),
    height_cm FLOAT,
    weight_kg FLOAT,
    ecog_status INTEGER,
    
    -- Medical History (stored but not displayed)
    history_of_cancer TEXT,
    past_medical_history TEXT,
    past_surgical_history TEXT,
    
    -- Metadata
    ocr_confidence FLOAT,
    manual_review_required BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_oncology_patient ON oncology_profiles(patient_id);
CREATE INDEX IF NOT EXISTS idx_oncology_provider ON oncology_profiles(provider_id);
CREATE INDEX IF NOT EXISTS idx_oncology_referral ON oncology_profiles(referral_uuid);
CREATE INDEX IF NOT EXISTS idx_oncology_cancer_type ON oncology_profiles(cancer_type);
CREATE INDEX IF NOT EXISTS idx_oncology_next_chemo ON oncology_profiles(next_chemo_date);
CREATE INDEX IF NOT EXISTS idx_oncology_status ON oncology_profiles(treatment_status);

COMMENT ON TABLE oncology_profiles IS 'Patient oncology profile with cancer diagnosis and treatment plan';


-- =============================================================================
-- MEDICATIONS TABLE - Normalized medication/drug list
-- =============================================================================

CREATE TABLE IF NOT EXISTS medications (
    medication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,  -- References patient_info(uuid)
    oncology_profile_id UUID REFERENCES oncology_profiles(profile_id),
    referral_uuid UUID,  -- Source referral
    
    -- Drug Identification
    medication_name VARCHAR(255) NOT NULL,
    generic_name VARCHAR(255),
    brand_name VARCHAR(255),
    ndc_code VARCHAR(20),  -- National Drug Code
    rxnorm_code VARCHAR(20),
    
    -- Classification
    category VARCHAR(50) NOT NULL CHECK (
        category IN ('chemotherapy', 'hormone_therapy', 'targeted_therapy', 
                     'immunotherapy', 'supportive', 'prophylactic', 'other')
    ),
    drug_class VARCHAR(100),
    
    -- Dosing
    dose VARCHAR(100),
    dose_unit VARCHAR(50),
    dose_per_m2 VARCHAR(50),  -- mg/m2 for chemo
    calculated_dose VARCHAR(100),
    route VARCHAR(50),  -- IV, Oral, Subcutaneous, etc.
    frequency VARCHAR(100),
    duration VARCHAR(100),
    
    -- Treatment Timing
    cycle_day VARCHAR(50),  -- Day 1, Days 1,8,15, etc.
    cycles_planned INTEGER,
    cycles_completed INTEGER DEFAULT 0,
    start_date DATE,
    end_date DATE,
    
    -- Status
    active BOOLEAN DEFAULT true,
    discontinued_reason TEXT,
    discontinued_date DATE,
    
    -- Data Source
    source VARCHAR(50) DEFAULT 'ocr',  -- ocr, manual, ehr_sync
    ocr_confidence FLOAT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_medications_profile ON medications(oncology_profile_id);
CREATE INDEX IF NOT EXISTS idx_medications_category ON medications(category);
CREATE INDEX IF NOT EXISTS idx_medications_active ON medications(active);
CREATE INDEX IF NOT EXISTS idx_medications_name ON medications(medication_name);

COMMENT ON TABLE medications IS 'Normalized medication list extracted from referrals';


-- =============================================================================
-- CHEMO SCHEDULE TABLE - Specific chemotherapy appointment dates
-- =============================================================================

CREATE TABLE IF NOT EXISTS chemo_schedule (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    oncology_profile_id UUID REFERENCES oncology_profiles(profile_id),
    
    -- Appointment Details
    scheduled_date DATE NOT NULL,
    scheduled_time TIME,
    cycle_number INTEGER,
    day_of_cycle INTEGER,  -- Day 1, Day 8, Day 15, etc.
    
    -- Medications for this date
    medications JSONB DEFAULT '[]',  -- Array of medication names
    
    -- Status
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (
        status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'missed')
    ),
    completed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'ocr',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chemo_schedule_patient ON chemo_schedule(patient_id);
CREATE INDEX IF NOT EXISTS idx_chemo_schedule_date ON chemo_schedule(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_chemo_schedule_status ON chemo_schedule(status);

COMMENT ON TABLE chemo_schedule IS 'Specific chemotherapy appointment dates for timeline visualization';


-- =============================================================================
-- FAX INGESTION LOG TABLE - HIPAA audit trail for fax reception
-- =============================================================================

CREATE TABLE IF NOT EXISTS fax_ingestion_log (
    fax_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Fax Reception
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_number VARCHAR(20),
    destination_number VARCHAR(20),
    
    -- Provider Info
    fax_provider VARCHAR(50) NOT NULL,  -- sinch, twilio, phaxio, ringcentral
    provider_fax_id VARCHAR(255),
    provider_callback_url TEXT,
    
    -- Document Info
    page_count INTEGER,
    file_type VARCHAR(50),  -- pdf, tiff
    file_size_bytes INTEGER,
    
    -- S3 Storage
    s3_bucket VARCHAR(255),
    s3_key VARCHAR(500),
    s3_version_id VARCHAR(255),
    
    -- OCR Processing
    ocr_status VARCHAR(50) DEFAULT 'pending' CHECK (
        ocr_status IN ('pending', 'processing', 'completed', 'failed', 'manual_review')
    ),
    ocr_started_at TIMESTAMP WITH TIME ZONE,
    ocr_completed_at TIMESTAMP WITH TIME ZONE,
    ocr_duration_ms INTEGER,
    textract_job_id VARCHAR(255),
    overall_confidence FLOAT,
    
    -- Manual Review
    manual_review_required BOOLEAN DEFAULT false,
    manual_review_reason TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(100),
    review_notes TEXT,
    
    -- Error Handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP WITH TIME ZONE,
    
    -- Linked Records
    referral_uuid UUID,  -- Created referral
    patient_uuid UUID,   -- Created/matched patient
    
    -- HIPAA Audit
    webhook_ip_address VARCHAR(50),
    webhook_signature_valid BOOLEAN,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fax_log_received ON fax_ingestion_log(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_fax_log_status ON fax_ingestion_log(ocr_status);
CREATE INDEX IF NOT EXISTS idx_fax_log_referral ON fax_ingestion_log(referral_uuid);
CREATE INDEX IF NOT EXISTS idx_fax_log_patient ON fax_ingestion_log(patient_uuid);
CREATE INDEX IF NOT EXISTS idx_fax_log_provider ON fax_ingestion_log(fax_provider);
CREATE INDEX IF NOT EXISTS idx_fax_log_review ON fax_ingestion_log(manual_review_required);

COMMENT ON TABLE fax_ingestion_log IS 'HIPAA-compliant audit log of all fax receptions';


-- =============================================================================
-- OCR FIELD CONFIDENCE TABLE - Per-field accuracy scores
-- =============================================================================

CREATE TABLE IF NOT EXISTS ocr_field_confidence (
    id SERIAL PRIMARY KEY,
    fax_id UUID NOT NULL REFERENCES fax_ingestion_log(fax_id),
    referral_uuid UUID,
    
    -- Field Identification
    field_name VARCHAR(100) NOT NULL,
    field_category VARCHAR(50) NOT NULL CHECK (
        field_category IN ('patient', 'physician', 'clinic', 'diagnosis', 
                           'treatment', 'medication', 'vitals', 'history', 'other')
    ),
    
    -- Extracted Values
    extracted_value TEXT,
    normalized_value TEXT,  -- After cleanup/normalization
    
    -- Confidence Scoring
    confidence_score DECIMAL(5,4) NOT NULL,  -- 0.0000 to 1.0000
    confidence_threshold DECIMAL(5,4) NOT NULL,  -- Required threshold for auto-accept
    
    -- Review Status
    status VARCHAR(50) DEFAULT 'pending' CHECK (
        status IN ('accepted', 'requires_review', 'rejected', 'corrected', 'pending')
    ),
    accepted BOOLEAN,
    
    -- Manual Correction
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by VARCHAR(100),
    corrected_value TEXT,
    correction_reason TEXT,
    
    -- Source Location (for UI highlighting)
    source_page INTEGER,
    source_location JSONB,  -- Bounding box coordinates
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ocr_confidence_fax ON ocr_field_confidence(fax_id);
CREATE INDEX IF NOT EXISTS idx_ocr_confidence_referral ON ocr_field_confidence(referral_uuid);
CREATE INDEX IF NOT EXISTS idx_ocr_confidence_field ON ocr_field_confidence(field_name);
CREATE INDEX IF NOT EXISTS idx_ocr_confidence_status ON ocr_field_confidence(status);
CREATE INDEX IF NOT EXISTS idx_ocr_confidence_category ON ocr_field_confidence(field_category);
CREATE INDEX IF NOT EXISTS idx_ocr_confidence_low ON ocr_field_confidence(confidence_score) 
    WHERE confidence_score < 0.9;

COMMENT ON TABLE ocr_field_confidence IS 'Per-field OCR confidence scores for quality assurance';


-- =============================================================================
-- OCR CONFIDENCE THRESHOLDS - Reference data for field validation
-- =============================================================================

CREATE TABLE IF NOT EXISTS ocr_confidence_thresholds (
    id SERIAL PRIMARY KEY,
    field_category VARCHAR(50) NOT NULL,
    field_name VARCHAR(100),
    
    -- Thresholds
    auto_accept_threshold DECIMAL(5,4) NOT NULL,  -- Above this: auto-accept
    manual_review_threshold DECIMAL(5,4) NOT NULL,  -- Below this: reject
    
    -- Field Configuration
    is_required BOOLEAN DEFAULT false,
    validation_regex TEXT,
    validation_type VARCHAR(50),  -- email, phone, date, number, text
    
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default thresholds
INSERT INTO ocr_confidence_thresholds (field_category, field_name, auto_accept_threshold, manual_review_threshold, is_required, validation_type, description)
VALUES 
    -- Patient fields (high accuracy required)
    ('patient', 'patient_first_name', 0.95, 0.80, true, 'text', 'Patient first name'),
    ('patient', 'patient_last_name', 0.95, 0.80, true, 'text', 'Patient last name'),
    ('patient', 'patient_dob', 0.98, 0.85, true, 'date', 'Patient date of birth'),
    ('patient', 'patient_email', 0.95, 0.85, true, 'email', 'Patient email address'),
    ('patient', 'patient_phone', 0.95, 0.85, true, 'phone', 'Patient phone number'),
    ('patient', 'patient_mrn', 0.98, 0.90, false, 'text', 'Medical record number'),
    
    -- Physician fields
    ('physician', 'attending_physician_name', 0.90, 0.75, true, 'text', 'Attending physician name'),
    ('physician', 'attending_physician_npi', 0.98, 0.90, false, 'npi', 'Physician NPI number'),
    
    -- Clinic fields
    ('clinic', 'clinic_name', 0.90, 0.75, true, 'text', 'Clinic name'),
    ('clinic', 'clinic_phone', 0.90, 0.80, false, 'phone', 'Clinic phone number'),
    ('clinic', 'clinic_fax', 0.90, 0.80, false, 'phone', 'Clinic fax number'),
    ('clinic', 'clinic_address', 0.85, 0.70, false, 'text', 'Clinic address'),
    
    -- Diagnosis fields
    ('diagnosis', 'cancer_type', 0.90, 0.75, true, 'text', 'Cancer type/diagnosis'),
    ('diagnosis', 'cancer_stage', 0.92, 0.80, false, 'text', 'Cancer staging'),
    ('diagnosis', 'cancer_icd10_code', 0.95, 0.85, false, 'icd10', 'ICD-10 diagnosis code'),
    
    -- Treatment fields
    ('treatment', 'chemo_plan_name', 0.88, 0.70, false, 'text', 'Chemotherapy plan name'),
    ('treatment', 'chemo_start_date', 0.95, 0.85, false, 'date', 'Treatment start date'),
    ('treatment', 'chemo_end_date', 0.95, 0.85, false, 'date', 'Treatment end date'),
    ('treatment', 'total_cycles', 0.95, 0.85, false, 'number', 'Total planned cycles'),
    
    -- Medication fields
    ('medication', 'medication_name', 0.90, 0.75, false, 'text', 'Medication name'),
    ('medication', 'dose', 0.92, 0.80, false, 'text', 'Medication dose'),
    ('medication', 'frequency', 0.88, 0.75, false, 'text', 'Medication frequency'),
    
    -- Vitals fields
    ('vitals', 'bmi', 0.95, 0.85, false, 'number', 'Body mass index'),
    ('vitals', 'height_cm', 0.95, 0.85, false, 'number', 'Height in cm'),
    ('vitals', 'weight_kg', 0.95, 0.85, false, 'number', 'Weight in kg'),
    ('vitals', 'blood_pressure', 0.90, 0.80, false, 'text', 'Blood pressure reading')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE ocr_confidence_thresholds IS 'Configuration for OCR field validation thresholds';


-- =============================================================================
-- DOCTOR DATABASE TABLES (oncolife_doctor)
-- =============================================================================

-- Symptom Time Series - Powers timeline charts and analytics
CREATE TABLE IF NOT EXISTS symptom_time_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    symptom_id VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('mild', 'moderate', 'severe', 'urgent')),
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source_session_id UUID,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance-critical indexes
CREATE INDEX IF NOT EXISTS idx_symptom_patient_time 
    ON symptom_time_series(patient_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_symptom_severity 
    ON symptom_time_series(severity);

COMMENT ON TABLE symptom_time_series IS 'Time-series symptom data for clinical analytics';


-- Treatment Events - Timeline overlays for chemo correlation
CREATE TABLE IF NOT EXISTS treatment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL CHECK (
        event_type IN ('chemo_start', 'chemo_end', 'cycle_start', 'cycle_end', 'regimen_change')
    ),
    event_date DATE NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for timeline queries
CREATE INDEX IF NOT EXISTS idx_treatment_patient_date 
    ON treatment_events(patient_id, event_date);

COMMENT ON TABLE treatment_events IS 'Treatment events for timeline overlays';


-- Physician Reports - Weekly report metadata
CREATE TABLE IF NOT EXISTS physician_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    physician_id UUID NOT NULL,
    report_week_start DATE NOT NULL,
    report_week_end DATE NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    report_s3_path TEXT NOT NULL,
    patient_count INTEGER,
    alert_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for report retrieval
CREATE INDEX IF NOT EXISTS idx_report_physician_week 
    ON physician_reports(physician_id, report_week_start);

COMMENT ON TABLE physician_reports IS 'Weekly physician report metadata';


-- Audit Logs - HIPAA compliance tracking
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_role VARCHAR(50) NOT NULL CHECK (user_role IN ('physician', 'staff', 'admin')),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    ip_address VARCHAR(50),
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_audit_user_time 
    ON audit_logs(user_id, accessed_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity 
    ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_action 
    ON audit_logs(action);

COMMENT ON TABLE audit_logs IS 'HIPAA-compliant access audit logs';


-- =============================================================================
-- EDUCATION TABLES (PATIENT DATABASE)
-- =============================================================================

-- Education PDFs - Symptom-specific educational content
CREATE TABLE IF NOT EXISTS education_pdfs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_code VARCHAR(50) NOT NULL,              -- e.g., 'NAU-203', 'FEV-202'
    symptom_name VARCHAR(100) NOT NULL,             -- Human-readable name
    title VARCHAR(255) NOT NULL,                    -- Document title
    source VARCHAR(100),                            -- Source org (ACS, NCI, Chemocare)
    file_path VARCHAR(500) NOT NULL,                -- Relative path to PDF
    summary TEXT,                                   -- Brief content summary
    keywords TEXT[],                                -- Keywords for search
    display_order INTEGER NOT NULL DEFAULT 1,       -- Order within symptom
    is_active BOOLEAN NOT NULL DEFAULT true,        -- Active/inactive toggle
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_education_pdfs_symptom_code ON education_pdfs(symptom_code);
CREATE INDEX IF NOT EXISTS ix_education_pdfs_symptom_active ON education_pdfs(symptom_code, is_active);

COMMENT ON TABLE education_pdfs IS 'Symptom-specific education PDFs (61 total)';
COMMENT ON COLUMN education_pdfs.symptom_code IS 'Symptom code matching symptom checker (e.g., NAU-203)';
COMMENT ON COLUMN education_pdfs.file_path IS 'Relative path: symptoms/nausea/ACS_Nausea.pdf';

-- Education Handbooks - General reference handbooks
CREATE TABLE IF NOT EXISTS education_handbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,                    -- Handbook title
    description TEXT,                               -- Handbook description
    file_path VARCHAR(500) NOT NULL,                -- Relative path to PDF
    handbook_type VARCHAR(50) NOT NULL DEFAULT 'general',  -- general, emergency, medication
    display_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE education_handbooks IS 'General handbooks like Chemo Basics';
COMMENT ON COLUMN education_handbooks.file_path IS 'Relative path: handbooks/chemo_basics_handbook.pdf';

-- Education Regimen PDFs - Chemotherapy regimen-specific content
CREATE TABLE IF NOT EXISTS education_regimen_pdfs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regimen_code VARCHAR(50) NOT NULL,              -- e.g., 'R-CHOP', 'FOLFOX'
    regimen_name VARCHAR(100) NOT NULL,             -- Human-readable name
    title VARCHAR(255) NOT NULL,                    -- Document title
    source VARCHAR(100),                            -- Source organization
    file_path VARCHAR(500) NOT NULL,                -- Relative path to PDF
    document_type VARCHAR(50) NOT NULL DEFAULT 'overview',  -- overview, drug_info, side_effects
    drug_name VARCHAR(100),                         -- Drug name if drug-specific
    summary TEXT,                                   -- Brief summary
    display_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_education_regimen_pdfs_regimen ON education_regimen_pdfs(regimen_code);
CREATE INDEX IF NOT EXISTS ix_education_regimen_pdfs_regimen_active ON education_regimen_pdfs(regimen_code, is_active);

COMMENT ON TABLE education_regimen_pdfs IS 'Chemo regimen-specific PDFs (R-CHOP, FOLFOX, etc.)';
COMMENT ON COLUMN education_regimen_pdfs.regimen_code IS 'Matches patient oncology_profile.chemo_plan_name';
COMMENT ON COLUMN education_regimen_pdfs.document_type IS 'overview = regimen overview, drug_info = specific drug';


-- =============================================================================
-- DATA MIGRATION - Populate symptom_time_series from existing conversations
-- =============================================================================

-- Run this to backfill symptom time series data from existing conversations
-- Note: This is a one-time migration; new data will be populated automatically

-- INSERT INTO symptom_time_series (patient_id, symptom_id, severity, recorded_at, source_session_id)
-- SELECT 
--     c.patient_uuid,
--     unnest(c.symptom_list) as symptom_id,
--     COALESCE(
--         CASE 
--             WHEN c.conversation_state = 'EMERGENCY' THEN 'urgent'
--             ELSE 'moderate'
--         END, 
--         'moderate'
--     ) as severity,
--     c.created_at as recorded_at,
--     c.uuid as source_session_id
-- FROM conversations c
-- WHERE c.symptom_list IS NOT NULL
-- AND array_length(c.symptom_list, 1) > 0
-- ON CONFLICT DO NOTHING;


-- =============================================================================
-- GRANT PERMISSIONS (adjust as needed for your environment)
-- =============================================================================

-- Grant permissions to application user for PATIENT database
-- GRANT SELECT, INSERT, UPDATE ON patient_questions TO oncolife_app;
-- GRANT SELECT, INSERT, UPDATE ON providers TO oncolife_app;
-- GRANT SELECT, INSERT, UPDATE ON oncology_profiles TO oncolife_app;
-- GRANT SELECT, INSERT, UPDATE ON medications TO oncolife_app;
-- GRANT SELECT, INSERT, UPDATE ON chemo_schedule TO oncolife_app;
-- GRANT INSERT ON fax_ingestion_log TO oncolife_app;
-- GRANT SELECT, INSERT ON ocr_field_confidence TO oncolife_app;
-- GRANT SELECT ON ocr_confidence_thresholds TO oncolife_app;
-- GRANT SELECT ON education_pdfs TO oncolife_app;
-- GRANT SELECT ON education_handbooks TO oncolife_app;
-- GRANT SELECT ON education_regimen_pdfs TO oncolife_app;

-- Grant permissions for DOCTOR database
-- GRANT SELECT, INSERT ON symptom_time_series TO oncolife_app;
-- GRANT SELECT, INSERT ON treatment_events TO oncolife_app;
-- GRANT SELECT, INSERT ON physician_reports TO oncolife_app;
-- GRANT INSERT ON audit_logs TO oncolife_app;  -- No SELECT for security


-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Run these queries to verify tables were created:

-- PATIENT DATABASE:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- \dt+ patient_questions
-- \dt+ providers
-- \dt+ oncology_profiles
-- \dt+ medications
-- \dt+ chemo_schedule
-- \dt+ fax_ingestion_log
-- \dt+ ocr_field_confidence
-- \dt+ ocr_confidence_thresholds
-- \dt+ education_pdfs
-- \dt+ education_handbooks
-- \dt+ education_regimen_pdfs

-- Verify education content counts:
-- SELECT COUNT(*) as symptom_pdfs FROM education_pdfs WHERE is_active = true;
-- SELECT COUNT(*) as handbooks FROM education_handbooks WHERE is_active = true;
-- SELECT COUNT(*) as regimen_pdfs FROM education_regimen_pdfs WHERE is_active = true;

-- DOCTOR DATABASE:
-- \dt+ symptom_time_series
-- \dt+ treatment_events
-- \dt+ physician_reports
-- \dt+ audit_logs

-- Verify patient_info columns added:
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'patient_info' AND column_name LIKE 'emergency%';

-- Verify patient_referrals columns added:
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'patient_referrals' ORDER BY column_name;

-- Verify OCR thresholds seeded:
-- SELECT * FROM ocr_confidence_thresholds ORDER BY field_category, field_name;



