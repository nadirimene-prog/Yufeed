from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os

app = FastAPI(
    title="EU Legal Monitoring MVP",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization"],  # Explicit headers
    expose_headers=["X-Request-ID"],
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response: Response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' http://localhost:* http://127.0.0.1:*"
    )

    # Strict Transport Security (HTTPS only - enable in production)
    if os.getenv("ENABLE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions Policy
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    return response

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.on_event("startup")
def startup_event():
    from src.database import engine, Base
    from src.search import init_indices
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Init search
    try:
        init_indices()
    except Exception as e:
        print(f"Warning: OpenSearch init failed: {e}")

from src.api.endpoints import router as api_router
from src.api.compliance import router as compliance_router
from src.api.impact import router as impact_router
from src.api.query import router as query_router
from src.api.transactions import router as transactions_router
from src.api.alerts import router as alerts_router
from src.api.monitoring_dashboard import router as monitoring_router

app.include_router(api_router)
app.include_router(compliance_router)
app.include_router(impact_router)
app.include_router(query_router)
app.include_router(transactions_router)
app.include_router(alerts_router)
app.include_router(monitoring_router)
