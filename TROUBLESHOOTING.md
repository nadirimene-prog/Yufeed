# Troubleshooting Guide

## Backend Issues

### Issue: Backend not connecting / Empty reply from server

**Root Cause**: The `.env` file was configured to use PostgreSQL, but PostgreSQL service was not running.

**Solution**: Updated `.env` to use SQLite for local development:

```bash
# backend/.env
DATABASE_URL=sqlite:///./compliance.db
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yufeed  # Use this for production
```

**Steps to Fix**:
1. Navigate to backend directory: `cd backend`
2. Update `.env` to use SQLite (as shown above)
3. Start the server: `python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload`
4. Test connection: `curl http://localhost:8000/api/docs`

### Issue: Tests failing on GitHub but passing locally

**Root Cause**: Tests are actually passing locally (4 passed, 34 warnings). The "failures" on GitHub may be deprecation warnings being treated as errors.

**Verification**:
```bash
cd backend
python3 -m pytest tests/ -v
```

**Warnings to Address** (non-blocking but should be fixed in future):
- Pydantic V1 → V2 migration warnings
- FastAPI `on_event` → lifespan handlers
- FastAPI `regex` → `pattern` parameter

## Frontend Issues

### Issue: Frontend not loading on localhost:3000

**Root Cause**: Backend was not responding, causing frontend API calls to fail.

**Solution**: Fix backend connection issues first (see above).

**Verification**:
```bash
cd frontend
npm install
npm run dev
# Visit http://localhost:3000
```

## Database Setup

### SQLite (Local Development)
- Automatically creates `compliance.db` file
- No additional setup required
- Used by default in updated configuration

### PostgreSQL (Production)
- Requires PostgreSQL service running
- Connection string: `postgresql://postgres:postgres@localhost:5432/yufeed`
- Start PostgreSQL:
  ```bash
  # macOS
  brew services start postgresql
  
  # Docker
  docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
  ```

## Common Commands

### Backend
```bash
cd backend

# Install dependencies
pip3 install -r requirements.txt

# Run tests
python3 -m pytest tests/ -v

# Start development server
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Check if server is running
curl http://localhost:8000/api/docs
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Environment Variables

### Backend `.env` (Local Development)
```env
# SQLite for local development
DATABASE_URL=sqlite:///./compliance.db

# Optional services (can be disabled for local dev)
REDIS_URL=redis://localhost:6379/0
OPENSEARCH_URL=http://localhost:9200
SMTP_HOST=localhost
SMTP_PORT=1025
```

### Backend `.env` (Production)
```env
# PostgreSQL for production
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/yufeed

# Required services
REDIS_URL=redis://localhost:6379/0
OPENSEARCH_URL=http://localhost:9200
SMTP_HOST=smtp.example.com
SMTP_PORT=587
ENVIRONMENT=production
```

## Phase 1 Changes Summary

### Backend Security & Reliability Improvements
1. **Database Error Handling** (`src/database.py`)
   - Added connection pooling with health checks
   - Comprehensive error handling for OperationalError, IntegrityError, DBAPIError
   - Proper transaction rollback on failures

2. **CORS Validation** (`src/main.py`)
   - Validates origin URLs for proper format
   - Rejects wildcards in production
   - Prevents suspicious patterns
   - Fallback to safe defaults

3. **Request Size Limits** (`src/main.py`)
   - Prevents DoS attacks with 10MB default limit
   - Returns 413 status with Retry-After header
   - Configurable via `MAX_REQUEST_SIZE` environment variable

## Phase 2 Changes Summary

### Frontend Code Quality Improvements
1. **Consolidated RiskBadge Components** (3 → 1)
   - Single source of truth: `components/ui/risk-badge.tsx`
   - Updated all import statements
   - Deleted duplicate implementations

2. **Enhanced Error Boundaries**
   - Global error boundary: `app/error.tsx`
   - Root layout errors: `app/global-error.tsx`
   - Reusable component: `components/ErrorBoundary.tsx`
   - Development mode error details
   - Recovery options (retry, go home)

3. **Replaced 'any' Types with Proper Interfaces**
   - `doc-tabs.tsx`: Added EUDocument interface
   - `NetworkGraph.tsx`: Added GraphNode, GraphLink, GraphData types
   - `impact-assessment.tsx`: Added proper prop interfaces
   - Better type safety and IDE autocomplete

## Known Issues

1. **Deprecation Warnings**: Multiple Pydantic V1 → V2 migration warnings. Not blocking but should be addressed.
2. **Network Analysis Type Mismatch**: Pre-existing TypeScript error in `network-analysis/page.tsx` line 272. Not related to Phase 2 changes.

## Getting Help

If you encounter issues not covered here:
1. Check backend logs: Look for error messages in terminal
2. Check frontend console: Open browser DevTools → Console tab
3. Verify services are running:
   - Backend: `curl http://localhost:8000/api/docs`
   - Frontend: `curl http://localhost:3000`
4. Check database connection:
   - SQLite: Verify `compliance.db` file exists in `backend/` directory
   - PostgreSQL: Verify service is running with `pg_isready`

## Contact

For issues or questions, create an issue at: https://github.com/nadirimene-prog/Yufeed/issues
