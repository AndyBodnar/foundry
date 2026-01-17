#!/usr/bin/env python3
"""
Foundry MLOps Platform - Seed Data Script
==========================================
This script populates the database with sample data for development and testing.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Optional
import random
import hashlib
import secrets
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import asyncpg
except ImportError:
    print("Installing asyncpg...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "asyncpg"])
    import asyncpg


# =============================================================================
# Configuration
# =============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://foundry:foundry_dev_password@localhost:5432/foundry"
)

# Parse database URL
def parse_database_url(url: str) -> dict:
    """Parse database URL into connection parameters."""
    # Remove postgresql:// prefix
    url = url.replace("postgresql://", "")

    # Split user:pass@host:port/db
    auth, rest = url.split("@")
    user, password = auth.split(":")
    host_port, database = rest.split("/")
    host, port = host_port.split(":")

    return {
        "user": user,
        "password": password,
        "host": host,
        "port": int(port),
        "database": database
    }


# =============================================================================
# Sample Data Generators
# =============================================================================

def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    """Generate a hashed password."""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key and its hash."""
    key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    prefix = key[:8]
    return key, key_hash, prefix


# =============================================================================
# Data Definitions
# =============================================================================

# Tenants
TENANTS = [
    {
        "name": "Demo Organization",
        "slug": "demo-org",
        "status": "ACTIVE",
        "settings": '{"theme": "dark", "notifications_enabled": true}',
        "quotas": '{"max_experiments": 100, "max_models": 50, "max_deployments": 10}'
    },
    {
        "name": "Acme Corp",
        "slug": "acme-corp",
        "status": "ACTIVE",
        "settings": '{"theme": "light"}',
        "quotas": '{"max_experiments": 500, "max_models": 100, "max_deployments": 25}'
    }
]

# Users
USERS = [
    {
        "email": "admin@foundry.ai",
        "name": "Admin User",
        "password": "admin123",
        "is_active": True,
        "is_superuser": True,
        "email_verified": True
    },
    {
        "email": "alice@demo-org.com",
        "name": "Alice Data Scientist",
        "password": "alice123",
        "is_active": True,
        "is_superuser": False,
        "email_verified": True
    },
    {
        "email": "bob@demo-org.com",
        "name": "Bob ML Engineer",
        "password": "bob123",
        "is_active": True,
        "is_superuser": False,
        "email_verified": True
    }
]

# Sample experiments
EXPERIMENTS = [
    {
        "name": "fraud-detection-v2",
        "description": "Fraud detection model using XGBoost",
        "tags": ["fraud", "xgboost", "classification"]
    },
    {
        "name": "customer-churn",
        "description": "Customer churn prediction model",
        "tags": ["churn", "classification", "lightgbm"]
    },
    {
        "name": "demand-forecasting",
        "description": "Time series demand forecasting",
        "tags": ["forecasting", "time-series", "prophet"]
    },
    {
        "name": "recommendation-engine",
        "description": "Product recommendation system",
        "tags": ["recommendation", "collaborative-filtering"]
    }
]

# Sample models
MODELS = [
    {
        "name": "fraud-detector",
        "description": "XGBoost-based fraud detection model"
    },
    {
        "name": "churn-predictor",
        "description": "LightGBM customer churn prediction"
    },
    {
        "name": "demand-forecaster",
        "description": "Prophet time series model"
    }
]

# Sample feature views
FEATURE_VIEWS = [
    {
        "name": "user_features",
        "description": "User profile and behavior features",
        "entities": ["user_id"],
        "features": '{"age": "int", "account_age_days": "int", "total_transactions": "int", "avg_transaction_amount": "float"}',
        "source_config": '{"type": "postgres", "table": "user_features"}'
    },
    {
        "name": "transaction_features",
        "description": "Transaction-level features",
        "entities": ["transaction_id", "user_id"],
        "features": '{"amount": "float", "merchant_category": "string", "is_international": "bool", "time_since_last_transaction": "float"}',
        "source_config": '{"type": "kafka", "topic": "transactions"}'
    }
]


# =============================================================================
# Database Seeding Functions
# =============================================================================

