#!/usr/bin/env python3
"""
Pre-deployment verification script for YuFeed v2.0
Run this before deploying to staging/production
"""
import sys
import os
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    END = "\033[0m"


def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists"""
    if Path(path).exists():
        print(f"{Colors.GREEN}✓{Colors.END} {description}")
        return True
    else:
        print(f"{Colors.RED}✗{Colors.END} {description} - MISSING: {path}")
        return False


def check_migration_files() -> bool:
    """Check if migration files exist"""
    print(f"\n{Colors.BLUE}Checking Migration Files...{Colors.END}")

    migrations_dir = Path("alembic/versions")
    if not migrations_dir.exists():
        print(f"{Colors.RED}✗ Migrations directory not found{Colors.END}")
        return False

    migration_files = list(migrations_dir.glob("20260206_*.py"))

    required = ["add_ai_usage_tracking", "add_performance_indexes"]
    found = []

    for req in required:
        matching = [f for f in migration_files if req in f.name]
        if matching:
            print(f"{Colors.GREEN}✓{Colors.END} Found migration: {matching[0].name}")
            found.append(req)
        else:
            print(f"{Colors.RED}✗{Colors.END} Missing migration: {req}")

    return len(found) == len(required)


def check_code_files() -> bool:
    """Check if key implementation files exist"""
    print(f"\n{Colors.BLUE}Checking Implementation Files...{Colors.END}")

    files = [
        ("src/models/ai_usage_models.py", "AI Usage Models"),
        ("src/ai/cost_tracker.py", "AI Cost Tracker"),
        ("src/services/ai_cost_service.py", "AI Cost Service"),
        ("src/api/ai_costs.py", "AI Costs API"),
        ("src/api/reports/sar_filing.py", "SAR Filing Module"),
        ("src/api/reports/evidence.py", "Evidence Module"),
        ("src/api/reports/compliance_dashboard.py", "Compliance Dashboard"),
        ("src/api/reports/scope_analysis.py", "Scope Analysis"),
        ("src/api/reports/audit_trails.py", "Audit Trails"),
        ("src/monitoring/metrics.py", "Metrics"),
    ]

    results = [check_file_exists(f, desc) for f, desc in files]
    return all(results)


def check_documentation() -> bool:
    """Check if documentation files exist"""
    print(f"\n{Colors.BLUE}Checking Documentation...{Colors.END}")

    docs = [
        ("../../IMPLEMENTATION_COMPLETE.md", "Implementation Complete"),
        ("../../DEPLOYMENT_CHECKLIST.md", "Deployment Checklist"),
        ("../../QUICK_START.md", "Quick Start Guide"),
        ("../../STAGING_DEPLOYMENT_REPORT.md", "Staging Deployment Report"),
        ("../../monitoring/slos.yml", "SLO Definitions"),
        ("../../docs/runbooks/deployment.md", "Deployment Runbook"),
        ("../../docs/runbooks/rollback.md", "Rollback Runbook"),
    ]

    results = [check_file_exists(f, desc) for f, desc in docs]
    return all(results)


def check_alembic_config() -> bool:
    """Check Alembic configuration"""
    print(f"\n{Colors.BLUE}Checking Alembic Configuration...{Colors.END}")

    if not check_file_exists("alembic.ini", "Alembic Config"):
        return False

    if not check_file_exists("alembic/env.py", "Alembic Environment"):
        return False

    return True


def display_next_steps():
    """Display deployment instructions"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.GREEN}✓ All pre-deployment checks passed!{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")

    print(f"{Colors.YELLOW}NEXT STEPS FOR STAGING DEPLOYMENT:{Colors.END}\n")

    print("1. Access your staging server:")
    print("   ssh user@staging-server\n")

    print("2. Navigate to application directory:")
    print("   cd /path/to/yufeed\n")

    print("3. Pull latest code:")
    print("   git pull origin main\n")

    print("4. Apply database migrations:")
    print("   cd apps/api")
    print("   alembic upgrade head\n")

    print("5. Verify migration:")
    print("   alembic current")
    print("   # Should show: 20260206_indexes (head)\n")

    print("6. Restart services:")
    print("   docker-compose -f docker-compose.staging.yml up -d")
    print("   # OR")
    print("   kubectl rollout restart deployment/yufeed-api\n")

    print("7. Verify deployment:")
    print("   curl https://staging-api.yufeed.com/health")
    print("   curl https://staging-api.yufeed.com/metrics | grep feature_extraction\n")

    print(f"{Colors.YELLOW}IMPORTANT NOTES:{Colors.END}")
    print("- These migrations require PostgreSQL (will fail on SQLite)")
    print("- Take database backup before running migrations")
    print("- Monitor logs during deployment")
    print("- Follow DEPLOYMENT_CHECKLIST.md for complete procedure\n")

    print(f"{Colors.BLUE}Documentation:{Colors.END}")
    print("- Deployment Guide: DEPLOYMENT_CHECKLIST.md")
    print("- Quick Reference: QUICK_START.md")
    print("- Staging Report: STAGING_DEPLOYMENT_REPORT.md")
    print("- Complete Summary: IMPLEMENTATION_COMPLETE.md\n")


def main():
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}YuFeed v2.0 - Pre-Deployment Verification{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

    checks = [
        ("Migration Files", check_migration_files),
        ("Implementation Files", check_code_files),
        ("Documentation", check_documentation),
        ("Alembic Configuration", check_alembic_config),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"{Colors.RED}✗ Error checking {name}: {e}{Colors.END}")
            results.append(False)

    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    if all(results):
        display_next_steps()
        sys.exit(0)
    else:
        print(f"{Colors.RED}✗ Some checks failed. Please fix issues before deploying.{Colors.END}")
        print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
