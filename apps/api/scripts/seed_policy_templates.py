"""
Seed standard EMI + CASP policy templates.
Run: python -m scripts.seed_policy_templates
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.policy_templates import seed_policy_templates
from src.services.policy_library import ensure_master_policies


def main() -> None:
    result = seed_policy_templates()
    print(f"✅ Seeded {result['created']} policy templates (updated {result['updated']}).")
    master_result = ensure_master_policies()
    print(
        "✅ Synced master policies: "
        f"{master_result.get('created', 0)} created, "
        f"{master_result.get('updated', 0)} updated, "
        f"{master_result.get('duplicates_retired', 0)} duplicates retired."
    )


if __name__ == "__main__":
    main()
