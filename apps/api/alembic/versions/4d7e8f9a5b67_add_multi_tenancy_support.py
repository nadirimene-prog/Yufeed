"""add multi-tenancy support

Revision ID: 4d7e8f9a5b67
Revises: 3e8f9a2b4c56
Create Date: 2026-01-23 14:00:00.000000

Phase 4C: Task 7.1 - Multi-Tenancy Database Schema Changes

Adds tenant support with complete data isolation:
- Creates tenants table and related tables
- Adds tenant_id to all existing tables
- Creates indexes for tenant filtering
- Adds foreign key constraints
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4d7e8f9a5b67'
down_revision = '3e8f9a2b4c56'
branch_labels = None
depends_on = None


def upgrade():
    """Add multi-tenancy support to all tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    json_type = postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()

    # Ensure rule_hits exists before adding tenant_id (some early schemas missed it)
    if "rule_hits" not in existing_tables:
        op.create_table(
            "rule_hits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(length=255), nullable=True),
            sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=False),
            sa.Column("rule_id", sa.Integer(), sa.ForeignKey("monitoring_rules.id"), nullable=False),
            sa.Column("trigger_values", json_type, nullable=True),
            sa.Column("matched_conditions", json_type, nullable=True),
            sa.Column("hit_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        )
        existing_tables.add("rule_hits")

    # ============================================================================
    # STEP 1: Create Tenant Tables
    # ============================================================================

    # Create tenants table
    if 'tenants' not in existing_tables:
        op.create_table(
            'tenants',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.String(length=255), unique=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('display_name', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('tier', sa.String(length=50), nullable=True, server_default='standard'),
            sa.Column('contact_email', sa.String(length=255), nullable=True),
            sa.Column('contact_name', sa.String(length=255), nullable=True),
            sa.Column('settings', json_type, nullable=True),
            sa.Column('rate_limits', json_type, nullable=True),
            sa.Column('feature_flags', json_type, nullable=True),
            sa.Column('logo_url', sa.String(length=500), nullable=True),
            sa.Column('primary_color', sa.String(length=7), nullable=True),
            sa.Column('secondary_color', sa.String(length=7), nullable=True),
            sa.Column('metadata', json_type, nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
        )
        existing_tables.add('tenants')
    if 'tenants' in existing_tables:
        tenant_indexes = {idx["name"] for idx in inspector.get_indexes('tenants')}
        tenant_index_name = op.f('ix_tenants_tenant_id')
        if tenant_index_name not in tenant_indexes:
            op.create_index(tenant_index_name, 'tenants', ['tenant_id'], unique=True)

    # Create tenant API keys table
    if 'tenant_api_keys' not in existing_tables:
        op.create_table(
            'tenant_api_keys',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('key_hash', sa.String(length=255), unique=True, nullable=False),
            sa.Column('key_prefix', sa.String(length=20), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.Column('usage_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('scopes', json_type, nullable=True),
            sa.Column('created_by', sa.String(length=255), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        )
        existing_tables.add('tenant_api_keys')
    if 'tenant_api_keys' in existing_tables:
        api_key_indexes = {idx["name"] for idx in inspector.get_indexes('tenant_api_keys')}
        api_key_tenant_index = op.f('ix_tenant_api_keys_tenant_id')
        api_key_hash_index = op.f('ix_tenant_api_keys_key_hash')
        if api_key_tenant_index not in api_key_indexes:
            op.create_index(api_key_tenant_index, 'tenant_api_keys', ['tenant_id'], unique=False)
        if api_key_hash_index not in api_key_indexes:
            op.create_index(api_key_hash_index, 'tenant_api_keys', ['key_hash'], unique=True)

    # Create tenant users table
    if 'tenant_users' not in existing_tables:
        op.create_table(
            'tenant_users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=True, server_default='viewer'),
            sa.Column('permissions', json_type, nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.func.now()),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user'),
        )
        existing_tables.add('tenant_users')
    if 'tenant_users' in existing_tables:
        tenant_user_indexes = {idx["name"] for idx in inspector.get_indexes('tenant_users')}
        tenant_user_tenant_index = op.f('ix_tenant_users_tenant_id')
        tenant_user_id_index = op.f('ix_tenant_users_user_id')
        if tenant_user_tenant_index not in tenant_user_indexes:
            op.create_index(tenant_user_tenant_index, 'tenant_users', ['tenant_id'], unique=False)
        if tenant_user_id_index not in tenant_user_indexes:
            op.create_index(tenant_user_id_index, 'tenant_users', ['user_id'], unique=False)

    # Create tenant audit logs table
    if 'tenant_audit_logs' not in existing_tables:
        op.create_table(
            'tenant_audit_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), nullable=False),
            sa.Column('action_type', sa.String(length=100), nullable=False),
            sa.Column('actor_user_id', sa.String(length=255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('details', json_type, nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        )
        existing_tables.add('tenant_audit_logs')
    if 'tenant_audit_logs' in existing_tables:
        audit_indexes = {idx["name"] for idx in inspector.get_indexes('tenant_audit_logs')}
        audit_tenant_index = op.f('ix_tenant_audit_logs_tenant_id')
        audit_created_index = op.f('ix_tenant_audit_logs_created_at')
        if audit_tenant_index not in audit_indexes:
            op.create_index(audit_tenant_index, 'tenant_audit_logs', ['tenant_id'], unique=False)
        if audit_created_index not in audit_indexes:
            op.create_index(audit_created_index, 'tenant_audit_logs', ['created_at'], unique=False)

    # ============================================================================
    # STEP 2: Add tenant_id to Existing Tables
    # ============================================================================

    # Tables to add tenant_id to
    tables_to_modify = [
        'transactions',
        'alerts',
        'cases',
        'monitoring_rules',
        'rule_hits',
        'rule_versions',
        'user_risk_profiles',
        'feature_values',
    ]

    for table_name in tables_to_modify:
        if table_name not in existing_tables:
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        if "tenant_id" in existing_columns:
            continue
        # Add tenant_id column (nullable initially, will set default tenant later)
        op.add_column(table_name, sa.Column('tenant_id', sa.String(length=255), nullable=True))

        # Create index for tenant filtering (critical for performance)
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table_name)}
        tenant_index_name = op.f(f'ix_{table_name}_tenant_id')
        if tenant_index_name not in existing_indexes:
            op.create_index(
                tenant_index_name,
                table_name,
                ['tenant_id'],
                unique=False
            )

    # ============================================================================
    # STEP 3: Create Default Tenant and Assign Existing Data
    # ============================================================================

    # Insert default tenant for existing data
    op.execute("""
        INSERT INTO tenants (tenant_id, name, display_name, is_active, tier)
        SELECT 'default', 'Default Tenant', 'Default Organization', true, 'enterprise'
        WHERE NOT EXISTS (
            SELECT 1 FROM tenants WHERE tenant_id = 'default'
        )
    """)

    # Assign all existing data to default tenant
    for table_name in tables_to_modify:
        if table_name not in existing_tables:
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
        if "tenant_id" not in existing_columns:
            continue
        op.execute(f"""
            UPDATE {table_name}
            SET tenant_id = 'default'
            WHERE tenant_id IS NULL
        """)

        # Make tenant_id NOT NULL after migration
        if bind.dialect.name != "sqlite":
            op.alter_column(table_name, 'tenant_id', nullable=False)


def downgrade():
    """Remove multi-tenancy support."""
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    # Drop indexes and tenant_id from existing tables
    tables_to_modify = [
        'transactions',
        'alerts',
        'cases',
        'monitoring_rules',
        'rule_hits',
        'rule_versions',
        'user_risk_profiles',
        'feature_values',
    ]

    for table_name in tables_to_modify:
        if table_name not in existing_tables:
            continue
        op.drop_index(op.f(f'ix_{table_name}_tenant_id'), table_name=table_name)
        op.drop_column(table_name, 'tenant_id')

    # Drop tenant audit logs
    op.drop_index(op.f('ix_tenant_audit_logs_created_at'), table_name='tenant_audit_logs')
    op.drop_index(op.f('ix_tenant_audit_logs_tenant_id'), table_name='tenant_audit_logs')
    op.drop_table('tenant_audit_logs')

    # Drop tenant users
    op.drop_index(op.f('ix_tenant_users_user_id'), table_name='tenant_users')
    op.drop_index(op.f('ix_tenant_users_tenant_id'), table_name='tenant_users')
    op.drop_table('tenant_users')

    # Drop tenant API keys
    op.drop_index(op.f('ix_tenant_api_keys_key_hash'), table_name='tenant_api_keys')
    op.drop_index(op.f('ix_tenant_api_keys_tenant_id'), table_name='tenant_api_keys')
    op.drop_table('tenant_api_keys')

    # Drop tenants
    op.drop_index(op.f('ix_tenants_tenant_id'), table_name='tenants')
    op.drop_table('tenants')
