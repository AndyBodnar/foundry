-- Foundry PostgreSQL Initialization Script
-- This script runs on first database initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE foundry TO foundry;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS foundry;

-- Set search path
ALTER DATABASE foundry SET search_path TO foundry, public;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Foundry database initialized successfully';
END $$;
