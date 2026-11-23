# DentalPilot AI - Production Deployment Guide

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Cloudflare    │────▶│    Nginx        │────▶│    Backend      │
│   (CDN/WAF)     │     │    (Frontend)   │     │    (FastAPI)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                              ┌─────────────────┐        │
                              │   PostgreSQL    │◀───────┘
                              │   (Primary)     │
                              └─────────────────┘
                              ┌─────────────────┐
                              │     Redis       │
                              │   (Cache/Queue) │
                              └─────────────────┘
                              ┌─────────────────┐
                              │   Workers       │
                              │ (Email, Billing,│
                              │  Communication) │
                              └─────────────────┘
```

## Quick Start

### 1. Prerequisites
- Docker 24+ and Docker Compose 2+
- Domain with DNS configured
- SSL certificates (Let's Encrypt or purchased)
- External services: PostgreSQL, Redis, S3, SMTP, Razorpay, Anthropic

### 2. Configure Environment
```bash
cp .env.production.example .env.production
# Edit .env.production with all required values
```

### 3. SSL Certificates
Place certificates in `nginx/ssl/`:
```
nginx/ssl/
├── fullchain.pem    # Certificate + chain
├── privkey.pem      # Private key
└── chain.pem        # CA chain
```

### 4. Deploy
```bash
./deploy.sh production
```

## Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | `secure-random-string` |
| `JWT_SECRET` | JWT signing secret (64+ chars) | `openssl rand -base64 64` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `RAZORPAY_KEY_ID` | Razorpay key ID | `rzp_live_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay secret | `...` |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook secret | `...` |
| `RAZORPAY_PLAN_IDS` | JSON of plan IDs | `{"starter_monthly":"plan_..."}` |
| `S3_BUCKET` | S3 bucket name | `dentalpilot-prod` |
| `S3_ENDPOINT_URL` | S3 endpoint | `https://s3.amazonaws.com` |
| `SMTP_HOST` | SMTP server | `smtp.sendgrid.net` |
| `SMTP_USERNAME` | SMTP username | `apikey` |
| `SMTP_PASSWORD` | SMTP password | `SG....` |
| `SMTP_SENDER_EMAIL` | From email | `noreply@dentalpilot.in` |

## Service Details

### Backend (FastAPI)
- **Port**: 8000 (internal), 443 via Nginx
- **Workers**: 4 Uvicorn workers
- **Health**: `GET /health`

### Workers (Background Jobs)
Three workers run in a single container:
1. **Email Outbox** - Sends patient emails with retry
2. **Subscription Billing** - Razorpay webhook processing, dunning, reconciliation
3. **Communication Outbox** - Multi-channel (email/SMS/WhatsApp) delivery

### Frontend (Nginx + Angular)
- **Port**: 80/443
- **Static assets**: Cached 1 year
- **API proxy**: `/api/` → Backend
- **SPA routing**: All routes serve `index.html`

### Database (PostgreSQL 16)
- **Persistence**: Docker volume `postgres_data`
- **Migrations**: Run on backend startup via `alembic upgrade head`

### Cache (Redis 7)
- **Persistence**: AOF enabled
- **Memory**: 256MB max with LRU eviction

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`):

1. **Backend Tests** - Lint (ruff), Type check (mypy), Tests (pytest)
2. **Frontend Tests** - Lint, Type check (tsc), Tests, Build
3. **Docker Build** - Multi-arch images pushed to GHCR
4. **Deploy Staging** - Auto-deploy on push to main
5. **Deploy Production** - Manual approval required

### Required GitHub Secrets
```
STAGING_HOST, STAGING_USER, STAGING_SSH_KEY
PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_SSH_KEY
```

## Monitoring & Observability

### Health Checks
- Frontend: `https://dentalpilot.in/health`
- Backend: `https://api.dentalpilot.in/health`
- Database: `pg_isready`
- Redis: `redis-cli ping`

### Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f workers
docker compose logs -f frontend
```

### Metrics (Optional)
Add Prometheus exporters:
- `prometheus-postgres-exporter`
- `prometheus-redis-exporter`
- FastAPI `/metrics` endpoint

## Backup & Recovery

### Database Backup
```bash
# Automated daily backup (add to cron)
docker exec dentalpilot-postgres pg_dump -U dentalpilot dentalpilot | gzip > backup_$(date +%F).sql.gz

# Restore
gunzip -c backup_2024-01-15.sql.gz | docker exec -i dentalpilot-postgres psql -U dentalpilot dentalpilot
```

### Volume Backup
```bash
# Backup volumes
docker run --rm -v dentalpilot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Scaling

### Horizontal Scaling (Backend)
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
```
Requires external load balancer or Nginx upstream with multiple backend containers.

### Worker Scaling
Run multiple worker containers for higher throughput:
```bash
docker compose up -d --scale workers=2
```

## Security Checklist

- [ ] Strong `JWT_SECRET` (64+ random chars)
- [ ] PostgreSQL password rotated regularly
- [ ] Razorpay webhook secret configured
- [ ] S3 bucket private, versioned, encrypted
- [ ] SMTP credentials secured
- [ ] SSL certificates valid (auto-renew with Let's Encrypt)
- [ ] CORS origins restricted to known domains
- [ ] Rate limiting enabled on auth endpoints
- [ ] Security headers configured in Nginx
- [ ] Regular dependency updates (`npm audit`, `pip-audit`)
- [ ] Container images scanned for vulnerabilities

## Troubleshooting

### Backend won't start
```bash
docker compose logs backend
# Check: DATABASE_URL, JWT_SECRET, migrations
```

### Workers not processing
```bash
docker compose logs workers
# Check: SMTP config, Razorpay credentials, DATABASE_URL
```

### Frontend shows "Unable to reach server"
```bash
docker compose logs frontend
# Check: Nginx config, backend connectivity, CORS
```

### Database connection failed
```bash
docker compose exec postgres pg_isready -U dentalpilot
# Check: POSTGRES_PASSWORD, network, volume permissions
```

## Rollback

```bash
# Rollback to previous image tag
docker compose pull
docker compose up -d --remove-orphans

# Or specific version
docker tag ghcr.io/org/dentalpilot-ai-backend:sha-abc123 ghcr.io/org/dentalpilot-ai-backend:latest
docker compose up -d backend
```

## Support

- **Logs**: `docker compose logs -f [service]`
- **Shell**: `docker compose exec backend bash`
- **Database**: `docker compose exec postgres psql -U dentalpilot dentalpilot`
- **Redis**: `docker compose exec redis redis-cli`