async def seed_tenants(conn) -> dict:
    """Seed tenants and return mapping of slug to ID."""
    print("Seeding tenants...")
    tenant_ids = {}

    for tenant in TENANTS:
        tenant_id = generate_uuid()
        await conn.execute("""
            INSERT INTO tenants (id, name, slug, status, settings, quotas)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
            ON CONFLICT (slug) DO NOTHING
        """, tenant_id, tenant["name"], tenant["slug"], tenant["status"],
            tenant["settings"], tenant["quotas"])

        # Get the actual ID (might already exist)
        row = await conn.fetchrow(
            "SELECT id FROM tenants WHERE slug = $1", tenant["slug"]
        )
        tenant_ids[tenant["slug"]] = str(row["id"])
        print(f"  Created tenant: {tenant['name']}")

    return tenant_ids


async def seed_users(conn, tenant_ids: dict) -> dict:
    """Seed users and return mapping of email to ID."""
    print("Seeding users...")
    user_ids = {}

    for user in USERS:
        user_id = generate_uuid()
        hashed_password = hash_password(user["password"])

        await conn.execute("""
            INSERT INTO users (id, email, name, hashed_password, is_active, is_superuser, email_verified)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (email) DO NOTHING
        """, user_id, user["email"], user["name"], hashed_password,
            user["is_active"], user["is_superuser"], user["email_verified"])

        # Get the actual ID
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", user["email"]
        )
        user_ids[user["email"]] = str(row["id"])
        print(f"  Created user: {user['email']}")

    # Create tenant memberships
    print("Creating tenant memberships...")
    demo_tenant_id = tenant_ids["demo-org"]

    # Admin is owner of demo org
    await conn.execute("""
        INSERT INTO tenant_memberships (id, tenant_id, user_id, role)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (tenant_id, user_id) DO NOTHING
    """, generate_uuid(), demo_tenant_id, user_ids["admin@foundry.ai"], "OWNER")

    # Alice is a member
    await conn.execute("""
        INSERT INTO tenant_memberships (id, tenant_id, user_id, role)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (tenant_id, user_id) DO NOTHING
    """, generate_uuid(), demo_tenant_id, user_ids["alice@demo-org.com"], "MEMBER")

    # Bob is a member
    await conn.execute("""
        INSERT INTO tenant_memberships (id, tenant_id, user_id, role)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (tenant_id, user_id) DO NOTHING
    """, generate_uuid(), demo_tenant_id, user_ids["bob@demo-org.com"], "MEMBER")

    return user_ids


async def seed_experiments(conn, tenant_id: str, user_id: str) -> dict:
    """Seed experiments and runs."""
    print("Seeding experiments...")
    experiment_ids = {}

    for exp in EXPERIMENTS:
        exp_id = generate_uuid()
        tags = "{" + ",".join(exp["tags"]) + "}"

        await conn.execute("""
            INSERT INTO experiments (id, tenant_id, name, description, tags, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (tenant_id, name) DO NOTHING
        """, exp_id, tenant_id, exp["name"], exp["description"], tags, user_id)

        # Get actual ID
        row = await conn.fetchrow(
            "SELECT id FROM experiments WHERE tenant_id = $1 AND name = $2",
            tenant_id, exp["name"]
        )
        experiment_ids[exp["name"]] = str(row["id"])
        print(f"  Created experiment: {exp['name']}")

        # Create some runs for each experiment
        for i in range(3):
            run_id = generate_uuid()
            status = random.choice(["COMPLETED", "COMPLETED", "COMPLETED", "FAILED"])
            params = f'{{"learning_rate": {random.uniform(0.001, 0.1):.4f}, "epochs": {random.randint(10, 100)}}}'
            metrics = f'{{"accuracy": {random.uniform(0.85, 0.99):.4f}, "f1_score": {random.uniform(0.80, 0.95):.4f}}}'

            start_time = datetime.now() - timedelta(days=random.randint(1, 30))
            end_time = start_time + timedelta(hours=random.randint(1, 24))

            await conn.execute("""
                INSERT INTO runs (id, experiment_id, tenant_id, name, status, parameters, metrics, user_id, start_time, end_time)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $10)
            """, run_id, row["id"], tenant_id, f"run-{i+1}", status, params, metrics, user_id, start_time, end_time)

        print(f"    Created 3 runs for {exp['name']}")

    return experiment_ids


