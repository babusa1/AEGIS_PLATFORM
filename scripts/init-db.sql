-- AEGIS Database Initialization Script
-- Runs automatically when PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =============================================================================
-- OPERATIONAL TABLES (Standard PostgreSQL)
-- =============================================================================

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    config JSONB DEFAULT '{}',
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(64) DEFAULT 'user',
    status VARCHAR(32) DEFAULT 'active',
    password_hash VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    scopes TEXT[] DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data Sources table
CREATE TABLE IF NOT EXISTS data_sources (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    config JSONB DEFAULT '{}',
    status VARCHAR(32) DEFAULT 'active',
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sync Jobs table
CREATE TABLE IF NOT EXISTS sync_jobs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    data_source_id VARCHAR(64) REFERENCES data_sources(id),
    job_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    records_processed INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log table
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(64),
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Consents table
CREATE TABLE IF NOT EXISTS consents (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    patient_id VARCHAR(64) NOT NULL,
    consent_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    granted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    scope JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Break-the-Glass Sessions
CREATE TABLE IF NOT EXISTS btg_sessions (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    user_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(64) NOT NULL,
    reason TEXT NOT NULL,
    approved_by VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- CLINICAL DATA TABLES (Patient, Conditions, Medications, etc.)
-- =============================================================================

-- Patients table
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    mrn VARCHAR(64) NOT NULL,
    given_name VARCHAR(255) NOT NULL,
    family_name VARCHAR(255) NOT NULL,
    birth_date DATE,
    gender VARCHAR(32),
    phone VARCHAR(32),
    email VARCHAR(255),
    address_line1 VARCHAR(255),
    address_city VARCHAR(128),
    address_state VARCHAR(32),
    address_postal VARCHAR(16),
    ssn_last4 VARCHAR(4),
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, mrn)
);

CREATE INDEX IF NOT EXISTS idx_patients_tenant ON patients(tenant_id);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(family_name, given_name);

-- Conditions table
CREATE TABLE IF NOT EXISTS conditions (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id),
    code VARCHAR(32) NOT NULL,
    code_system VARCHAR(64) DEFAULT 'ICD-10',
    display VARCHAR(255) NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    onset_date DATE,
    resolved_date DATE,
    severity VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conditions_patient ON conditions(patient_id);
CREATE INDEX IF NOT EXISTS idx_conditions_code ON conditions(code);

-- Medications table
CREATE TABLE IF NOT EXISTS medications (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id),
    code VARCHAR(32),
    code_system VARCHAR(64) DEFAULT 'RxNorm',
    display VARCHAR(255) NOT NULL,
    dosage VARCHAR(128),
    frequency VARCHAR(64),
    route VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    prescriber VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id);

-- Encounters table
CREATE TABLE IF NOT EXISTS encounters (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id),
    encounter_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'finished',
    admit_date TIMESTAMPTZ NOT NULL,
    discharge_date TIMESTAMPTZ,
    facility VARCHAR(255),
    provider VARCHAR(255),
    reason VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_encounters_patient ON encounters(patient_id, admit_date DESC);

