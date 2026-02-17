# 🐳 Docker vs Local Development Setup Guide

## The Problem (Fixed!)

You had **conflicting database configurations** that caused PostgreSQL vs SQLite issues:
- Root `.env` was configured for Docker (host=`db`)
- `apps/api/.env` was configured for local (host=`localhost`)
- Fallback in `config.py` defaulted to SQLite
- Some scripts had hardcoded SQLite paths

## The Solution

### 1. Unified Configuration Files

**`.env`** (Root - Now works for BOTH Docker and local)
```bash
# For LOCAL development (default):
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yufeed

# For DOCKER, this gets overridden by docker-compose.override.yml
```

**`docker-compose.override.yml`** (Docker-specific overrides)
```yaml
api:
  environment:
    # Inside Docker, use service name "db" instead of "localhost"
    - DATABASE_URL=postgresql://postgres:postgres@db:5432/yufeed
```

### 2. Fixed Config Loading

**`apps/api/src/config.py`** now loads from:
1. Project root `.env` (preferred)
2. Falls back to `apps/api/.env` if root not found

### 3. Fixed Hardcoded Scripts

8 scripts updated to use `DATABASE_URL` env var instead of hardcoded SQLite:
- `add_supervisory_sources.py`
- `demo_rag.py`
- `fix_content.py`
- `fix_rag.py`
- `fix_source_urls.py`
- `fix_working_sources.py`
- `ingest_supervisory.py`
- `test_rag.py`

---

## 🚀 Usage

### Option A: Local Development (PostgreSQL on localhost)

```bash
# 1. Make sure PostgreSQL is running locally
brew services start postgresql@15  # macOS
sudo service postgresql start       # Linux

# 2. Create database
psql -U postgres -c "CREATE DATABASE yufeed;"

# 3. Start the API
cd apps/api
source .venv/bin/activate
uvicorn src.main:app --reload

# 4. Start the frontend
cd apps/web
npm run dev
```

### Option B: Docker Development (Everything in containers)

```bash
# 1. Start all services
docker-compose up -d

# 2. Run migrations
docker-compose exec api alembic upgrade head

# 3. Access:
# - API: http://localhost:8000
# - Frontend: http://localhost:3000
# - PostgreSQL: localhost:5432
```

### Option C: Quick Testing with SQLite

```bash
# Edit .env and uncomment:
# DATABASE_URL=sqlite:///./compliance.db

# Then start the API - it will use SQLite instead
cd apps/api
source .venv/bin/activate
uvicorn src.main:app --reload
```

---

## 🔍 Troubleshooting

### "Connection refused" to PostgreSQL

```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# If not running:
brew services start postgresql@15  # macOS
sudo service postgresql start       # Linux
```

### "Database yufeed does not exist"

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE yufeed;"
```

### "SQLite database keeps appearing"

This happens when `DATABASE_URL` is not set correctly:

```bash
# Check current value
echo $DATABASE_URL

# Check what .env files are being loaded
ls -la .env apps/api/.env 2>/dev/null

# The fix: Make sure root .env has the correct DATABASE_URL
```

### Switching Between PostgreSQL and SQLite

```bash
# To use PostgreSQL:
echo 'DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yufeed' > .env

# To use SQLite:
echo 'DATABASE_URL=sqlite:///./compliance.db' > .env
```

---

## 📁 Configuration Files Reference

| File | Purpose | When to Edit |
|------|---------|--------------|
| `.env` | Main config (root) | Local development settings |
| `docker-compose.yml` | Docker service definitions | Rarely - infrastructure |
| `docker-compose.override.yml` | Docker local overrides | Local Docker customizations |
| `apps/api/src/config.py` | Application config | Never - code defaults |

---

## ✅ Verification

```bash
# 1. Check which database is configured
grep DATABASE_URL .env

# 2. Test the API connection
curl http://localhost:8000/healthz

# 3. Check logs for database info
cd apps/api
source .venv/bin/activate
python -c "from src.config import settings; print(f'Database: {settings.DATABASE_URL}')"
```

---

## 🎯 CI/CD (GitHub Actions)

The CI workflow already handles this correctly:
```yaml
env:
  DATABASE_URL: postgresql://yufeed:yufeed123@localhost:5432/yufeed_test
```

It uses the environment variable directly, bypassing `.env` files.