async def seed_models(conn, tenant_id: str, user_id: str) -> dict:
    """Seed registered models and versions."""
    print("Seeding models...")
    model_ids = {}

    for model in MODELS:
        model_id = generate_uuid()

        await conn.execute("""
            INSERT INTO registered_models (id, tenant_id, name, description, created_by)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tenant_id, name) DO NOTHING
        """, model_id, tenant_id, model["name"], model["description"], user_id)

        # Get actual ID
        row = await conn.fetchrow(
            "SELECT id FROM registered_models WHERE tenant_id = $1 AND name = $2",
            tenant_id, model["name"]
        )
        model_ids[model["name"]] = str(row["id"])
        print(f"  Created model: {model['name']}")

        # Create versions
        for v in range(1, 4):
            version_id = generate_uuid()
            version = f"v{v}.0.0"
            stage = "NONE" if v < 2 else ("STAGING" if v == 2 else "PRODUCTION")
            metrics = f'{{"accuracy": {0.85 + v * 0.03:.4f}, "latency_ms": {random.randint(10, 50)}}}'

            await conn.execute("""
                INSERT INTO model_versions (id, model_id, tenant_id, version, stage, artifact_path, metrics, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
            """, version_id, row["id"], tenant_id, version, stage,
                f"s3://foundry-models/{model['name']}/{version}/model.pkl", metrics, user_id)

        print(f"    Created 3 versions for {model['name']}")

    return model_ids


async def seed_feature_views(conn, tenant_id: str, user_id: str) -> dict:
    """Seed feature views and services."""
    print("Seeding feature views...")
    feature_view_ids = {}

    for fv in FEATURE_VIEWS:
        fv_id = generate_uuid()
        entities = "{" + ",".join(fv["entities"]) + "}"

        await conn.execute("""
            INSERT INTO feature_views (id, tenant_id, name, description, entities, features, source_config, created_by)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8)
            ON CONFLICT (tenant_id, name) DO NOTHING
        """, fv_id, tenant_id, fv["name"], fv["description"], entities,
            fv["features"], fv["source_config"], user_id)

        row = await conn.fetchrow(
            "SELECT id FROM feature_views WHERE tenant_id = $1 AND name = $2",
            tenant_id, fv["name"]
        )
        feature_view_ids[fv["name"]] = str(row["id"])
        print(f"  Created feature view: {fv['name']}")

    return feature_view_ids


async def seed_deployments(conn, tenant_id: str, user_id: str, model_ids: dict) -> dict:
    """Seed deployments."""
    print("Seeding deployments...")
    deployment_ids = {}

    deployments = [
        {
            "name": "fraud-detector-prod",
            "model_name": "fraud-detector",
            "status": "RUNNING",
            "config": '{"replicas": 3, "cpu": "1", "memory": "2Gi"}',
            "traffic_config": '{"default_version": "v3.0.0", "traffic_split": {"v3.0.0": 100}}'
        },
        {
            "name": "churn-predictor-staging",
            "model_name": "churn-predictor",
            "status": "RUNNING",
            "config": '{"replicas": 1, "cpu": "500m", "memory": "1Gi"}',
            "traffic_config": '{"default_version": "v2.0.0", "traffic_split": {"v2.0.0": 100}}'
        }
    ]

    for dep in deployments:
        dep_id = generate_uuid()

        await conn.execute("""
            INSERT INTO deployments (id, tenant_id, name, status, config, traffic_config, created_by)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)
            ON CONFLICT (tenant_id, name) DO NOTHING
        """, dep_id, tenant_id, dep["name"], dep["status"], dep["config"],
            dep["traffic_config"], user_id)

        row = await conn.fetchrow(
            "SELECT id FROM deployments WHERE tenant_id = $1 AND name = $2",
            tenant_id, dep["name"]
        )
        deployment_ids[dep["name"]] = str(row["id"])
        print(f"  Created deployment: {dep['name']}")

    return deployment_ids


