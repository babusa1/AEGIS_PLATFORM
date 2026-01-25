-- TimescaleDB Hypertables for Time-Series Data

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Vitals table (high-frequency time-series)
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

-- Convert to hypertable
SELECT create_hypertable('vitals', 'time', if_not_exists => TRUE);

-- Indexes for vitals
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

-- Continuous aggregates for common queries
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
GROUP BY bucket, tenant_id, patient_id, vital_type;

-- Retention policy (keep raw data for 90 days, aggregates longer)
SELECT add_retention_policy('vitals', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('wearable_metrics', INTERVAL '90 days', if_not_exists => TRUE);
