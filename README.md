# YuFeed

YuFeed is an AI-powered EU legal monitoring & AML compliance platform.
It combines regulatory intelligence (EUR-Lex/CELEX ingestion + search) with transaction monitoring, investigations, and reporting workflows.

**New:** End-to-end regulatory intelligence pipeline with AI policy generation, obligation tracking, and automated compliance enforcement.

## Repository structure

- `apps/api` — FastAPI backend (SQLAlchemy/Alembic), ingestion, AI agents, monitoring
- `apps/web` — Next.js frontend (App Router)\
- `docs` — product, architecture, ADRs, audits, runbooks
- `scripts` — helper scripts

## Tech stack

- **Backend**: FastAPI, PostgreSQL, OpenSearch, Redis, Celery
- **Frontend**: Next.js, TypeScript, Tailwind, shadcn/ui
- **Infra**: Docker Compose, GitHub Actions

## Quickstart (Docker)

```bash
cp .env.example .env

docker compose up --build
```

- API: http://localhost:8000
- Web: http://localhost:3000
- OpenSearch: http://localhost:9200
- MailHog: http://localhost:8025

## Documentation

- Architecture: `docs/architecture/architecture.md`
- Product docs: `docs/product/`
- **Regulatory Pipeline:** `docs/product/regulatory-pipeline-plan.md`
- **Product Backlog:** `docs/product/regulatory-pipeline-backlog.md`
- Evaluation assets: `docs/eval/`
- Engineering notes: `docs/engineering/`
- Development setup & troubleshooting: `docs/dev/`

## Contributing

See `CONTRIBUTING.md`.

## Security

See `SECURITY.md` for vulnerability reporting.

## Code of Conduct

See `CODE_OF_CONDUCT.md`.
