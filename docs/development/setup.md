# Development Setup Guide

This guide will help you set up YuFeed for local development.

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend runtime |
| Docker | 24.0+ | Infrastructure services |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Git | 2.40+ | Version control |
| Make | any | Build automation (optional) |

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required software
brew install python@3.12 node docker docker-compose git make

# Start Docker Desktop
open -a Docker
```

### Linux (Ubuntu/Debian)

```bash
# Install Python 3.12
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-venv python3.12-dev

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install other tools
sudo apt install git make
```

### Windows (WSL2 Recommended)

We strongly recommend using WSL2 for Windows development.

```powershell
# In WSL2 Ubuntu, follow the Linux instructions above
# Ensure Docker Desktop has WSL2 integration enabled
```

## Quick Start (Recommended)

The fastest way to get started:

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/yufeed.git
cd yufeed

# 2. Run automated setup
make dev-setup

# 3. Start infrastructure services
make docker-up

# 4. Run database migrations
docker-compose exec api alembic upgrade head

# 5. Seed initial data (optional)
docker-compose exec api python scripts/seed_data.py

# 6. Verify installation
make verify
```

Access the application:
- **Web**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/healthz

## Manual Setup

If you prefer manual setup or the automated script doesn't work:

### 1. Clone Repository

```bash
git clone https://github.com/yourorg/yufeed.git
cd yufeed
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# At minimum, update these:
# - SECRET_KEY (generate a secure random key)
# - ANTHROPIC_API_KEY (for AI features)
```

Generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, and OpenSearch
docker-compose up -d db redis opensearch

# Wait for services to be healthy
docker-compose ps
```

### 4. Setup Python Environment

```bash
cd apps/api

# Create virtual environment
python3.12 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 5. Setup Database

```bash
# Run migrations
alembic upgrade head

# Seed data (optional)
python scripts/seed_data.py
```

### 6. Setup Frontend

```bash
cd apps/web

# Install dependencies
npm install

# Or if using pnpm
pnpm install
```

### 7. Start Development Servers

Terminal 1 - API:
```bash
cd apps/api
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:
```bash
cd apps/web
npm run dev
```

## IDE Setup

### VS Code (Recommended)

Install these extensions:

- Python
- Pylance
- ESLint
- Prettier
- Docker
- Thunder Client (API testing)
- GitLens

Recommended settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "./apps/api/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.tsdk": "./apps/web/node_modules/typescript/lib"
}
```

### PyCharm

1. Open the project root
2. Set Python interpreter to `apps/api/.venv/bin/python`
3. Configure code style:
   - Line length: 100
   - Formatter: Black
   - Enable "Reformat on save"

## Verification

Run these commands to verify your setup:

```bash
# Check all services are running
docker-compose ps

# Test API health
curl http://localhost:8000/healthz

# Run tests
make test

# Run linting
make lint

# Full verification
make verify
```

## Common Issues

### Issue: `ModuleNotFoundError` for local packages

**Solution**: Ensure you're in the virtual environment
```bash
cd apps/api
source .venv/bin/activate
```

### Issue: Database connection refused

**Solution**: Check if PostgreSQL container is running
```bash
docker-compose ps db
# If not running:
docker-compose up -d db
```

### Issue: Port already in use

**Solution**: Kill processes using the ports
```bash
# Find processes on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different ports
uvicorn src.main:app --port 8001
```

### Issue: Redis connection error

**Solution**: Ensure Redis is running
```bash
docker-compose up -d redis
redis-cli ping  # Should return PONG
```

### Issue: Node modules conflicts

**Solution**: Clean and reinstall
```bash
cd apps/web
rm -rf node_modules package-lock.json
npm install
```

## Development Workflow

### Daily Development

```bash
# 1. Start your day - ensure services are running
docker-compose ps
# If not running: make docker-up

# 2. Activate virtual environment
cd apps/api && source .venv/bin/activate

# 3. Pull latest changes
git pull origin main

# 4. Run migrations (if needed)
alembic upgrade head

# 5. Start development servers
# Terminal 1: make dev-api
# Terminal 2: make dev-web
```

### Before Committing

```bash
# Run all checks
make verify

# Or individually:
make lint
make test
make type-check
make security-scan
```

## Debugging

### API Debugging

Enable debug logging:
```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
```

### Frontend Debugging

Use React Developer Tools browser extension for component inspection.

### Database Debugging

Connect to development database:
```bash
psql postgresql://postgres:postgres@localhost:5432/yufeed # pragma: allowlist secret
```

### Docker Debugging

View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
```

## Additional Resources

- [Architecture Overview](../architecture/overview.md)
- [API Documentation](http://localhost:8000/api/docs)
- [Contributing Guide](../../CONTRIBUTING.md)
- [Troubleshooting Guide](./troubleshooting.md)

## Getting Help

- 📖 [Documentation](https://docs.yufeed.io)
- 💬 [Discord](https://discord.gg/yufeed)
- 📧 [Email](mailto:dev@yufeed.io)
- 🐛 [Issue Tracker](https://github.com/yourorg/yufeed/issues)

## Next Steps

Now that you have YuFeed running:

1. Read the [Contributing Guide](../../CONTRIBUTING.md)
2. Explore the [Architecture](../architecture/overview.md)
3. Check out [Good First Issues](https://github.com/yourorg/yufeed/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
4. Join our [Discord community](https://discord.gg/yufeed)

Happy coding! 🚀
