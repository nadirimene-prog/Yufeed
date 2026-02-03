"""
Seed standard EMI + CASP policy templates.
Run: python -m scripts.seed_policy_templates
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.policy_templates import seed_policy_templates


def main() -> None:
    result = seed_policy_templates()
    print(f"✅ Seeded {result['created']} policy templates (updated {result['updated']}).")


if __name__ == "__main__":
    main()
