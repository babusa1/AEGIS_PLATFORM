-- AEGIS Initial Schema Migration
-- Postgres tables for operational metadata

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    permissions JSONB DEFAULT '[]',
    expires_at TIMESTAMPTZ,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data Sources (connector configs)
CREATE TABLE IF NOT EXISTS data_sources (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    connection_config JSONB NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    last_sync TIMESTAMPTZ,
    sync_frequency VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sync Jobs table
CREATE TABLE IF NOT EXISTS sync_jobs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    data_source_id VARCHAR(64) REFERENCES data_sources(id),
    status VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    records_processed INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Log table (high-volume, consider partitioning)
CREATE TABLE IF NOT EXISTS audit_log (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    category VARCHAR(32) NOT NULL,
    action VARCHAR(64) NOT NULL,
    actor_id VARCHAR(64) NOT NULL,
    actor_type VARCHAR(32) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(64),
    patient_id VARCHAR(64),
    outcome VARCHAR(32),
    severity VARCHAR(32) DEFAULT 'info',
    ip_address VARCHAR(45),
    details JSONB DEFAULT '{}',
    hash VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_time ON audit_log(tenant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_patient ON audit_log(patient_id, timestamp DESC);

-- Consent Records table
CREATE TABLE IF NOT EXISTS consents (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    patient_id VARCHAR(64) NOT NULL,
    scope VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    provisions JSONB DEFAULT '[]',
    source_document VARCHAR(255),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consent_patient ON consents(patient_id, status);

-- BTG Sessions table
CREATE TABLE IF NOT EXISTS btg_sessions (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    user_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(64) NOT NULL,
    reason VARCHAR(64) NOT NULL,
    justification TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    accessed_resources JSONB DEFAULT '[]',
    reviewed_by VARCHAR(64),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT
);

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    incident_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    reported_by VARCHAR(64),
    assigned_to VARCHAR(64),
    affected_systems JSONB DEFAULT '[]',
    affected_patients JSONB DEFAULT '[]',
    root_cause TEXT,
    resolution TEXT,
    resolved_at TIMESTAMPTZ,
    notification_required BOOLEAN DEFAULT FALSE,
    notification_deadline TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sources_tenant ON data_sources(tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON sync_jobs(data_source_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status, severity);
