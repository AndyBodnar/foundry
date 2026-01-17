@echo off
echo ============================================
echo   FOUNDRY MLOps Platform - Starting...
echo ============================================
echo.

REM Check if Docker is running
docker info > nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Check if .env exists, if not copy from example
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo WARNING: Default passwords are being used. Edit .env for production!
    echo.
)

echo Building and starting all services...
echo This may take a few minutes on first run.
echo.

docker compose up --build -d

echo.
echo ============================================
echo   FOUNDRY MLOps Platform - Running!
echo ============================================
echo.
echo Services:
echo   Dashboard:    http://localhost:3000
echo   API:          http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo   Grafana:      http://localhost:3001 (admin/admin)
echo   Kafka UI:     http://localhost:8090
echo   MinIO:        http://localhost:9001
echo   Jaeger:       http://localhost:16686
echo   Prometheus:   http://localhost:9090
echo   Mailhog:      http://localhost:8025
echo.
echo To view logs:   docker compose logs -f
echo To stop:        docker compose down
echo.
pause
