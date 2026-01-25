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

RAISE NOTICE 'AEGIS database initialization complete!';