-- Claims table
CREATE TABLE IF NOT EXISTS claims (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id),
    encounter_id VARCHAR(64) REFERENCES encounters(id),
    claim_number VARCHAR(64) NOT NULL,
    claim_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'submitted',
    billed_amount DECIMAL(12,2),
    allowed_amount DECIMAL(12,2),
    paid_amount DECIMAL(12,2),
    patient_responsibility DECIMAL(12,2),
    payer_name VARCHAR(255),
    service_date DATE,
    submission_date DATE,
    adjudication_date DATE,
    denial_reason VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claims_patient ON claims(patient_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

-- =============================================================================
-- TIMESCALEDB HYPERTABLES (Time-Series Data)
-- =============================================================================

-- Vitals table
CREATE TABLE IF NOT EXISTS vitals (
    time TIMESTAMPTZ NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(64) NOT NULL,
    vital_type VARCHAR(64) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(32),
    source VARCHAR(64),
    device_id VARCHAR(64)
);

SELECT create_hypertable('vitals', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_vitals_patient ON vitals(patient_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_vitals_type ON vitals(vital_type, time DESC);

-- Lab Results table
CREATE TABLE IF NOT EXISTS lab_results (
    time TIMESTAMPTZ NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(64) NOT NULL,
    test_code VARCHAR(64) NOT NULL,
    test_name VARCHAR(255),
    value DOUBLE PRECISION,
    value_string VARCHAR(255),
    unit VARCHAR(32),
    reference_low DOUBLE PRECISION,
    reference_high DOUBLE PRECISION,
    interpretation VARCHAR(32),
    abnormal BOOLEAN DEFAULT FALSE,
    critical BOOLEAN DEFAULT FALSE,
    source VARCHAR(64)
);

SELECT create_hypertable('lab_results', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_labs_patient ON lab_results(patient_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_labs_code ON lab_results(test_code, time DESC);

-- Wearable Metrics table
CREATE TABLE IF NOT EXISTS wearable_metrics (
    time TIMESTAMPTZ NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(64) NOT NULL,
    metric_type VARCHAR(64) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(32),
    device_type VARCHAR(64),
    device_id VARCHAR(64),
    source VARCHAR(64)
);

SELECT create_hypertable('wearable_metrics', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_wearables_patient ON wearable_metrics(patient_id, time DESC);

-- =============================================================================
-- CONTINUOUS AGGREGATES
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS vitals_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    tenant_id,
    patient_id,
    vital_type,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    COUNT(*) AS reading_count
FROM vitals
GROUP BY bucket, tenant_id, patient_id, vital_type
WITH NO DATA;

-- =============================================================================
-- RETENTION POLICIES
-- =============================================================================

SELECT add_retention_policy('vitals', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('wearable_metrics', INTERVAL '90 days', if_not_exists => TRUE);

-- =============================================================================
-- DEFAULT DATA
-- =============================================================================

-- Insert default tenant
INSERT INTO tenants (id, name, config, status)
VALUES ('default', 'Default Tenant', '{"features": ["all"]}', 'active')
ON CONFLICT (id) DO NOTHING;

-- Insert demo admin user (password: admin123)
INSERT INTO users (id, tenant_id, email, name, role, password_hash)
VALUES (
    'admin-001',
    'default',
    'admin@aegis.local',
    'AEGIS Admin',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.8l.2VW.uKZVtKW'
)
ON CONFLICT (tenant_id, email) DO NOTHING;

-- =============================================================================
-- SEED DATA: 20 Sample Patients
-- =============================================================================

INSERT INTO patients (id, tenant_id, mrn, given_name, family_name, birth_date, gender, phone, email, address_city, address_state) VALUES
    ('patient-001', 'default', 'MRN001001', 'John', 'Smith', '1958-03-15', 'male', '555-101-1001', 'john.smith@email.com', 'Boston', 'MA'),
    ('patient-002', 'default', 'MRN001002', 'Mary', 'Johnson', '1965-07-22', 'female', '555-102-1002', 'mary.johnson@email.com', 'Cambridge', 'MA'),
    ('patient-003', 'default', 'MRN001003', 'Robert', 'Williams', '1972-11-08', 'male', '555-103-1003', 'robert.williams@email.com', 'Somerville', 'MA'),
    ('patient-004', 'default', 'MRN001004', 'Patricia', 'Brown', '1980-01-30', 'female', '555-104-1004', 'patricia.brown@email.com', 'Newton', 'MA'),
    ('patient-005', 'default', 'MRN001005', 'Michael', 'Davis', '1955-09-12', 'male', '555-105-1005', 'michael.davis@email.com', 'Brookline', 'MA'),
    ('patient-006', 'default', 'MRN001006', 'Jennifer', 'Miller', '1968-04-18', 'female', '555-106-1006', 'jennifer.miller@email.com', 'Quincy', 'MA'),
    ('patient-007', 'default', 'MRN001007', 'William', 'Wilson', '1950-12-03', 'male', '555-107-1007', 'william.wilson@email.com', 'Medford', 'MA'),
    ('patient-008', 'default', 'MRN001008', 'Elizabeth', 'Moore', '1975-08-25', 'female', '555-108-1008', 'elizabeth.moore@email.com', 'Arlington', 'MA'),
    ('patient-009', 'default', 'MRN001009', 'David', 'Taylor', '1962-06-14', 'male', '555-109-1009', 'david.taylor@email.com', 'Watertown', 'MA'),
    ('patient-010', 'default', 'MRN001010', 'Barbara', 'Anderson', '1978-02-09', 'female', '555-110-1010', 'barbara.anderson@email.com', 'Waltham', 'MA'),
    ('patient-011', 'default', 'MRN001011', 'Richard', 'Thomas', '1948-11-22', 'male', '555-111-1011', 'richard.thomas@email.com', 'Malden', 'MA'),
    ('patient-012', 'default', 'MRN001012', 'Susan', 'Jackson', '1983-09-30', 'female', '555-112-1012', 'susan.jackson@email.com', 'Revere', 'MA'),
    ('patient-013', 'default', 'MRN001013', 'Joseph', 'White', '1970-05-07', 'male', '555-113-1013', 'joseph.white@email.com', 'Chelsea', 'MA'),
    ('patient-014', 'default', 'MRN001014', 'Margaret', 'Harris', '1959-01-19', 'female', '555-114-1014', 'margaret.harris@email.com', 'Everett', 'MA'),
    ('patient-015', 'default', 'MRN001015', 'Charles', 'Martin', '1945-07-28', 'male', '555-115-1015', 'charles.martin@email.com', 'Lynn', 'MA'),
    ('patient-016', 'default', 'MRN001016', 'Dorothy', 'Garcia', '1988-03-12', 'female', '555-116-1016', 'dorothy.garcia@email.com', 'Salem', 'MA'),
    ('patient-017', 'default', 'MRN001017', 'Thomas', 'Martinez', '1967-10-05', 'male', '555-117-1017', 'thomas.martinez@email.com', 'Peabody', 'MA'),
    ('patient-018', 'default', 'MRN001018', 'Lisa', 'Robinson', '1973-12-17', 'female', '555-118-1018', 'lisa.robinson@email.com', 'Beverly', 'MA'),
    ('patient-019', 'default', 'MRN001019', 'Daniel', 'Clark', '1952-08-21', 'male', '555-119-1019', 'daniel.clark@email.com', 'Gloucester', 'MA'),
    ('patient-020', 'default', 'MRN001020', 'Nancy', 'Rodriguez', '1981-04-03', 'female', '555-120-1020', 'nancy.rodriguez@email.com', 'Marblehead', 'MA')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- SEED DATA: Conditions (ICD-10)
-- =============================================================================

INSERT INTO conditions (id, tenant_id, patient_id, code, display, status, onset_date) VALUES
    -- Patient 001: Diabetes + Hypertension
    ('cond-001', 'default', 'patient-001', 'E11.9', 'Type 2 Diabetes Mellitus', 'active', '2015-03-10'),
    ('cond-002', 'default', 'patient-001', 'I10', 'Essential Hypertension', 'active', '2016-07-22'),
    -- Patient 002: Asthma
    ('cond-003', 'default', 'patient-002', 'J45.909', 'Asthma, unspecified', 'active', '2010-05-15'),
    -- Patient 003: Hyperlipidemia
    ('cond-004', 'default', 'patient-003', 'E78.5', 'Hyperlipidemia', 'active', '2018-09-01'),
    -- Patient 005: HIGH RISK - Diabetes + Hypertension + CKD + Heart Failure
    ('cond-005', 'default', 'patient-005', 'E11.9', 'Type 2 Diabetes Mellitus', 'active', '2008-01-15'),
    ('cond-006', 'default', 'patient-005', 'I10', 'Essential Hypertension', 'active', '2010-03-20'),
    ('cond-007', 'default', 'patient-005', 'N18.3', 'Chronic Kidney Disease Stage 3', 'active', '2018-06-10'),
    ('cond-008', 'default', 'patient-005', 'I50.9', 'Heart Failure, unspecified', 'active', '2020-11-05'),
    -- Patient 007: COPD + Hypertension (elderly high risk)
    ('cond-009', 'default', 'patient-007', 'J44.9', 'COPD', 'active', '2012-04-18'),
    ('cond-010', 'default', 'patient-007', 'I10', 'Essential Hypertension', 'active', '2005-08-30'),
    -- Patient 011: Multiple conditions (oldest patient)
    ('cond-011', 'default', 'patient-011', 'E11.9', 'Type 2 Diabetes Mellitus', 'active', '2000-02-14'),
    ('cond-012', 'default', 'patient-011', 'I10', 'Essential Hypertension', 'active', '1998-11-20'),
    ('cond-013', 'default', 'patient-011', 'E78.5', 'Hyperlipidemia', 'active', '2005-07-08'),
    ('cond-014', 'default', 'patient-011', 'M81.0', 'Osteoporosis', 'active', '2015-09-22'),
    -- Patient 015: Elderly with conditions
    ('cond-015', 'default', 'patient-015', 'I50.9', 'Heart Failure', 'active', '2019-03-15'),
    ('cond-016', 'default', 'patient-015', 'I10', 'Essential Hypertension', 'active', '1995-06-10'),
    -- Other patients with various conditions
    ('cond-017', 'default', 'patient-006', 'F32.9', 'Major Depressive Disorder', 'active', '2020-01-10'),
    ('cond-018', 'default', 'patient-008', 'E78.5', 'Hyperlipidemia', 'active', '2019-08-15'),
    ('cond-019', 'default', 'patient-009', 'I10', 'Essential Hypertension', 'active', '2017-05-20'),
    ('cond-020', 'default', 'patient-010', 'J45.909', 'Asthma', 'active', '2015-12-01')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- SEED DATA: Medications (RxNorm)
-- =============================================================================

INSERT INTO medications (id, tenant_id, patient_id, code, display, dosage, frequency, status, start_date) VALUES
    -- Patient 001
    ('med-001', 'default', 'patient-001', '860975', 'Metformin 500mg', '500mg', 'twice daily', 'active', '2015-03-15'),
    ('med-002', 'default', 'patient-001', '314076', 'Lisinopril 10mg', '10mg', 'once daily', 'active', '2016-08-01'),
    -- Patient 002
    ('med-003', 'default', 'patient-002', '745679', 'Albuterol inhaler', '2 puffs', 'as needed', 'active', '2010-05-20'),
    -- Patient 003
    ('med-004', 'default', 'patient-003', '310798', 'Atorvastatin 20mg', '20mg', 'once daily', 'active', '2018-09-10'),
    -- Patient 005 (HIGH RISK - polypharmacy)
    ('med-005', 'default', 'patient-005', '860975', 'Metformin 1000mg', '1000mg', 'twice daily', 'active', '2008-02-01'),
    ('med-006', 'default', 'patient-005', '314076', 'Lisinopril 20mg', '20mg', 'once daily', 'active', '2010-04-01'),
    ('med-007', 'default', 'patient-005', '310798', 'Atorvastatin 40mg', '40mg', 'once daily', 'active', '2015-01-15'),
    ('med-008', 'default', 'patient-005', '197361', 'Amlodipine 10mg', '10mg', 'once daily', 'active', '2018-07-01'),
    ('med-009', 'default', 'patient-005', '200801', 'Furosemide 40mg', '40mg', 'once daily', 'active', '2020-11-10'),
    ('med-010', 'default', 'patient-005', '198440', 'Aspirin 81mg', '81mg', 'once daily', 'active', '2015-01-15'),
    -- Patient 007
    ('med-011', 'default', 'patient-007', '896188', 'Tiotropium inhaler', '1 puff', 'once daily', 'active', '2012-05-01'),
    ('med-012', 'default', 'patient-007', '314076', 'Lisinopril 10mg', '10mg', 'once daily', 'active', '2005-09-01'),
    -- Patient 011
    ('med-013', 'default', 'patient-011', '860975', 'Metformin 500mg', '500mg', 'twice daily', 'active', '2000-03-01'),
    ('med-014', 'default', 'patient-011', '197361', 'Amlodipine 5mg', '5mg', 'once daily', 'active', '1998-12-01'),
    ('med-015', 'default', 'patient-011', '310798', 'Atorvastatin 10mg', '10mg', 'once daily', 'active', '2005-08-01'),
    ('med-016', 'default', 'patient-011', '312961', 'Omeprazole 20mg', '20mg', 'once daily', 'active', '2010-06-15'),
    -- Other patients
    ('med-017', 'default', 'patient-006', '312938', 'Sertraline 50mg', '50mg', 'once daily', 'active', '2020-02-01'),
    ('med-018', 'default', 'patient-008', '310798', 'Atorvastatin 10mg', '10mg', 'once daily', 'active', '2019-09-01'),
    ('med-019', 'default', 'patient-009', '314076', 'Lisinopril 5mg', '5mg', 'once daily', 'active', '2017-06-01'),
    ('med-020', 'default', 'patient-010', '745679', 'Albuterol inhaler', '2 puffs', 'as needed', 'active', '2015-12-15')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- SEED DATA: Encounters
-- =============================================================================

INSERT INTO encounters (id, tenant_id, patient_id, encounter_type, status, admit_date, discharge_date, facility, reason) VALUES
    -- Patient 001 encounters
    ('enc-001', 'default', 'patient-001', 'outpatient', 'finished', '2024-01-15 09:00:00', '2024-01-15 10:00:00', 'Boston Medical Center', 'Diabetes follow-up'),
    ('enc-002', 'default', 'patient-001', 'outpatient', 'finished', '2024-03-10 14:00:00', '2024-03-10 15:00:00', 'Boston Medical Center', 'Hypertension check'),
    -- Patient 002
    ('enc-003', 'default', 'patient-002', 'emergency', 'finished', '2024-02-20 22:00:00', '2024-02-21 06:00:00', 'Mass General Hospital', 'Asthma exacerbation'),
    -- Patient 005 (high risk - more encounters)
    ('enc-004', 'default', 'patient-005', 'inpatient', 'finished', '2024-01-05 14:00:00', '2024-01-09 11:00:00', 'Brigham and Womens', 'CHF exacerbation'),
    ('enc-005', 'default', 'patient-005', 'outpatient', 'finished', '2024-02-15 10:00:00', '2024-02-15 11:00:00', 'Brigham and Womens', 'Cardiology follow-up'),
    ('enc-006', 'default', 'patient-005', 'outpatient', 'finished', '2024-03-20 09:00:00', '2024-03-20 10:00:00', 'Brigham and Womens', 'Nephrology consult'),
    -- Patient 007
    ('enc-007', 'default', 'patient-007', 'inpatient', 'finished', '2024-01-25 08:00:00', '2024-01-28 14:00:00', 'Beth Israel', 'COPD exacerbation'),
    -- Patient 011
    ('enc-008', 'default', 'patient-011', 'outpatient', 'finished', '2024-02-08 11:00:00', '2024-02-08 12:00:00', 'Boston Medical Center', 'Annual wellness visit'),
    -- Other patients
    ('enc-009', 'default', 'patient-003', 'outpatient', 'finished', '2024-03-01 15:00:00', '2024-03-01 16:00:00', 'Cambridge Health', 'Lipid panel review'),
    ('enc-010', 'default', 'patient-006', 'outpatient', 'finished', '2024-02-28 10:00:00', '2024-02-28 11:00:00', 'Quincy Medical', 'Mental health follow-up')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- SEED DATA: Claims
-- =============================================================================

INSERT INTO claims (id, tenant_id, patient_id, encounter_id, claim_number, claim_type, status, billed_amount, paid_amount, payer_name, service_date) VALUES
    -- Patient 001 claims
    ('claim-001', 'default', 'patient-001', 'enc-001', 'CLM-2024-0001', 'professional', 'paid', 250.00, 200.00, 'Blue Cross Blue Shield', '2024-01-15'),
    ('claim-002', 'default', 'patient-001', 'enc-002', 'CLM-2024-0002', 'professional', 'paid', 180.00, 144.00, 'Blue Cross Blue Shield', '2024-03-10'),
    -- Patient 002 claims
    ('claim-003', 'default', 'patient-002', 'enc-003', 'CLM-2024-0003', 'institutional', 'paid', 3500.00, 2800.00, 'Aetna', '2024-02-20'),
    -- Patient 005 claims (includes denied claim)
    ('claim-004', 'default', 'patient-005', 'enc-004', 'CLM-2024-0004', 'institutional', 'paid', 15000.00, 12000.00, 'Medicare', '2024-01-05'),
    ('claim-005', 'default', 'patient-005', 'enc-005', 'CLM-2024-0005', 'professional', 'denied', 450.00, 0.00, 'Medicare', '2024-02-15'),
    ('claim-006', 'default', 'patient-005', 'enc-006', 'CLM-2024-0006', 'professional', 'paid', 350.00, 280.00, 'Medicare', '2024-03-20'),
    -- Patient 007 claims
    ('claim-007', 'default', 'patient-007', 'enc-007', 'CLM-2024-0007', 'institutional', 'paid', 8500.00, 6800.00, 'Medicare', '2024-01-25'),
    -- Other claims
    ('claim-008', 'default', 'patient-011', 'enc-008', 'CLM-2024-0008', 'professional', 'paid', 275.00, 220.00, 'Medicare', '2024-02-08'),
    ('claim-009', 'default', 'patient-003', 'enc-009', 'CLM-2024-0009', 'professional', 'pending', 200.00, NULL, 'United Healthcare', '2024-03-01'),
    ('claim-010', 'default', 'patient-006', 'enc-010', 'CLM-2024-0010', 'professional', 'denied', 175.00, 0.00, 'Cigna', '2024-02-28')
ON CONFLICT (id) DO NOTHING;

-- Update denied claims with denial reasons
UPDATE claims SET denial_reason = 'CO-4: Service not covered by plan' WHERE id = 'claim-005';
UPDATE claims SET denial_reason = 'CO-16: Missing prior authorization' WHERE id = 'claim-010';

-- =============================================================================
-- SEED DATA: Sample Vitals (TimescaleDB)
-- =============================================================================

INSERT INTO vitals (time, tenant_id, patient_id, vital_type, value, unit, source) VALUES
    -- Patient 001 vitals
    ('2024-01-15 09:30:00', 'default', 'patient-001', 'bp_systolic', 138, 'mmHg', 'clinic'),
    ('2024-01-15 09:30:00', 'default', 'patient-001', 'bp_diastolic', 88, 'mmHg', 'clinic'),
    ('2024-01-15 09:30:00', 'default', 'patient-001', 'heart_rate', 78, 'bpm', 'clinic'),
    ('2024-01-15 09:30:00', 'default', 'patient-001', 'temperature', 98.6, 'F', 'clinic'),
    ('2024-01-15 09:30:00', 'default', 'patient-001', 'weight', 195, 'lbs', 'clinic'),
    -- Patient 005 vitals (high risk indicators)
    ('2024-01-05 14:30:00', 'default', 'patient-005', 'bp_systolic', 165, 'mmHg', 'inpatient'),
    ('2024-01-05 14:30:00', 'default', 'patient-005', 'bp_diastolic', 98, 'mmHg', 'inpatient'),
    ('2024-01-05 14:30:00', 'default', 'patient-005', 'heart_rate', 102, 'bpm', 'inpatient'),
    ('2024-01-05 14:30:00', 'default', 'patient-005', 'spo2', 91, '%', 'inpatient'),
    ('2024-01-05 14:30:00', 'default', 'patient-005', 'weight', 220, 'lbs', 'inpatient'),
    -- Patient 007 vitals
    ('2024-01-25 08:30:00', 'default', 'patient-007', 'bp_systolic', 145, 'mmHg', 'inpatient'),
    ('2024-01-25 08:30:00', 'default', 'patient-007', 'spo2', 88, '%', 'inpatient'),
    ('2024-01-25 08:30:00', 'default', 'patient-007', 'heart_rate', 95, 'bpm', 'inpatient');

-- =============================================================================
-- SEED DATA: Sample Lab Results
-- =============================================================================

INSERT INTO lab_results (time, tenant_id, patient_id, test_code, test_name, value, unit, reference_low, reference_high, interpretation, abnormal) VALUES
    -- Patient 001 labs
    ('2024-01-15 10:00:00', 'default', 'patient-001', '4548-4', 'Hemoglobin A1c', 7.2, '%', 4.0, 5.6, 'high', true),
    ('2024-01-15 10:00:00', 'default', 'patient-001', '2345-7', 'Glucose', 145, 'mg/dL', 70, 100, 'high', true),
    -- Patient 005 labs (more concerning)
    ('2024-01-05 15:00:00', 'default', 'patient-005', '4548-4', 'Hemoglobin A1c', 8.5, '%', 4.0, 5.6, 'high', true),
    ('2024-01-05 15:00:00', 'default', 'patient-005', '2160-0', 'Creatinine', 2.1, 'mg/dL', 0.7, 1.3, 'high', true),
    ('2024-01-05 15:00:00', 'default', 'patient-005', '33914-3', 'eGFR', 38, 'mL/min/1.73m2', 90, 120, 'low', true),
    ('2024-01-05 15:00:00', 'default', 'patient-005', '30313-1', 'BNP', 850, 'pg/mL', 0, 100, 'high', true);

RAISE NOTICE 'AEGIS database initialization complete with seed data!';
