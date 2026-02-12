from __future__ import annotations

from pathlib import Path
import re
import sys


FILE = Path("apps/api/src/services/rules_engine.py")

NEW_TRY_BLOCK = r"""
        # Finding-first: normalize velocity alert as a finding
        try:
            user_id = transaction.user_id
            tenant_id = transaction.tenant_id

            fingerprint_key = f"{tenant_id}:TX_ALERT:VELOCITY:{user_id}:{rule.rule_id}"
            fingerprint = (
                __import__("hashlib").sha256(fingerprint_key.encode("utf-8")).hexdigest()[:128]
            )

            finding = (
                self.db.query(Finding)
                .filter(Finding.tenant_id == tenant_id, Finding.fingerprint == fingerprint)
                .first()
            )

            if not finding:
                finding = Finding(
                    tenant_id=tenant_id,
                    finding_type="TX_ALERT",
                    severity=(rule.severity or "").lower() or None,
                    status=FindingStatus.new.value,
                    title=f"Velocity: {rule.name}",
                    summary=f"Velocity rule triggered for user {user_id}",
                    fingerprint=fingerprint,
                    source_refs_json={
                        "alert_id": alert_id,
                        "user_id": user_id,
                        "rule_id": rule.rule_id,
                        "transaction_id": transaction.id,
                        "transactions": evidence.get("transactions"),
                    },
                    explainability_json={
                        "evidence": evidence,
                        "matched_rules": {rule.rule_id: rule.name},
                        "regulation_context": regulation_context,
                        "related_regulations": related_regulations,
                    },
                )
                self.db.add(finding)
            else:
                finding.updated_at = utc_now()
                finding.source_refs_json = {
                    **(finding.source_refs_json or {}),
                    "alert_id": alert_id,
                    "last_triggered_at": utc_now().isoformat(),
                }
                if finding.status == FindingStatus.closed.value:
                    finding.status = FindingStatus.new.value
        except Exception:
            pass
""".lstrip("\n")


def main() -> int:
    if not FILE.exists():
        print(f"ERROR: file not found: {FILE}", file=sys.stderr)
        return 2

    text = FILE.read_text(encoding="utf-8")

    # We replace the whole try/except block right after the marker comment.
    pattern = re.compile(
        r"""
(^[ \t]*\#\ Finding-first:\ normalize\ velocity\ alert\ as\ a\ finding[ \t]*\n)  # marker
([ \t]*try:\n)                                                                  # try
(?:.*?\n)                                                                       # body (non-greedy)
([ \t]*except\ Exception:\n[ \t]*pass[ \t]*\n)                                  # except
""",
        re.VERBOSE | re.MULTILINE | re.DOTALL,
    )

    m = pattern.search(text)
    if not m:
        print("ERROR: target try/except block not found. No changes made.", file=sys.stderr)
        return 3

    start = m.start(1)
    end = m.end(3)

    replacement = NEW_TRY_BLOCK
    new_text = text[:start] + replacement + text[end:]

    if new_text == text:
        print("No changes needed (already fixed).")
        return 0

    FILE.write_text(new_text, encoding="utf-8")
    print(f"Patched: {FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
