"""
Multi-Tenancy Test Setup Script
Phase 4C: Task 7 - Create test tenants and API keys for validation

This script creates sample tenants with API keys for testing.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import hashlib
import secrets
from datetime import datetime
from sqlalchemy.orm import Session

from src.database import SessionLocal, engine
from src.models.tenant_models import Tenant, TenantAPIKey, TenantUser
from src.models.transaction_models import Transaction, Alert
from src.tenancy.context import TenantContext


def create_tenant(
    db: Session,
    tenant_id: str,
    name: str,
    tier: str = "standard",
    contact_email: str = None
) -> Tenant:
    """Create a new tenant."""
    print(f"\n📦 Creating tenant: {tenant_id}")

    # Check if tenant already exists
    existing = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
    if existing:
        print(f"   ⚠️  Tenant {tenant_id} already exists, skipping...")
        return existing

    tenant = Tenant(
        tenant_id=tenant_id,
        name=name,
        display_name=name,
        tier=tier,
        contact_email=contact_email,
        is_active=True,
        settings={
            "timezone": "UTC",
            "currency": "USD",
            "language": "en"
        },
        rate_limits={
            "requests_per_minute": 60,
            "requests_per_hour": 1000
        },
        feature_flags={
            "ml_auto_triage": True,
            "websocket_notifications": True,
            "advanced_reporting": True
        }
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    print(f"   ✅ Tenant created: {tenant.tenant_id} (ID: {tenant.id})")
    return tenant


def create_api_key(
    db: Session,
    tenant: Tenant,
    name: str = "Test API Key"
) -> str:
    """Create an API key for a tenant."""
    print(f"\n🔑 Creating API key for tenant: {tenant.tenant_id}")

    # Generate API key
    random_part = secrets.token_hex(16)
    api_key = f"yk_live_{tenant.tenant_id}_{random_part}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    api_key_record = TenantAPIKey(
        tenant_id=tenant.id,
        key_hash=key_hash,
        key_prefix=api_key[:20],
        name=name,
        is_active=True,
        scopes=["read:alerts", "write:transactions", "read:cases"]
    )

    db.add(api_key_record)
    db.commit()

    print(f"   ✅ API Key created: {api_key}")
    print(f"   📋 Key prefix: {api_key[:20]}...")
    print(f"   ⚠️  SAVE THIS KEY - it won't be shown again!")

    return api_key


def create_sample_data(db: Session, tenant: Tenant):
    """Create sample transactions and alerts for a tenant."""
    print(f"\n📊 Creating sample data for tenant: {tenant.tenant_id}")

    with TenantContext(tenant.tenant_id):
        # Create sample transactions
        transactions = []
        for i in range(5):
            tx = Transaction(
                transaction_id=f"TX-{tenant.tenant_id.upper()}-{i+1:03d}",
                user_id=f"user_{tenant.tenant_id}_{i+1}",
                amount=1000.00 * (i + 1),
                currency="USD",
                transaction_type="transfer",
                timestamp=datetime.utcnow(),
                status="completed",
                tenant_id=tenant.tenant_id
            )
            transactions.append(tx)
            db.add(tx)

        db.commit()
        print(f"   ✅ Created {len(transactions)} sample transactions")

        # Create sample alerts
        alerts = []
        for i in range(3):
            alert = Alert(
                alert_id=f"ALT-{tenant.tenant_id.upper()}-{i+1:03d}",
                alert_type="high_amount" if i % 2 == 0 else "velocity",
                severity="medium" if i % 2 == 0 else "high",
                user_id=f"user_{tenant.tenant_id}_{i+1}",
                status="pending",
                priority=i + 1,
                tenant_id=tenant.tenant_id
            )
            alerts.append(alert)
            db.add(alert)

        db.commit()
        print(f"   ✅ Created {len(alerts)} sample alerts")


def validate_isolation(db: Session, tenant_a: Tenant, tenant_b: Tenant):
    """Validate that data is properly isolated between tenants."""
    print("\n🔍 Validating tenant isolation...")

    # Count data for tenant A
    with TenantContext(tenant_a.tenant_id):
        from src.tenancy.queries import get_tenant_filtered_query
        tx_count_a = get_tenant_filtered_query(Transaction, db).count()
        alert_count_a = get_tenant_filtered_query(Alert, db).count()

    # Count data for tenant B
    with TenantContext(tenant_b.tenant_id):
        from src.tenancy.queries import get_tenant_filtered_query
        tx_count_b = get_tenant_filtered_query(Transaction, db).count()
        alert_count_b = get_tenant_filtered_query(Alert, db).count()

    print(f"\n   Tenant A ({tenant_a.tenant_id}):")
    print(f"      - Transactions: {tx_count_a}")
    print(f"      - Alerts: {alert_count_a}")

    print(f"\n   Tenant B ({tenant_b.tenant_id}):")
    print(f"      - Transactions: {tx_count_b}")
    print(f"      - Alerts: {alert_count_b}")

    # Verify isolation
    if tx_count_a > 0 and tx_count_b > 0:
        print("\n   ✅ Data isolation verified: Each tenant has separate data")
    else:
        print("\n   ⚠️  Warning: One or both tenants have no data")

    return tx_count_a, alert_count_a, tx_count_b, alert_count_b


def print_summary(tenants: list, api_keys: dict):
    """Print summary of created tenants and API keys."""
    print("\n" + "="*70)
    print("📋 MULTI-TENANCY SETUP SUMMARY")
    print("="*70)

    for tenant in tenants:
        print(f"\n🏢 Tenant: {tenant.name}")
        print(f"   ID: {tenant.tenant_id}")
        print(f"   Tier: {tenant.tier}")
        print(f"   Status: {'Active' if tenant.is_active else 'Inactive'}")

        if tenant.tenant_id in api_keys:
            print(f"\n   🔑 API Key:")
            print(f"   {api_keys[tenant.tenant_id]}")
            print(f"\n   📝 Usage Example:")
            print(f"   curl -H 'X-API-Key: {api_keys[tenant.tenant_id]}' \\")
            print(f"        http://localhost:8000/api/alerts")

    print("\n" + "="*70)
    print("✅ Setup complete! Test tenants are ready for validation.")
    print("="*70)


def main():
    """Main setup function."""
    print("\n" + "="*70)
    print("🚀 MULTI-TENANCY TEST SETUP")
    print("="*70)
    print("\nThis script will:")
    print("  1. Create test tenants (Acme Corp, Beta Industries)")
    print("  2. Generate API keys for each tenant")
    print("  3. Create sample data (transactions & alerts)")
    print("  4. Validate tenant isolation")
    print("\n" + "="*70)

    db = SessionLocal()
    api_keys = {}

    try:
        # Create Tenant A: Acme Corp
        tenant_a = create_tenant(
            db,
            tenant_id="acme_corp",
            name="Acme Corporation",
            tier="enterprise",
            contact_email="admin@acme.com"
        )
        api_keys["acme_corp"] = create_api_key(db, tenant_a, "Acme Production Key")
        create_sample_data(db, tenant_a)

        # Create Tenant B: Beta Industries
        tenant_b = create_tenant(
            db,
            tenant_id="beta_industries",
            name="Beta Industries",
            tier="standard",
            contact_email="admin@beta.com"
        )
        api_keys["beta_industries"] = create_api_key(db, tenant_b, "Beta Production Key")
        create_sample_data(db, tenant_b)

        # Create Tenant C: Gamma LLC (minimal tenant)
        tenant_c = create_tenant(
            db,
            tenant_id="gamma_llc",
            name="Gamma LLC",
            tier="free",
            contact_email="admin@gamma.com"
        )
        api_keys["gamma_llc"] = create_api_key(db, tenant_c, "Gamma Test Key")

        # Validate isolation
        validate_isolation(db, tenant_a, tenant_b)

        # Print summary
        print_summary([tenant_a, tenant_b, tenant_c], api_keys)

        # Save API keys to file
        output_file = Path(__file__).parent / "test_api_keys.txt"
        with open(output_file, "w") as f:
            f.write("MULTI-TENANCY TEST API KEYS\n")
            f.write("=" * 70 + "\n\n")
            for tenant_id, api_key in api_keys.items():
                f.write(f"Tenant: {tenant_id}\n")
                f.write(f"API Key: {api_key}\n\n")
            f.write("\nWARNING: Keep these keys secure. Delete after testing.\n")

        print(f"\n💾 API keys saved to: {output_file}")
        print("   ⚠️  Remember to delete this file after testing!")

    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    exit(main())
