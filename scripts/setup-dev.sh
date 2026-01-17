#!/bin/bash
# =============================================================================
# Foundry MLOps Platform - Development Environment Setup Script
# =============================================================================
# This script initializes the local development environment for Foundry.
# It handles Docker services, database migrations, and initial configuration.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

wait_for_service() {
    local service=$1
    local host=$2
    local port=$3
    local max_attempts=${4:-30}
    local attempt=1

    log_info "Waiting for $service to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "$service is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "$service failed to start within expected time"
    return 1
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check required commands
    check_command docker
    check_command docker-compose
    check_command python3
    check_command pip3

    # Check Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi

    # Check disk space (need at least 10GB free)
    free_space=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$free_space" -lt 10 ]; then
        log_warning "Low disk space: ${free_space}GB free. Recommended: 10GB+"
    fi

    log_success "Pre-flight checks passed!"
}

# =============================================================================
# Environment Setup
# =============================================================================

setup_environment() {
    log_info "Setting up environment..."

    # Create .env file if it doesn't exist
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            log_info "Created .env file from .env.example"
        else
            log_warning ".env.example not found, creating default .env"
            cat > "$PROJECT_ROOT/.env" << 'EOF'
# Foundry Development Environment
APP_ENV=development
LOG_LEVEL=DEBUG

# PostgreSQL
POSTGRES_USER=foundry
POSTGRES_PASSWORD=foundry_dev_password
POSTGRES_DB=foundry
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# TimescaleDB
TIMESCALE_USER=foundry_ts
TIMESCALE_PASSWORD=foundry_ts_password
TIMESCALE_DB=foundry_metrics

# Redis
REDIS_PASSWORD=foundry_redis_password
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ROOT_USER=foundry_minio
MINIO_ROOT_PASSWORD=foundry_minio_password

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# JWT
JWT_SECRET_KEY=dev_secret_key_change_in_production
EOF
        fi
    else
        log_info ".env file already exists"
    fi

    # Source environment
    set -a
    source "$PROJECT_ROOT/.env"
    set +a

    log_success "Environment configured!"
}

# =============================================================================
# Docker Services
# =============================================================================

start_docker_services() {
    log_info "Starting Docker services..."

    cd "$PROJECT_ROOT"

    # Pull latest images
    log_info "Pulling Docker images..."
    docker-compose pull

    # Start services
    log_info "Starting containers..."
    docker-compose up -d

    # Wait for services to be ready
    wait_for_service "PostgreSQL" localhost 5432 60
    wait_for_service "TimescaleDB" localhost 5433 60
    wait_for_service "Redis" localhost 6379 30
    wait_for_service "MinIO" localhost 9000 30
    wait_for_service "Kafka" localhost 9092 60
    wait_for_service "Prometheus" localhost 9090 30
    wait_for_service "Grafana" localhost 3001 30

    log_success "All Docker services are running!"
}

stop_docker_services() {
    log_info "Stopping Docker services..."
    cd "$PROJECT_ROOT"
    docker-compose down
    log_success "Docker services stopped!"
}

# =============================================================================
# Database Setup
# =============================================================================

setup_database() {
    log_info "Setting up database..."

    # Wait a bit for PostgreSQL to fully initialize
    sleep 5

    # Run Alembic migrations
    cd "$PROJECT_ROOT/backend"

    # Create Python virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    log_info "Installing Python dependencies..."
    pip install --upgrade pip
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        pip install alembic asyncpg sqlalchemy psycopg2-binary
    fi

    # Run migrations
    log_info "Running database migrations..."
    alembic upgrade head

    deactivate

    log_success "Database setup complete!"
}

# =============================================================================
# Initialize Data
# =============================================================================

initialize_data() {
    log_info "Initializing sample data..."

    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate

    # Run seed script
    if [ -f "$PROJECT_ROOT/scripts/seed-data.py" ]; then
        python "$PROJECT_ROOT/scripts/seed-data.py"
    else
        log_warning "Seed data script not found, skipping..."
    fi

    deactivate

    log_success "Data initialization complete!"
}

# =============================================================================
# Create Init SQL Scripts
# =============================================================================

