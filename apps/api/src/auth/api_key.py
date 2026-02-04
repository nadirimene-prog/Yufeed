import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.models.tenant_models import TenantAPIKey, Tenant


def resolve_api_key(
    db: Session,
    api_key: str,
    *,
    update_usage: bool = True,
) -> Optional[Tuple[str, str]]:
    """
    Resolve an API key to (tenant_id, key_prefix).

    Returns None if the key is invalid or inactive, or tenant is inactive.
    """
    if not api_key or not api_key.startswith("yk_"):
        return None

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_record = db.query(TenantAPIKey).filter(
        TenantAPIKey.key_hash == key_hash,
        TenantAPIKey.is_active == True,
    ).first()
    if not api_key_record:
        return None

    tenant = db.query(Tenant).filter(
        Tenant.id == api_key_record.tenant_id,
        Tenant.is_active == True,
    ).first()
    if not tenant:
        return None

    if update_usage:
        api_key_record.last_used_at = datetime.now(timezone.utc)
        api_key_record.usage_count = (api_key_record.usage_count or 0) + 1
        db.commit()

    return tenant.tenant_id, api_key_record.key_prefix