async def seed_alerts(conn, tenant_id: str, user_id: str, deployment_ids: dict):
    """Seed alert rules."""
    print("Seeding alert rules...")

    alert_rules = [
        {
            "deployment_name": "fraud-detector-prod",
            "name": "High Latency Alert",
            "metric": "inference_latency_p99",
            "condition": "GREATER_THAN",
            "threshold": 100.0,
            "severity": "WARNING"
        },
        {
            "deployment_name": "fraud-detector-prod",
            "name": "Error Rate Alert",
            "metric": "error_rate",
            "condition": "GREATER_THAN",
            "threshold": 0.01,
            "severity": "CRITICAL"
        },
        {
            "deployment_name": "fraud-detector-prod",
            "name": "Data Drift Alert",
            "metric": "drift_score",
            "condition": "GREATER_THAN",
            "threshold": 0.3,
            "severity": "WARNING"
        }
    ]

    for alert in alert_rules:
        if alert["deployment_name"] in deployment_ids:
            alert_id = generate_uuid()

            await conn.execute("""
                INSERT INTO alert_rules (id, tenant_id, deployment_id, name, metric, condition, threshold, severity, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, alert_id, tenant_id, deployment_ids[alert["deployment_name"]],
                alert["name"], alert["metric"], alert["condition"],
                alert["threshold"], alert["severity"], user_id)

            print(f"  Created alert: {alert['name']}")


async def seed_api_keys(conn, tenant_id: str, user_id: str):
    """Seed API keys."""
    print("Seeding API keys...")

    key, key_hash, prefix = generate_api_key()

    await conn.execute("""
        INSERT INTO api_keys (id, tenant_id, user_id, name, key_hash, key_prefix, scopes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    """, generate_uuid(), tenant_id, user_id, "Development Key", key_hash, prefix,
        "{read,write,deploy}")

    print(f"  Created API key: {prefix}...")
    print(f"  Full key (save this): {key}")


async def seed_audit_logs(conn, tenant_id: str, user_id: str):
    """Seed some audit log entries."""
    print("Seeding audit logs...")

    events = [
        ("USER_LOGIN", "user", "Login successful"),
        ("EXPERIMENT_CREATED", "experiment", "Created experiment"),
        ("MODEL_REGISTERED", "model", "Registered new model"),
        ("DEPLOYMENT_CREATED", "deployment", "Created deployment"),
        ("MODEL_PROMOTED", "model_version", "Promoted to production")
    ]

    for event_type, resource_type, details in events:
        await conn.execute("""
            INSERT INTO audit_logs (id, tenant_id, user_id, event_type, resource_type, action, details, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
        """, generate_uuid(), tenant_id, user_id, event_type, resource_type, event_type,
            f'{{"message": "{details}"}}',
            datetime.now() - timedelta(hours=random.randint(1, 72)))

    print(f"  Created {len(events)} audit log entries")


# =============================================================================
# Main
# =============================================================================

async def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("Foundry MLOps Platform - Database Seeder")
    print("=" * 60)
    print()

    # Parse connection parameters
    db_params = parse_database_url(DATABASE_URL)
    print(f"Connecting to database: {db_params['host']}:{db_params['port']}/{db_params['database']}")

    try:
        # Connect to database
        conn = await asyncpg.connect(**db_params)
        print("Connected successfully!\n")

        # Seed data
        tenant_ids = await seed_tenants(conn)
        user_ids = await seed_users(conn, tenant_ids)

        # Use demo tenant for most data
        demo_tenant_id = tenant_ids["demo-org"]
        admin_user_id = user_ids["admin@foundry.ai"]

        experiment_ids = await seed_experiments(conn, demo_tenant_id, admin_user_id)
        model_ids = await seed_models(conn, demo_tenant_id, admin_user_id)
        feature_view_ids = await seed_feature_views(conn, demo_tenant_id, admin_user_id)
        deployment_ids = await seed_deployments(conn, demo_tenant_id, admin_user_id, model_ids)
        await seed_alerts(conn, demo_tenant_id, admin_user_id, deployment_ids)
        await seed_api_keys(conn, demo_tenant_id, admin_user_id)
        await seed_audit_logs(conn, demo_tenant_id, admin_user_id)

        await conn.close()

        print()
        print("=" * 60)
        print("Seeding complete!")
        print("=" * 60)
        print()
        print("You can now log in with:")
        print("  Email: admin@foundry.ai")
        print("  Password: admin123")
        print()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
