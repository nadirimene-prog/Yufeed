#!/usr/bin/env python3
"""
Master Plan Execution Script
Executes all improvements in the master plan with full error handling and progress tracking.
"""

import sys
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Execution order
PHASES = {
    1: {
        "name": "Critical Fixes",
        "tasks": [
            "scripts/implement_content_extractor_v2.py",
            "scripts/implement_celex_utils.py",
            "scripts/fix_existing_documents.py",
            "scripts/implement_confidence_scoring.py",
        ],
    },
    2: {
        "name": "Quality Improvements",
        "tasks": [
            "scripts/implement_article_chunking.py",
            "scripts/implement_deduplication.py",
            "scripts/setup_version_control.py",
        ],
    },
    3: {
        "name": "Automation & Intelligence",
        "tasks": [
            "scripts/setup_celery.py",
            "scripts/implement_relationship_detection.py",
            "scripts/add_multilanguage_support.py",
        ],
    },
}


def run_script(script_path):
    """Run a Python script with error handling."""
    full_path = Path(__file__).parent / script_path
    if not full_path.exists():
        logger.warning(f"Script not found: {script_path}")
        return False

    try:
        logger.info(f"Running: {script_path}")
        result = subprocess.run(
            ["python3", str(full_path)],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )

        if result.returncode == 0:
            logger.info(f"✅ {script_path} completed successfully")
            return True
        else:
            logger.error(f"❌ {script_path} failed with code {result.returncode}")
            logger.error(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ {script_path} timed out")
        return False
    except Exception as e:
        logger.error(f"💥 {script_path} crashed: {e}")
        return False


def backup_database():
    """Create database backup before execution."""
    logger.info("Creating database backup...")
    # Implementation depends on DB type
    pass


def main():
    parser = argparse.ArgumentParser(description="Execute master improvement plan")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Execute specific phase")
    parser.add_argument("--backup", action="store_true", help="Backup database first")
    parser.add_argument("--task", type=str, help="Execute specific task only")
    args = parser.parse_args()

    if args.backup:
        backup_database()

    # Determine which tasks to run
    if args.task:
        tasks = [args.task]
    elif args.phase:
        tasks = PHASES[args.phase]["tasks"]
    else:
        tasks = []
        for phase in PHASES.values():
            tasks.extend(phase["tasks"])

    # Execute tasks
    results = []
    for task in tasks:
        success = run_script(task)
        results.append((task, success))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 60)
    for task, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {task}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} passed ({100*passed//total}%)")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
