# YuFeed

[![CI](https://github.com/yourorg/yufeed/actions/workflows/ci.yml/badge.svg)](https://github.com/yourorg/yufeed/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/yourorg/yufeed/branch/main/graph/badge.svg)](https://codecov.io/gh/yourorg/yufeed)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Node 20](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)

> **AI-powered EU legal monitoring & AML compliance platform**

YuFeed is a comprehensive compliance platform that leverages AI to monitor EU regulations, detect AML risks, and automate compliance workflows for financial institutions.

[📖 Documentation](https://docs.yufeed.io) • [🚀 Quick Start](#quick-start) • [🛠️ Development](docs/development/setup.md) • [📊 Architecture](docs/architecture/overview.md)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               YUFEED PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Web App    │  │  AML Officer │  │  Compliance  │  │   Auditing   │    │
│  │   (Next.js)  │  │   (AI/ML)    │  │   Dashboard  │  │   & Reports  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│         └─────────────────┴─────────────────┴─────────────────┘            │
│                                   │                                         │
│                           ┌───────┴───────┐                                │
│                           │   API Gateway │                                │
│                           │   (FastAPI)   │                                │
│                           └───────┬───────┘                                │
│                                   │                                         │
│  ┌────────────────────────────────┼────────────────────────────────┐      │
│  │                                ▼                                 │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │      │
│  │  │  Alerts  │ │  Cases   │ │ Policies │ │  Rules   │ │  Risk  │ │      │
│  │  │  Engine  │ │  Mgmt    │ │  Engine  │ │  Engine  │ │  Mgmt  │ │      │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │      │
│  │                                                                │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │      │
│  │  │ Gap      │ │ Reminder │ │ Policy   │ │ Impact   │ │  AI    │ │      │
│  │  │ Analysis │ │ Service  │ │ Generator│ │ Assessment│ │  Core  │ │      │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │      │
│  └────────────────────────────────────────────────────────────────┘      │
│                                   │                                         │
│  ┌────────────────────────────────┼────────────────────────────────┐      │
│  │           Data Layer           │                                 │      │
│  │  ┌──────────┬──────────┬───────┴──────┬──────────┬──────────┐   │      │
│  │  │PostgreSQL│  Redis   │ OpenSearch   │  MinIO   │  Vector  │   │      │
│  │  │(Primary) │  (Cache) │  (Search)    │ (Files)  │   DB     │   │      │
│  │  └──────────┴──────────┴──────────────┴──────────┴──────────┘   │      │
│  └─────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🤖 AI-Powered Compliance
- **AML Officer Assistant** - AI-driven suspicious activity detection and investigation
- **Smart Policy Generator** - Auto-generate compliance policies from regulations
- **Impact Assessment** - AI analysis of regulatory changes on your business
- **Natural Language Queries** - Ask compliance questions in plain English

### 📊 Regulatory Monitoring
- **EU Legal Tracking** - Real-time monitoring of EUR-Lex, Official Journal
- **Gap Analysis** - Identify compliance gaps between obligations and policies
- **Deadline Reminders** - Automated reminders for compliance deadlines
- **Risk Mapping** - Visual risk heatmaps and coverage analysis

### 🔒 Security & Audit
- **Multi-tenancy** - Complete tenant isolation with row-level security
- **Audit Trails** - Comprehensive audit logging for all actions
- **Evidence Packs** - Automated evidence collection for regulators
- **SAR Filing** - Streamlined Suspicious Activity Report filing

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 24.0+ & Docker Compose
- **Python** 3.12+ (for local development)
- **Node.js** 20+ (for frontend)
- **Make** (optional, for convenience commands)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourorg/yufeed.git
cd yufeed

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Seed initial data
docker-compose exec api python scripts/seed_data.py

# Access the application
open http://localhost:3000
```

### Option 2: Local Development

```bash
# 1. Start infrastructure services
docker-compose up -d db redis opensearch

# 2. Setup Python environment
cd apps/api
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Start API server
uvicorn src.main:app --reload

# 5. In another terminal, start frontend
cd apps/web
npm install
npm run dev
```

---

## 📁 Repository Structure

```
yufeed/
├── apps/                     # Application code
│   ├── api/                 # FastAPI backend
│   │   ├── src/            # Source code
│   │   ├── tests/          # Test suites
│   │   └── requirements.txt
│   └── web/                # Next.js frontend
│       ├── src/           # Source code
│       └── package.json
├── docs/                    # Documentation
│   ├── architecture/       # Architecture docs & ADRs
│   ├── development/        # Developer guides
│   └── operations/         # Runbooks & SOPs
├── scripts/                 # Automation scripts
│   ├── setup/             # Setup scripts
│   ├── ci/                # CI/CD helpers
│   └── deploy/            # Deployment scripts
├── config/                  # Configuration files
├── tools/                   # Development tools
├── .github/                 # GitHub templates & workflows
├── docker-compose.yml       # Local development stack
├── Makefile                # Common commands
└── README.md               # This file
```

---

## 🛠️ Development

### Code Quality

We maintain high code quality standards:

```bash
# Run all checks
make lint
make test
make type-check
make security-scan

# Or run individually
pre-commit run --all-files
pytest --cov=src --cov-report=html
mypy src/
bandit -r src/
```

### Testing

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test suite
pytest tests/unit/test_gap_analysis.py -v

# Run integration tests
pytest tests/integration/ -v --integration
```

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our [style guide](docs/development/style-guide.md)

3. **Run tests and checks**
   ```bash
   make verify
   ```

4. **Commit using conventional commits**
   ```bash
   git commit -m "feat(gap-analysis): add trend analysis endpoint"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📊 Monitoring & Observability

```bash
# Access monitoring dashboards
open http://localhost:3001  # Grafana
open http://localhost:9090  # Prometheus
open http://localhost:16686 # Jaeger (Tracing)
```

### Key Metrics

- **API Response Time** < 200ms (p95)
- **Database Query Time** < 50ms (p99)
- **AI Inference Time** < 5s (p95)
- **Test Coverage** > 80%

---

## 🔐 Security

Security is a top priority. Please refer to our security documentation:

- [Security Policy](SECURITY.md)
- [Reporting Vulnerabilities](docs/operations/security-incidents.md)
- [Compliance](docs/operations/compliance.md)

### Security Scanning

```bash
# Run security scans
make security-scan

# Dependency vulnerability check
safety check

# Static analysis
bandit -r src/
semgrep --config=auto src/
```

---

## 📚 Documentation

| Resource | Description |
|----------|-------------|
| [Architecture Overview](docs/architecture/overview.md) | System architecture & components |
| [API Reference](https://api-docs.yufeed.io) | OpenAPI/Swagger documentation |
| [Development Setup](docs/development/setup.md) | Local development guide |
| [Deployment Guide](docs/operations/deployment.md) | Production deployment |
| [Runbooks](docs/operations/runbooks/) | Operational procedures |
| [ADRs](docs/adr/) | Architecture Decision Records |

---

## 🤝 Contributing

We welcome contributions! Please see:

- [Contributing Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Development Guide](docs/development/setup.md)

### Contributors

<a href="https://github.com/yourorg/yufeed/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=yourorg/yufeed" />
</a>

---

## 📄 License

YuFeed is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [Next.js](https://nextjs.org/), and [PostgreSQL](https://www.postgresql.org/)
- AI/ML powered by [Anthropic Claude](https://www.anthropic.com/claude)
- Inspired by compliance challenges in the EU financial sector

---

<p align="center">
  <a href="https://yufeed.io">🌐 Website</a> •
  <a href="https://docs.yufeed.io">📖 Docs</a> •
  <a href="https://twitter.com/yufeed">🐦 Twitter</a> •
  <a href="https://discord.gg/yufeed">💬 Discord</a>
</p>