create_init_scripts() {
    log_info "Creating database initialization scripts..."

    # PostgreSQL init script
    mkdir -p "$PROJECT_ROOT/scripts"

    cat > "$PROJECT_ROOT/scripts/init-db.sql" << 'EOF'
-- Foundry MLOps Platform - PostgreSQL Initialization
-- This script runs when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS foundry;

-- Grant privileges
GRANT ALL PRIVILEGES ON SCHEMA foundry TO foundry;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA foundry TO foundry;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA foundry TO foundry;

-- Set search path
ALTER DATABASE foundry SET search_path TO foundry, public;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL initialization complete';
END $$;
EOF

    # TimescaleDB init script
    cat > "$PROJECT_ROOT/scripts/init-timescaledb.sql" << 'EOF'
-- Foundry MLOps Platform - TimescaleDB Initialization
-- This script runs when the TimescaleDB container is first created

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create prediction logs table
CREATE TABLE IF NOT EXISTS prediction_logs (
    time TIMESTAMPTZ NOT NULL,
    deployment_id UUID NOT NULL,
    model_version_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    request_id UUID NOT NULL,
    input_features JSONB NOT NULL,
    prediction JSONB NOT NULL,
    latency_ms INTEGER NOT NULL,
    ground_truth JSONB
);

-- Convert to hypertable
SELECT create_hypertable('prediction_logs', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_prediction_logs_deployment
    ON prediction_logs (deployment_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_tenant
    ON prediction_logs (tenant_id, time DESC);

-- Create drift scores table
CREATE TABLE IF NOT EXISTS drift_scores_ts (
    time TIMESTAMPTZ NOT NULL,
    deployment_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    feature_name VARCHAR(255),
    drift_score DOUBLE PRECISION,
    drift_method VARCHAR(50),
    status VARCHAR(50)
);

-- Convert to hypertable
SELECT create_hypertable('drift_scores_ts', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_drift_scores_deployment
    ON drift_scores_ts (deployment_id, time DESC);

-- Create continuous aggregates for predictions
CREATE MATERIALIZED VIEW IF NOT EXISTS prediction_stats_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    deployment_id,
    COUNT(*) AS request_count,
    AVG(latency_ms) AS avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_latency_ms
FROM prediction_logs
GROUP BY bucket, deployment_id
WITH NO DATA;

-- Set up refresh policy
SELECT add_continuous_aggregate_policy('prediction_stats_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Create retention policy (keep 90 days of detailed data)
SELECT add_retention_policy('prediction_logs', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('drift_scores_ts', INTERVAL '365 days', if_not_exists => TRUE);

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'TimescaleDB initialization complete';
END $$;
EOF

    log_success "Init scripts created!"
}

# =============================================================================
# Health Check
# =============================================================================

health_check() {
    log_info "Running health checks..."

    local all_healthy=true

    # Check PostgreSQL
    if docker exec foundry-postgres pg_isready -U foundry &> /dev/null; then
        log_success "PostgreSQL: healthy"
    else
        log_error "PostgreSQL: unhealthy"
        all_healthy=false
    fi

    # Check TimescaleDB
    if docker exec foundry-timescaledb pg_isready -U foundry_ts &> /dev/null; then
        log_success "TimescaleDB: healthy"
    else
        log_error "TimescaleDB: unhealthy"
        all_healthy=false
    fi

    # Check Redis
    if docker exec foundry-redis redis-cli -a "$REDIS_PASSWORD" ping &> /dev/null; then
        log_success "Redis: healthy"
    else
        log_error "Redis: unhealthy"
        all_healthy=false
    fi

    # Check MinIO
    if curl -s http://localhost:9000/minio/health/live &> /dev/null; then
        log_success "MinIO: healthy"
    else
        log_warning "MinIO: may still be initializing"
    fi

    # Check Kafka
    if docker exec foundry-kafka kafka-topics --bootstrap-server localhost:9092 --list &> /dev/null; then
        log_success "Kafka: healthy"
    else
        log_error "Kafka: unhealthy"
        all_healthy=false
    fi

    if [ "$all_healthy" = true ]; then
        log_success "All services are healthy!"
    else
        log_warning "Some services are unhealthy. Check the logs."
    fi
}

# =============================================================================
# Print Service URLs
# =============================================================================

print_urls() {
    echo ""
    echo "=============================================="
    echo "  Foundry Development Environment"
    echo "=============================================="
    echo ""
    echo "Services:"
    echo "  PostgreSQL:    localhost:5432"
    echo "  TimescaleDB:   localhost:5433"
    echo "  Redis:         localhost:6379"
    echo "  MinIO Console: http://localhost:9001"
    echo "  MinIO API:     http://localhost:9000"
    echo "  Kafka:         localhost:9092"
    echo "  Kafka UI:      http://localhost:8090"
    echo "  Prometheus:    http://localhost:9090"
    echo "  Grafana:       http://localhost:3001"
    echo "  Alertmanager:  http://localhost:9093"
    echo "  Jaeger:        http://localhost:16686"
    echo "  Mailhog:       http://localhost:8025"
    echo ""
    echo "Credentials:"
    echo "  PostgreSQL:  foundry / foundry_dev_password"
    echo "  MinIO:       foundry_minio / foundry_minio_password"
    echo "  Grafana:     admin / admin"
    echo ""
    echo "=============================================="
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "  Foundry MLOps Platform - Dev Setup"
    echo "=============================================="
    echo ""

    case "${1:-}" in
        start)
            preflight_checks
            setup_environment
            create_init_scripts
            start_docker_services
            setup_database
            health_check
            print_urls
            ;;
        stop)
            stop_docker_services
            ;;
        restart)
            stop_docker_services
            start_docker_services
            health_check
            print_urls
            ;;
        status)
            health_check
            print_urls
            ;;
        reset)
            stop_docker_services
            log_info "Removing Docker volumes..."
            docker-compose down -v
            log_info "Starting fresh..."
            start_docker_services
            setup_database
            initialize_data
            health_check
            print_urls
            ;;
        logs)
            docker-compose logs -f "${2:-}"
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|reset|logs [service]}"
            echo ""
            echo "Commands:"
            echo "  start   - Start all development services"
            echo "  stop    - Stop all development services"
            echo "  restart - Restart all services"
            echo "  status  - Check health of all services"
            echo "  reset   - Remove all data and start fresh"
            echo "  logs    - View logs (optionally specify service)"
            exit 1
            ;;
    esac
}

main "$@"
