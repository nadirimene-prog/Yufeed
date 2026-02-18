# ADR-001: Multi-Tenancy Architecture

## Status

Accepted

## Context

YuFeed serves multiple financial institutions (banks, fintechs, compliance firms) from a single deployment. Each client needs:
- Complete data isolation
- Custom configurations
- Independent user management
- Scalable resource allocation

We needed to decide on an architecture that balances:
- Security (strong isolation)
- Cost efficiency (shared infrastructure)
- Operational simplicity
- Performance

## Decision

We will implement **Shared Database with Row-Level Security (RLS)** for multi-tenancy.

### Key Components:

1. **Tenant Identification**: Every table has a `tenant_id` column
2. **Automatic Filtering**: Middleware injects tenant context into all queries
3. **API Keys**: Each tenant has scoped API keys for authentication
4. **Rate Limiting**: Per-tenant quotas for API usage

```python
# Example: Automatic tenant filtering
class TenantMiddleware:
    async def dispatch(self, request, call_next):
        tenant = extract_tenant_from_request(request)
        set_tenant_context(tenant.id)

        # All queries automatically include: WHERE tenant_id = 'xxx'
        response = await call_next(request)
        return response
```

## Consequences

### Positive

- **Cost Efficient**: Single database cluster serves all tenants
- **Easy Maintenance**: One schema to manage, simpler backups
- **Strong Security**: Database-level enforcement of isolation
- **Fast Queries**: No cross-database joins needed

### Negative

- **Complexity**: Must ensure `tenant_id` is always filtered
- **Noisy Neighbor**: One tenant's heavy queries can impact others
- **Schema Changes**: Affects all tenants simultaneously
- **Backup Granularity**: Per-tenant restore is more complex

### Neutral

- Requires careful testing to prevent data leakage
- Tenant ID must be indexed on all tables

## Alternatives Considered

### Alternative 1: Database-per-Tenant

**Pros:**
- Complete isolation at database level
- Easier per-tenant backup/restore
- Independent schema migrations

**Cons:**
- Higher infrastructure costs
- Complex connection pooling
- Harder to manage many databases
- Cross-tenant analytics difficult

**Why Not:** Too expensive and operationally complex for our use case.

### Alternative 2: Schema-per-Tenant

**Pros:**
- Good isolation within same database
- Per-tenant schema migrations possible
- Moderate cost

**Cons:**
- PostgreSQL has schema limits (~32k)
- Connection management complexity
- Harder to enforce security consistently

**Why Not:** Doesn't scale well beyond thousands of tenants.

## Implementation

See:
- [Tenant Models](../../apps/api/src/models/tenant_models.py)
- [Tenant Middleware](../../apps/api/src/tenancy/middleware.py)
- [Tenant Queries](../../apps/api/src/tenancy/queries.py)

## References

- [Microsoft: Multi-tenant SaaS patterns](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns)
- [AWS: SaaS Tenant Isolation Strategies](https://aws.amazon.com/blogs/apn/saas-tenant-isolation-strategies/)
