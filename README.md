# Foundry MLOps Platform

<div align="center">

**Enterprise-grade Machine Learning Operations Platform**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://docker.com)

[What Is This?](#what-is-this) •
[Quick Start](#quick-start) •
[Features](#features) •
[Architecture](#architecture) •
[API Docs](#api-documentation)

</div>

---

## What Is This?

**Foundry is a management platform for machine learning models** — think of it like a control center for AI/ML in production.

### The Problem

When companies use machine learning, they run into problems that regular software doesn't have:

| Problem | What Foundry Does |
|---------|-------------------|
| "Which version of the model is running right now?" | Tracks all versions like Git does for code |
| "Our predictions suddenly got worse" | Monitors accuracy and alerts you when it drops |
| "We want to test a new model without breaking production" | Lets you send 10% of traffic to the new model first |
| "What settings did we use when we trained this?" | Logs all parameters, results, and files |
| "Training and production compute features differently" | Single source of truth for all ML inputs |

### What Foundry Does vs. What You Do

| You Do | Foundry Does |
|--------|--------------|
| Train models (PyTorch, TensorFlow, scikit-learn) | Store and version those models |
| Write ML code in notebooks or scripts | Track your experiments and results |
| Decide which algorithms to use | Deploy models as APIs |
| Label and prepare your data | Monitor performance and send alerts |
| Run training on your GPUs/cloud | Manage traffic between model versions |

**In short:** You create the models. Foundry manages everything after that.

### Where Do Models Come From?

Foundry doesn't create models — you bring them from:

- **Your own training code** — Python scripts using PyTorch, TensorFlow, scikit-learn, XGBoost, etc.
- **Jupyter notebooks** — Train, evaluate, export, then register in Foundry
- **Pre-trained models** — Download from Hugging Face, PyTorch Hub, TensorFlow Hub, then fine-tune
- **AutoML tools** — H2O, AutoGluon, Google AutoML, etc.
- **Cloud ML services** — AWS SageMaker, Google Vertex AI, Azure ML

Example workflow:
```
1. Train model in Jupyter notebook
2. Save model file (model.pkl, model.pt, etc.)
3. Register in Foundry via API
4. Deploy through Foundry dashboard
5. Monitor in Foundry
```

---

## Quick Start

### Prerequisites

- **Docker Desktop** (with Docker Compose)
- **8GB+ RAM** available for containers

### One Command to Run Everything

**Windows:**
```bash
git clone https://github.com/YOUR_USERNAME/foundry.git
cd foundry
start.bat
```

**Linux/Mac:**
```bash
git clone https://github.com/YOUR_USERNAME/foundry.git
cd foundry
chmod +x start.sh && ./start.sh
```

**With Make:**
```bash
make dev
```

That's it! The entire platform will start.

### Access the Platform

| Service | URL | Credentials |
|---------|-----|-------------|
| **Dashboard** | http://localhost:3000 | - |
| **API** | http://localhost:8000 | - |
| **API Docs (Swagger)** | http://localhost:8000/docs | - |
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Jaeger (Tracing)** | http://localhost:16686 | - |
| **Kafka UI** | http://localhost:8090 | - |
| **MinIO Console** | http://localhost:9001 | foundry_minio / foundry_minio_password |
| **Mailhog (Email)** | http://localhost:8025 | - |

### Stop the Platform

```bash
# Windows
stop.bat

# Linux/Mac
./stop.sh

# With Make
make dev-down
```

---

## Features

### Experiment Tracking
- Track ML experiments with parameters, metrics, and artifacts
- Compare runs side-by-side with interactive visualizations
- Automatic versioning and lineage tracking
- Tag and organize experiments

### Model Registry
- Version models with semantic versioning
- Stage transitions: Development → Staging → Production
- Model lineage and dependency tracking
- Artifact storage with S3/MinIO

### Feature Store
- Centralized feature definitions and management
- Online serving (Redis) for real-time inference
- Offline serving (PostgreSQL) for batch training
- Feature versioning and freshness monitoring
- Point-in-time correct feature retrieval

### Model Deployment
- Blue/Green deployments with zero downtime
- Canary releases with traffic splitting
- A/B testing infrastructure
- Auto-scaling based on load
- Kubernetes-native deployment

### Monitoring and Observability
- Real-time metrics dashboards (Grafana)
- Data drift detection with alerting
- Model performance monitoring
- Distributed tracing (Jaeger)
- Custom alert rules (Prometheus + Alertmanager)

### Pipeline Orchestration
- DAG-based training pipelines
- Scheduled and event-triggered runs
- Pipeline versioning
- Automatic retraining triggers

### Multi-Tenancy and Security
- Full tenant isolation
- Role-based access control (RBAC)
- JWT authentication with refresh tokens
- API key management
- Audit logging

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FOUNDRY MLOps PLATFORM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │   Dashboard     │    │    API Gateway   │    │   Grafana       │         │
│  │   (Next.js)     │───▶│    (FastAPI)     │◀───│   Dashboards    │         │
│  │   Port: 3000    │    │   Port: 8000     │    │   Port: 3001    │         │
│  └─────────────────┘    └────────┬─────────┘    └─────────────────┘         │
│                                  │                                          │
│         ┌────────────────────────┼────────────────────────┐                 │
│         │                        │                        │                 │
│         ▼                        ▼                        ▼                 │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│  │ Experiments │         │   Models    │         │  Features   │           │
│  │   Service   │         │  Registry   │         │   Store     │           │
│  └─────────────┘         └─────────────┘         └─────────────┘           │
│         │                        │                        │                 │
│         └────────────────────────┼────────────────────────┘                 │
│                                  │                                          │
│  ┌───────────────────────────────┼───────────────────────────────┐         │
│  │                     DATA LAYER                                 │         │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │         │
│  │  │PostgreSQL│  │TimescaleDB│ │  Redis   │  │  MinIO   │      │         │
│  │  │  (Main)  │  │ (Metrics)│  │ (Cache)  │  │(Artifacts)│      │         │
│  │  │  :5432   │  │  :5433   │  │  :6379   │  │  :9000   │      │         │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────┐         │
│  │                     EVENT STREAMING                            │         │
│  │  ┌──────────────────────────────────────────────────────┐     │         │
│  │  │                    Apache Kafka                       │     │         │
│  │  │  Topics: predictions, drift-events, training-triggers │     │         │
│  │  │          alerts, audit, feature-updates, model-events │     │         │
│  │  └──────────────────────────────────────────────────────┘     │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────┐         │
│  │                     OBSERVABILITY                              │         │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │         │
│  │  │ Prometheus │  │Alertmanager│  │   Jaeger   │              │         │
│  │  │  :9090     │  │   :9093    │  │  :16686    │              │         │
│  │  └────────────┘  └────────────┘  └────────────┘              │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Each Service Does

| Service | Port | Purpose |
|---------|------|---------|
| **Dashboard** | 3000 | Web interface you interact with |
| **API** | 8000 | REST API that powers everything |
| **PostgreSQL** | 5432 | Main database for users, experiments, models |
| **TimescaleDB** | 5433 | Time-series data (latency over time, etc.) |
| **Redis** | 6379 | Fast cache and real-time feature serving |
| **MinIO** | 9001 | File storage for model artifacts (S3-compatible) |
| **Kafka** | 9092 | Event streaming for real-time processing |
| **Prometheus** | 9090 | Collects metrics from all services |
| **Grafana** | 3001 | Visualizes metrics in dashboards |
| **Alertmanager** | 9093 | Routes alerts to Slack, email, PagerDuty |
| **Jaeger** | 16686 | Traces requests across services for debugging |

---

## Project Structure

```
foundry/
├── backend/                      # FastAPI Backend
│   ├── src/foundry/
│   │   ├── api/v1/              # API routes
│   │   │   ├── experiments.py   # Experiment endpoints
│   │   │   ├── models.py        # Model registry endpoints
│   │   │   ├── features.py      # Feature store endpoints
│   │   │   ├── deployments.py   # Deployment endpoints
│   │   │   ├── monitoring.py    # Monitoring endpoints
│   │   │   └── pipelines.py     # Pipeline endpoints
│   │   ├── core/                # Core utilities
│   │   │   ├── config.py        # Configuration
│   │   │   └── security.py      # Auth & security
│   │   ├── infrastructure/      # Infrastructure layer
│   │   │   ├── database/        # SQLAlchemy models
│   │   │   └── celery/          # Background tasks
│   │   └── main.py              # FastAPI app
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suites
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                     # Next.js Dashboard
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── (auth)/          # Auth pages (login, register)
│   │   │   └── (dashboard)/     # Dashboard pages
│   │   │       ├── experiments/ # Experiment tracking UI
│   │   │       ├── models/      # Model registry UI
│   │   │       ├── features/    # Feature store UI
│   │   │       ├── deployments/ # Deployment UI
│   │   │       ├── monitoring/  # Monitoring dashboards
│   │   │       └── settings/    # Settings UI
│   │   ├── components/          # React components
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   ├── layout/          # Layout components
│   │   │   └── shared/          # Shared components
│   │   └── lib/                 # Utilities
│   ├── Dockerfile
│   └── package.json
│
├── infrastructure/               # Deployment Configs
│   ├── kubernetes/              # K8s manifests
│   └── terraform/               # Infrastructure as Code
│
├── monitoring/                   # Observability Configs
│   ├── prometheus/              # Scrape configs and alert rules
│   ├── grafana/                 # Datasources and dashboards
│   └── alertmanager/            # Alert routing
│
├── scripts/                      # Init scripts
│   ├── init-db.sql              # PostgreSQL init
│   └── init-timescaledb.sql     # TimescaleDB init
│
├── docker-compose.yml           # Run everything locally
├── Makefile                     # Common commands
├── start.bat / start.sh         # Startup scripts
├── stop.bat / stop.sh           # Stop scripts
├── .env.example                 # Environment template
└── README.md
```

---

## API Documentation

### Core Endpoints

#### Experiments
```
POST   /api/v1/experiments              Create experiment
GET    /api/v1/experiments              List experiments
GET    /api/v1/experiments/{id}         Get experiment
PUT    /api/v1/experiments/{id}         Update experiment
DELETE /api/v1/experiments/{id}         Delete experiment
POST   /api/v1/experiments/{id}/runs    Create run
GET    /api/v1/experiments/{id}/runs    List runs
POST   /api/v1/runs/{id}/metrics        Log metrics
POST   /api/v1/runs/{id}/artifacts      Upload artifact
```

#### Model Registry
```
POST   /api/v1/models                   Register model
GET    /api/v1/models                   List models
GET    /api/v1/models/{id}              Get model
POST   /api/v1/models/{id}/versions     Create version
PUT    /api/v1/models/{id}/versions/{v}/stage   Transition stage
```

#### Feature Store
```
POST   /api/v1/feature-groups           Create feature group
GET    /api/v1/feature-groups           List feature groups
POST   /api/v1/features                 Create feature
GET    /api/v1/features/online/{key}    Get online features
POST   /api/v1/features/offline         Get offline features (batch)
```

#### Deployments
```
POST   /api/v1/deployments              Create deployment
GET    /api/v1/deployments              List deployments
GET    /api/v1/deployments/{id}         Get deployment
PUT    /api/v1/deployments/{id}/scale   Scale deployment
POST   /api/v1/deployments/{id}/rollback Rollback deployment
```

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Tech Stack

### Backend
- **FastAPI** - High-performance async Python web framework
- **SQLAlchemy 2.0** - Async ORM with PostgreSQL
- **Alembic** - Database migrations
- **Celery** - Distributed task queue
- **Pydantic** - Data validation

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **shadcn/ui** - UI component library
- **TailwindCSS** - Styling
- **TanStack Table** - Data tables
- **Recharts** - Charts and visualizations

### Data Layer
- **PostgreSQL 16** - Primary database
- **TimescaleDB** - Time-series metrics
- **Redis 7** - Caching and feature store
- **MinIO** - S3-compatible object storage
- **Apache Kafka** - Event streaming

### Observability
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards and visualization
- **Alertmanager** - Alert routing
- **Jaeger** - Distributed tracing

### Infrastructure
- **Docker** - Containerization
- **Kubernetes** - Container orchestration
- **Terraform** - Infrastructure as Code
- **GitHub Actions** - CI/CD (optional)

---

## Deployment

### Local Development

```bash
# Start everything
make dev

# View logs
make dev-logs

# Stop everything
make dev-down

# Reset (removes all data)
make dev-reset
```

### Production Deployment

#### Kubernetes

```bash
# Deploy to dev cluster
make deploy-dev

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-prod

# Check status
make k8s-status

# Rollback if needed
make rollback
```

#### Terraform (AWS)

```bash
# Initialize
make tf-init ENV=production

# Plan changes
make tf-plan ENV=production

# Apply
make tf-apply ENV=production
```

---

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Key Environment Variables

```env
# Database
POSTGRES_USER=foundry
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=foundry

# Redis
REDIS_PASSWORD=your-secure-password

# MinIO (S3)
MINIO_ROOT_USER=foundry_minio
MINIO_ROOT_PASSWORD=your-secure-password

# Security
JWT_SECRET_KEY=generate-with-openssl-rand-base64-64

# Environment
ENVIRONMENT=production
```

**Important**: Change all default passwords before deploying to production!

---

## Testing

```bash
# Run all tests
make test

# Backend tests only
make test-backend

# Frontend tests only
make test-frontend

# With coverage report
make test-coverage
```

---

## Monitoring

### Grafana Dashboards

Pre-configured dashboards included:
- **Foundry Overview** - System health, request rates, latencies
- **Inference Metrics** - Model performance, throughput, latency percentiles
- **Drift Detection** - Feature drift scores over time
- **Infrastructure** - Database, cache, queue metrics

### Alerting

Alerts configured in Prometheus:
- High API latency (p99 > 500ms)
- High error rate (> 1%)
- Data drift detected
- Database connection pool exhaustion
- Redis memory usage high
- Kafka consumer lag

---

## Security

- **Authentication**: JWT with access/refresh tokens
- **Authorization**: Role-based access control (Admin, User, Viewer)
- **Encryption**: TLS for all connections
- **Secrets**: Environment variables (Vault in production)
- **Audit**: Full audit logging for compliance
- **Multi-tenancy**: Complete tenant isolation

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">
Built for the ML community
</div>
