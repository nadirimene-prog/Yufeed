# YuFeed

YuFeed is an AI-powered EU legal monitoring and AML compliance platform.
It combines regulatory intelligence (EUR-Lex/CELEX ingestion and search) with transaction monitoring, investigations, and reporting workflows.

## Monorepo layout

- `apps/api` FastAPI backend (SQLAlchemy + Alembic, ingestion, AI services, monitoring)
- `apps/web` Next.js frontend (App Router, TypeScript, Vitest, Playwright)
- `docs` architecture, product docs, ADRs, runbooks, and audits
- `monitoring` Prometheus + Alertmanager + Grafana provisioning

## Tech stack

- Backend: FastAPI, PostgreSQL, Redis, OpenSearch, Celery
- Frontend: Next.js, React, TypeScript, Tailwind
- Tooling: pre-commit, GitHub Actions, Docker Compose

## Quick start

### Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

Services:
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/api/docs`
- Web: `http://localhost:3000`
- OpenSearch: `http://localhost:9200`
- MailHog: `http://localhost:8025`

### Local dev (without Docker)

Backend:
```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn src.main:app --reload --port 8000
```

Frontend:
```bash
cd apps/web
npm ci
npm run dev
```

## Standard developer commands

Use the root `Makefile` as the canonical workflow:

```bash
make setup
make lint
make test
make build-web
make build-images
make ci
```

## Quality gates

- Linting: Python (`flake8`, `black --check`) and frontend (`eslint --max-warnings=0`, `tsc --noEmit`)
- Testing: `pytest` (backend) and `vitest` coverage run (frontend)
- Security: Trivy filesystem scan + tenant/security audit script in CI
- Pre-commit: run locally before pushing:
  ```bash
  pre-commit install
  pre-commit run --all-files
  ```

## Repository hygiene rules

- Do not commit generated reports, local probes, lint dumps, or backup snapshots.
- Keep secrets out of git (`.env` and derived files are ignored; detect-secrets runs in pre-commit).
- Prefer small, focused pull requests with tests for behavior changes.

## Documentation map

- Architecture: `docs/architecture/architecture.md`
- Product plans: `docs/product/`
- API compatibility/deprecations: `docs/engineering/api/API_COMPATIBILITY.md`
- Runbooks: `docs/runbooks/`
- Engineering audits: `docs/audits/`
- Archived implementation reports: `docs/archive/root-reports/`
- Developer setup/troubleshooting: `docs/dev/`

## Contributing and security

- Contributing guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
