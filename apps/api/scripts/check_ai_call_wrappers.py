#!/usr/bin/env python3
"""
Static guardrail for raw provider calls in production app code.

Fails if a new direct provider invocation is introduced in `apps/api/src`
without being explicitly allowlisted. This helps preserve centralized AI usage
telemetry instrumentation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]  # apps/api
SRC = ROOT / "src"

# Existing direct call sites are allowlisted (some are instrumented in-place).
ALLOWLIST = {
    "ai/agents/base.py",
    "ai/alert_triage.py",
    "ai/analyzer.py",
    "ai/impact_analyzer.py",
    "ai/rag_service.py",
    "ai/regulatory_enrichment.py",
    "services/policy_generator.py",
    "services/policy_matcher.py",
}

PATTERNS = [
    re.compile(r"\.messages\.create\s*\("),  # Anthropic SDK
    re.compile(r"/chat/completions"),  # Raw OpenAI HTTP path
    re.compile(r"\.chat\.completions\.create\s*\("),  # OpenAI SDK
]


def main() -> int:
    violations: list[str] = []

    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel.startswith("tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(pattern.search(text) for pattern in PATTERNS):
            continue
        if rel in ALLOWLIST:
            continue
        violations.append(rel)

    if violations:
        print("Unallowlisted raw AI provider calls detected:", file=sys.stderr)
        for rel in violations:
            print(f" - apps/api/src/{rel}", file=sys.stderr)
        print(
            "Route calls through shared instrumentation or update the allowlist with justification.",
            file=sys.stderr,
        )
        return 1

    print("AI provider call wrapper check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
