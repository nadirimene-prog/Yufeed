# Yufeed

> **EU Legal Monitoring & AML Compliance Platform**

A production-ready platform combining EU regulatory intelligence with advanced Anti-Money Laundering (AML) compliance tools, powered by AI agents and real-time transaction monitoring.

[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/next.js-14+-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 Overview

Yufeed is a comprehensive compliance platform that helps financial institutions and businesses:

- **Monitor EU Regulations** - Track directives, regulations, and decisions in real-time
- **Assess Business Impact** - AI-powered analysis of regulatory obligations and deadlines
- **Detect Financial Crime** - Transaction monitoring with configurable rules and risk scoring
- **Automate Compliance** - SAR filing, sanctions screening, and case management
- **Visualize Networks** - Graph analysis of transaction patterns and entity relationships

---

## ✨ Key Features

### 🔍 EU Legal Intelligence
- Real-time ingestion from EUR-Lex and CELEX databases
- Full-text search across 100,000+ legal documents
- AI-powered document classification and summarization
- Compliance domain categorization (AML, GDPR, Data Protection, etc.)
- Impact assessment with obligation extraction

### 💰 Transaction Monitoring
- Configurable rule engine with nested logical conditions
- Real-time risk scoring and alert generation
- User behavior analysis and velocity checks
- Geographic risk assessment
- Alert triage and investigation workflow

### 🤖 AI Agents
- **AML Officer Agent** - Automated compliance assistance
- **Investigation Agent** - Deep-dive transaction analysis
- **SAR Agent** - Suspicious Activity Report generation
- **Compliance Officer** - Regulatory guidance and recommendations

### 🔐 Sanctions & KYC
- Multi-source sanctions screening (EU, OFAC, UN)
- Fuzzy name matching with configurable thresholds
- Entity risk profiling and scoring
- KYC/KYB case management

### 📊 Analytics & Reporting
- Real-time compliance dashboard
- Network graph visualization
- Risk trend analysis
- Regulatory reporting automation

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- FastAPI 0.115+ (Python 3.12)
- PostgreSQL 15+ (primary database)
- OpenSearch 2.x (full-text search)
- Redis 7.x (caching & task queue)
- Celery (background jobs)
- Anthropic Claude API (AI agents)

**Frontend:**
- Next.js 14+ (App Router)
- React 18+
- TypeScript 5+
- Tailwind CSS 3.4+
- shadcn/ui components

**Infrastructure:**
- Docker & Docker Compose
- Mailhog (email testing)

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  Next.js 14+ App Router │ React 18+ │ TypeScript │ Tailwind│
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                        BACKEND                              │
│              FastAPI │ Python 3.12 │ Pydantic               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  API Layer   │  │  AI Agents   │  │  Integrations│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                  │            │
│  ┌──────▼─────────────────▼──────────────────▼───────┐   │
│  │           Services Layer                          │   │
│  │  (Business Logic, Rule Engine, Risk Scoring)     │   │
│  └──────┬────────────────────────────────────────────┘   │
│         │                                                 │
│  ┌──────▼─────────┐                                      │
│  │ Models (ORM)   │                                      │
│  └──────┬─────────┘                                      │
└─────────┼────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────┐
│              INFRASTRUCTURE                              │
│  PostgreSQL │ OpenSearch │ Redis │ Celery Worker        │
└──────────────────────────────────────────────────────────┘
```

**For detailed architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md)**

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Git** 2.30+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nadirimene-prog/Yufeed.git
   cd Yufeed
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

   Required variables:
   ```bash
   # AI Features (required for AI agents)
   ANTHROPIC_API_KEY=sk-ant-your-key-here

   # Database (defaults work for Docker)
   DATABASE_URL=postgresql://yufeed:yufeed123@postgres:5432/yufeed
   REDIS_URL=redis://redis:6379/0
   OPENSEARCH_URL=http://opensearch:9200
   ```

3. **Start all services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - **Frontend**: http://localhost:3000
   - **Backend API Docs**: http://localhost:8000/api/docs
   - **Mailhog (Email testing)**: http://localhost:8025
   - **OpenSearch**: http://localhost:9200

### First Steps

1. **Search for EU regulations**
   - Navigate to http://localhost:3000/search
   - Try searching for "AMLD5" or "GDPR"

2. **Run an impact assessment**
   - Open a document detail page
   - Click "Assess Impact" to get AI-powered analysis

3. **Explore the dashboard**
   - Visit http://localhost:3000/dashboard
   - View high-risk documents and compliance metrics

4. **Test transaction monitoring**
   - Go to http://localhost:3000/transaction-monitoring/dashboard
   - Ingest sample transactions via API
   - Watch alerts generate in real-time

---

## 📚 Documentation

### For Developers

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete system architecture, tech stack, and design patterns
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Development workflow, coding standards, and PR process
- **[CODE_AUDIT_REPORT.md](./CODE_AUDIT_REPORT.md)** - Code quality audit and improvement roadmap

### API Documentation

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

All endpoints are automatically documented with request/response schemas.

---

## 🔧 Development

### Local Development (without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn src.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A src.worker worker --loglevel=info
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (to be implemented)
cd frontend
npm test
```

### Code Quality

```bash
# Backend linting
cd backend
flake8 src/
black src/
mypy src/

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

---

## 🛣️ Project Status & Roadmap

### Current Status: MVP Complete ✅

**Implemented:**
- ✅ EU legal document search and retrieval
- ✅ AI-powered impact assessment
- ✅ Transaction monitoring with rule engine
- ✅ Alert management and case workflow
- ✅ Sanctions screening (EU, OFAC)
- ✅ Network graph visualization
- ✅ Compliance dashboard
- ✅ Multi-agent AI system

**In Progress:**
- 🔶 Authentication & authorization (JWT-based)
- 🔶 Rate limiting & API throttling
- 🔶 Comprehensive test coverage (target: 80%+)

### Roadmap

#### Phase 1: Security & Stability (Q1 2026)
- [ ] Implement JWT authentication
- [ ] Add rate limiting middleware
- [ ] Database connection pooling & error handling
- [ ] Increase test coverage to 80%+

#### Phase 2: Code Quality (Q1-Q2 2026)
- [ ] Consolidate duplicate components
- [ ] Standardize error handling patterns
- [ ] Improve type safety (eliminate `any` types)
- [ ] Add accessibility improvements (WCAG 2.1 AA)

#### Phase 3: Feature Enhancements (Q2 2026)
- [ ] Real-time WebSocket notifications
- [ ] Advanced ML risk models
- [ ] Multi-language support
- [ ] Mobile-responsive design improvements

#### Phase 4: Enterprise Features (Q3 2026)
- [ ] Role-based access control (RBAC)
- [ ] Audit logging & compliance trails
- [ ] Multi-tenant architecture
- [ ] SSO/SAML integration

**See [CODE_AUDIT_REPORT.md](./CODE_AUDIT_REPORT.md) for detailed improvement plan.**

---

## 🐛 Known Issues

See [CODE_AUDIT_REPORT.md](./CODE_AUDIT_REPORT.md) for comprehensive list of known issues and their priorities.

**Critical (Fixed):**
- ✅ Missing `re` import in rule engine (caused runtime crashes)

**High Priority:**
- ⚠️ No authentication on endpoints (all public)
- ⚠️ CORS validation needs improvement
- ⚠️ Database connection error handling missing

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for:

- Development environment setup
- Coding standards (Python & TypeScript)
- Git workflow and commit conventions
- Testing requirements
- Pull request process

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following our coding standards
4. Run tests and linting
5. Commit with conventional commit messages
6. Push and create a Pull Request

---

## 📝 License

This project is proprietary software. All rights reserved.

For licensing inquiries, please contact: [your-email@example.com]

---

## 🙏 Acknowledgments

- **Anthropic** - Claude AI API for intelligent agents
- **EUR-Lex** - EU legal database and CELEX system
- **shadcn/ui** - Beautiful UI component library
- **FastAPI** - High-performance Python framework

---

## 📧 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/nadirimene-prog/Yufeed/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nadirimene-prog/Yufeed/discussions)
- **Email**: [your-email@example.com]

---

## 🔒 Security

**Security Policy**: We take security seriously. If you discover a security vulnerability, please email [security@example.com] instead of using the public issue tracker.

**Important Notes:**
- Never commit `.env` files with real API keys
- Rotate API keys regularly
- Use strong passwords for database access
- Enable HTTPS in production

---

## 📊 Project Statistics

- **Languages**: Python 60%, TypeScript 35%, Other 5%
- **Total Files**: 147+ (75 backend, 72 frontend)
- **Lines of Code**: ~15,000+
- **Documentation**: 3,500+ lines

---

<div align="center">

**Built with ❤️ for EU Compliance & Financial Crime Prevention**

[Report Bug](https://github.com/nadirimene-prog/Yufeed/issues) · [Request Feature](https://github.com/nadirimene-prog/Yufeed/issues) · [Documentation](./ARCHITECTURE.md)

</div>
