# Rate Limiting Documentation

## Overview

The Yufeed API implements rate limiting to prevent abuse and ensure fair resource allocation. Rate limiting is applied per user (when authenticated) or per IP address (for anonymous requests).

## How It Works

- **Identifier**: Rate limits are tracked by user ID (authenticated) or IP address (anonymous)
- **Storage**: In-memory storage for development, Redis for production (distributed)
- **Strategy**: Fixed-window rate limiting
- **Default Limits**: 200 requests/hour, 1000 requests/day (can be overridden per endpoint)

## Rate Limit Tiers

### Authentication Endpoints (Strict)
Protect against brute force attacks:
- **Login**: 5 requests/minute
- **Registration**: 3 requests/hour
- **Token Refresh**: 10 requests/minute

### Data Operations
- **Create**: 20 requests/minute
- **Read**: 100 requests/minute
- **Update**: 30 requests/minute
- **Delete**: 10 requests/minute
- **List**: 60 requests/minute

### Search & Query
- **Search**: 30 requests/minute
- **Query**: 60 requests/minute

### AI/LLM Operations (Expensive)
- **AI Analysis**: 10 requests/hour
- **AI Generation**: 5 requests/hour

### Export & Reporting (Resource Intensive)
- **Export**: 5 requests/hour
- **Report**: 10 requests/hour

## Usage in API Endpoints

### Basic Usage

```python
from fastapi import APIRouter, Request
from src.middleware import limiter, RateLimits

router = APIRouter()

@router.get("/items")
@limiter.limit(RateLimits.READ)  # Apply read rate limit
async def get_items(request: Request):
    return {"items": []}
```

### Custom Rate Limits

```python
@router.post("/expensive-operation")
@limiter.limit("5 per hour")  # Custom limit
async def expensive_operation(request: Request):
    # Expensive operation here
    pass
```

### Multiple Rate Limits

```python
@router.post("/protected")
@limiter.limit("10 per minute")
@limiter.limit("100 per hour")
async def protected_endpoint(request: Request):
    # This endpoint has both per-minute and per-hour limits
    pass
```

### Exempt from Rate Limiting

To exempt an endpoint from rate limiting, simply don't apply the `@limiter.limit()` decorator.

```python
@router.get("/public")
async def public_endpoint():
    # No rate limiting applied
    return {"status": "ok"}
```

## Configuration

### Development (In-Memory)

By default, rate limiting uses in-memory storage:

```python
# backend/src/middleware/rate_limiter.py
limiter = Limiter(
    key_func=get_identifier,
    storage_uri="memory://",  # In-memory storage
)
```

### Production (Redis)

For production with Redis, ensure `REDIS_URL` is set in your `.env` file:

```bash
REDIS_URL=redis://localhost:6379
```

The rate limiter will automatically use Redis if configured:

```python
# In backend/src/main.py startup event
configure_redis_storage(settings.REDIS_URL)
```

## Rate Limit Response

When rate limit is exceeded, the API returns:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "detail": "5 per 1 minute",
  "retry_after": 45
}
```

HTTP Status Code: **429 Too Many Requests**

## Best Practices

### 1. Choose Appropriate Limits

- **Authentication**: Use strict limits (5-10/minute) to prevent brute force
- **Read Operations**: More permissive (60-100/minute)
- **Expensive Operations**: Conservative (5-10/hour for AI, exports)

### 2. Always Include Request Parameter

Rate limiting decorators require the `Request` object:

```python
# ✅ Correct
@limiter.limit(RateLimits.READ)
async def endpoint(request: Request):
    pass

# ❌ Wrong - Missing request parameter
@limiter.limit(RateLimits.READ)
async def endpoint():
    pass
```

### 3. Document Rate Limits

Include rate limits in API documentation:

```python
@router.get("/items")
@limiter.limit(RateLimits.READ)
async def get_items(request: Request):
    """
    Get all items.

    Rate Limit: 100 requests/minute
    """
    pass
```

### 4. Use Pre-configured Limits

Prefer using `RateLimits` constants over custom strings:

```python
# ✅ Good - Using constant
@limiter.limit(RateLimits.CREATE)

# ⚠️  Acceptable but not preferred - Custom limit
@limiter.limit("20 per minute")
```

## Monitoring

### Check Rate Limit Headers

Clients can check rate limit status via response headers (if configured):

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

### Logging

Rate limit violations are logged:

```
WARNING: Rate limit exceeded for user:abc123 on /api/alerts. Limit: 60 per 1 minute
```

## Testing

### Unit Tests

Test rate limiting in isolation:

```bash
cd backend
python3 test_rate_limiting.py
```

### Integration Tests

Test with actual HTTP requests:

```python
import requests

# Make 6 requests (limit is 5/minute for login)
for i in range(6):
    response = requests.post("http://localhost:8000/api/auth/login", json={
        "email": "test@example.com",
        "password": "password"
    })

    if i < 5:
        assert response.status_code != 429
    else:
        assert response.status_code == 429  # 6th request should be rate limited
```

## Troubleshooting

### Issue: Rate limits not working

**Solution**: Ensure `app.state.limiter` is set in `main.py`:

```python
app.state.limiter = limiter
```

### Issue: Redis connection error

**Solution**: Verify Redis is running and `REDIS_URL` is correct:

```bash
redis-cli ping  # Should return PONG
```

If Redis is unavailable, the system falls back to in-memory storage with a warning.

### Issue: Rate limit per user not working

**Solution**: Ensure authentication middleware sets `request.state.user`:

```python
# In authentication dependency
async def get_current_user(request: Request, ...):
    # ... validate token ...
    request.state.user = current_user  # Set user on request state
    return current_user
```

## Future Enhancements

- [ ] Add Redis Cluster support for high availability
- [ ] Implement rate limit bypass for admin users
- [ ] Add dynamic rate limits based on user tier/subscription
- [ ] Implement sliding window rate limiting for better accuracy
- [ ] Add rate limit analytics dashboard
- [ ] Support rate limiting by other dimensions (API key, organization)
