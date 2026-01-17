-- Foundry TimescaleDB Initialization Script
-- For time-series metrics storage

-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create metrics schema
CREATE SCHEMA IF NOT EXISTS metrics;

-- Create predictions table (hypertable)
CREATE TABLE IF NOT EXISTS metrics.predictions (
    time TIMESTAMPTZ NOT NULL,
    model_id UUID NOT NULL,
    deployment_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    latency_ms DOUBLE PRECISION,
    input_size INTEGER,
    output_size INTEGER,
    status VARCHAR(50),
    error_message TEXT
);

SELECT create_hypertable('metrics.predictions', 'time', if_not_exists => TRUE);

-- Create drift_scores table (hypertable)
CREATE TABLE IF NOT EXISTS metrics.drift_scores (
    time TIMESTAMPTZ NOT NULL,
    model_id UUID NOT NULL,
    deployment_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    feature_name VARCHAR(255),
    drift_score DOUBLE PRECISION,
    drift_type VARCHAR(50),
    threshold DOUBLE PRECISION,
    is_drifted BOOLEAN
);

SELECT create_hypertable('metrics.drift_scores', 'time', if_not_exists => TRUE);

-- Create system_metrics table (hypertable)
CREATE TABLE IF NOT EXISTS metrics.system_metrics (
    time TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION,
    labels JSONB
);

SELECT create_hypertable('metrics.system_metrics', 'time', if_not_exists => TRUE);

-- Create continuous aggregates for hourly rollups
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics.predictions_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    model_id,
    deployment_id,
    tenant_id,
    COUNT(*) as prediction_count,
    AVG(latency_ms) as avg_latency,
    MAX(latency_ms) as max_latency,
    MIN(latency_ms) as min_latency,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency
FROM metrics.predictions
GROUP BY bucket, model_id, deployment_id, tenant_id
WITH NO DATA;

-- Add retention policy (keep raw data for 30 days)
SELECT add_retention_policy('metrics.predictions', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics.drift_scores', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics.system_metrics', INTERVAL '7 days', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_predictions_model_time ON metrics.predictions (model_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_deployment_time ON metrics.predictions (deployment_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_drift_model_time ON metrics.drift_scores (model_id, time DESC);

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB initialized with hypertables and retention policies';
END $$;
