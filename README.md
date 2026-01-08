# Yufeed Monorepo

EU Legal Monitoring MVP.

## Architecture

- **Backend**: FastAPI (Access via `http://localhost:8000/docs`)
- **Worker**: Celery (Async background tasks, daily ingestion)
- **Frontend**: Next.js + Tailwind + shadcn/ui` (Access via `http://localhost:3000`)
- **Infrastructure**: Postgres, Redis, OpenSearch, Mailhog.

## Prerequisites

- Docker & Docker Compose

## Getting Started

1.  **Clone the repository** (if not already)

2.  **Environment Setup**
    ```bash
    cp .env.example .env
    ```
    The default values in `.env.example` are configured for the Docker environment.

3.  **Start Services**
    ```bash
    docker-compose up --build
    ```

4.  **Access Services**
    - **Frontend**: [http://localhost:3000](http://localhost:3000)
    - **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)
    - **Mailhog (Emails)**: [http://localhost:8025](http://localhost:8025)
    - **OpenSearch**: [http://localhost:9200](http://localhost:9200)

## Development

- **Backend**: Code is in `backend/`. Changes trigger auto-reload in the container.
- **Frontend**: Code is in `frontend/`. 
- **Worker**: Code is shared with backend in `backend/src`.

## Security

All services adhere to binding to `127.0.0.1` on the host to prevent accidental external exposure.
