-- AEGIS PostgreSQL Initialization
-- Creates schemas for audit logs, metadata, and tenant management

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- SCHEMA: Audit (HIPAA compliance)
-- ===========================================
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE audit.access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(255),
    user_email VARCHAR(255),
    tenant_id VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    patient_id VARCHAR(255),
    purpose VARCHAR(50),
    purpose_detail TEXT,
    action VARCHAR(50),
    success BOOLEAN DEFAULT true,
    denial_reason TEXT,
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(255),
    duration_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX idx_audit_timestamp ON audit.access_logs(timestamp DESC);
CREATE INDEX idx_audit_tenant ON audit.access_logs(tenant_id);
CREATE INDEX idx_audit_user ON audit.access_logs(user_id);
CREATE INDEX idx_audit_patient ON audit.access_logs(patient_id);
CREATE INDEX idx_audit_resource ON audit.access_logs(resource_type, resource_id);

-- ===========================================
-- SCHEMA: Tenants
-- ===========================================
CREATE SCHEMA IF NOT EXISTS tenants;

CREATE TABLE tenants.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'provider',
    is_active BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    hipaa_baa_signed BOOLEAN DEFAULT false,
    data_region VARCHAR(50) DEFAULT 'us-east-1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE tenants.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sub VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    name VARCHAR(255),
    given_name VARCHAR(100),
    family_name VARCHAR(100),
    tenant_id UUID NOT NULL REFERENCES tenants.organizations(id),
    roles JSONB DEFAULT '{}',
    npi VARCHAR(20),
    credentials VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    mfa_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_tenant ON tenants.users(tenant_id);
CREATE INDEX idx_users_email ON tenants.users(email);

-- ===========================================
-- SCHEMA: Pipeline (ingestion tracking)
-- ===========================================
CREATE SCHEMA IF NOT EXISTS pipeline;

CREATE TABLE pipeline.ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    records_total INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE pipeline.data_quality_issues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES pipeline.ingestion_jobs(id),
    tenant_id UUID NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    rule_name VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_tenant ON pipeline.ingestion_jobs(tenant_id);
CREATE INDEX idx_jobs_status ON pipeline.ingestion_jobs(status);
CREATE INDEX idx_dq_job ON pipeline.data_quality_issues(job_id);

-- ===========================================
-- Insert default tenant for development
-- ===========================================
INSERT INTO tenants.organizations (id, name, slug, type, hipaa_baa_signed)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'AEGIS Development',
    'aegis-dev',
    'provider',
    true
) ON CONFLICT (slug) DO NOTHING;
