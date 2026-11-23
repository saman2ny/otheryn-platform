#!/bin/bash
# DentalPilot AI - Production Deployment Script
# Usage: ./deploy.sh [staging|production]

set -euo pipefail

ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.yml"

if [[ "$ENVIRONMENT" == "staging" ]]; then
    COMPOSE_FILE="docker-compose.yml -f docker-compose.staging.yml"
    echo "🚀 Deploying to STAGING environment..."
elif [[ "$ENVIRONMENT" == "production" ]]; then
    echo "🚀 Deploying to PRODUCTION environment..."
else
    echo "Usage: $0 [staging|production]"
    exit 1
fi

# Check for required environment file
if [[ ! -f ".env.${ENVIRONMENT}" ]]; then
    echo "❌ Missing .env.${ENVIRONMENT} file"
    echo "   Copy .env.production.example to .env.${ENVIRONMENT} and fill in values"
    exit 1
fi

# Load environment variables
set -a
source ".env.${ENVIRONMENT}"
set +a

# Verify required variables
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "JWT_SECRET"
    "ANTHROPIC_API_KEY"
    "RAZORPAY_KEY_ID"
    "RAZORPAY_KEY_SECRET"
    "RAZORPAY_WEBHOOK_SECRET"
    "S3_BUCKET"
    "SMTP_HOST"
    "SMTP_USERNAME"
    "SMTP_PASSWORD"
    "SMTP_SENDER_EMAIL"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "❌ Required variable $var is not set in .env.${ENVIRONMENT}"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker compose -f $COMPOSE_FILE pull

# Run database migrations
echo "🗄️  Running database migrations..."
docker compose -f $COMPOSE_FILE run --rm backend alembic upgrade head

# Start services
echo "🔄 Starting services..."
docker compose -f $COMPOSE_FILE up -d --remove-orphans

# Wait for health checks
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Verify deployments
echo "🔍 Verifying deployments..."
for i in {1..30}; do
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        echo "✅ Frontend is healthy"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "❌ Frontend health check failed"
        docker compose -f $COMPOSE_FILE logs frontend
        exit 1
    fi
    sleep 2
done

for i in {1..30}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "❌ Backend health check failed"
        docker compose -f $COMPOSE_FILE logs backend
        exit 1
    fi
    sleep 2
done

# Clean up old images
echo "🧹 Cleaning up old Docker images..."
docker image prune -f

echo "✅ Deployment to $ENVIRONMENT completed successfully!"
echo ""
echo "Frontend: https://${ENVIRONMENT}.dentalpilot.in"
echo "Backend API: https://api.${ENVIRONMENT}.dentalpilot.in"
echo "Health: https://api.${ENVIRONMENT}.dentalpilot.in/health"