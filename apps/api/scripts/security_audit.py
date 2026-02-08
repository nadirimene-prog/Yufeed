#!/usr/bin/env python3
"""
Static security/tenant isolation audit.

This is a fast, repo-aware check meant to run in CI to prevent regressions in
tenant scoping and obvious secret leaks. It is intentionally conservative to
avoid false positives.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Finding:
    check: str
    message: str
    path: Optional[Path] = None

    def format(self) -> str:
        if self.path:
            return f"[{self.check}] {self.message} ({self.path})"
        return f"[{self.check}] {self.message}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _require_substrings(check: str, path: Path, required: Iterable[str]) -> List[Finding]:
    if not path.exists():
        return [Finding(check=check, message="File missing", path=path)]

    text = _read_text(path)
    findings: List[Finding] = []
    for needle in required:
        if needle not in text:
            findings.append(
                Finding(check=check, message=f"Missing required pattern: {needle!r}", path=path)
            )
    return findings


def _scan_for_secrets(source_root: Path) -> List[Finding]:
    patterns = [
        (re.compile(r"AKIA[0-9A-Z]{16}"), "Possible AWS access key id"),
        (re.compile(r"-----BEGIN (RSA|OPENSSH) PRIVATE KEY-----"), "Private key material"),
        (re.compile(r"sk-[A-Za-z0-9]{20,}"), "Possible API key"),
        (re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"), "Possible Slack token"),
    ]

    findings: List[Finding] = []
    for path in source_root.rglob("*.py"):
        text = _read_text(path)
        for regex, desc in patterns:
            if regex.search(text):
                findings.append(Finding(check="secrets", message=desc, path=path))
    return findings


def run(repo_api_root: Path) -> List[Finding]:
    src = repo_api_root / "src"

    checks = [
        (
            "feature_refresh",
            src / "tasks" / "feature_refresh.py",
            [
                "TenantContext",
                "Transaction.tenant_id == tenant_id",
                "FeatureValue.tenant_id == tenant_id",
            ],
        ),
        (
            "time_series_features",
            src / "services" / "time_series_features.py",
            ["Transaction.tenant_id == tenant_id"],
        ),
        (
            "feature_store_cache",
            src / "services" / "feature_store.py",
            [
                "def _cache_key",
                'f"{tenant_id}:{entity_type}:{entity_id}:v{version}"',
            ],
        ),
        (
            "transaction_processing_task",
            src / "tasks" / "transaction_processing.py",
            [
                "TenantContext",
                "Transaction.tenant_id == tenant_id",
            ],
        ),
        (
            "rules_engine_scoping",
            src / "services" / "rules_engine.py",
            [
                "MonitoringRule.tenant_id",
                "Transaction.tenant_id",
                "rule_coercion_failures_total",
            ],
        ),
        (
            "risk_scoring_scoping",
            src / "services" / "risk_scoring.py",
            [
                "Transaction.tenant_id == tenant_id",
                "Alert.tenant_id == tenant_id",
            ],
        ),
        (
            "websocket_endpoint_auth",
            src / "api" / "websocket.py",
            ['tenant_id = payload.get("tenant_id")'],
        ),
        (
            "websocket_manager_scoping",
            src / "websocket" / "manager.py",
            [
                "send_to_tenant_user",
                "broadcast_to_tenant",
                "broadcast_global",
                "Tuple[str, str]",
            ],
        ),
        (
            "audit_models_tenant_id",
            src / "audit" / "models.py",
            [
                "tenant_id = Column",
                "class EventRecord",
                "class DecisionRecord",
            ],
        ),
    ]

    findings: List[Finding] = []
    for check, path, required in checks:
        findings.extend(_require_substrings(check, path, required))

    findings.extend(_scan_for_secrets(src))
    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Static security/tenant isolation audit")
    parser.add_argument(
        "--mode",
        choices=["warn", "fail"],
        default="fail",
        help="warn: exit 0 even if issues found; fail: exit 1 on findings",
    )
    args = parser.parse_args(argv)

    api_root = Path(__file__).resolve().parents[1]
    findings = run(api_root)

    if findings:
        print("Security audit findings:")
        for finding in findings:
            print(f" - {finding.format()}")
        return 0 if args.mode == "warn" else 1

    print("Security audit passed (no findings).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
