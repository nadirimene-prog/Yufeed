# Repo Hardening Audit (2026-02-17)

## Scope

Repository hygiene, CI reliability, and developer workflow consistency for the monorepo.

## Findings

1. Tracked temporary artifacts and backup files were present in git history.
2. CI backend test job installed runtime dependencies only, but executed `pytest`.
3. Frontend CI uploaded coverage without generating coverage artifacts.
4. Security scan used an unpinned action reference (`@master`), which is not reproducible.
5. No canonical top-level command interface existed for local verification and CI parity.

## Remediations implemented

1. Removed tracked temporary artifacts and backup snapshots:
   - `apps/api/extraction_progress.json`
   - `apps/api/fix_report.json`
   - `apps/api/full_reextraction_report.json`
   - `apps/api/reextraction_report.json`
   - `apps/web/SYNC_TEST.txt`
   - `apps/web/src/app/globals.css.backup.20260217_073601`
   - `apps/web/src/app/layout.tsx.backup.20260217_073601`
   - `apps/web/src/app/page.tsx.backup.20260217_073601`
2. Added preventive ignore rules for generated reports, lint outputs, and backup file patterns.
3. Hardened CI:
   - added workflow concurrency cancellation
   - installed backend `requirements-dev.txt` before tests
   - switched frontend tests to coverage-producing command
   - pinned Trivy action to a fixed release
4. Added a root `Makefile` to standardize setup, linting, testing, build, and CI commands.
5. Updated `README.md` to document production-grade developer workflow and hygiene rules.
6. Tightened lint rigor without breaking delivery:
   - reduced Python flake8 suppression baseline from 16 ignored codes to 7
   - removed stale wildcard export (`F403`) in `apps/api/src/schemas/__init__.py`
   - enforced frontend zero-warning lint gate (`--max-warnings=0`)
   - removed dead duplicate file `apps/web/src/components/ui/button.tsx` and dropped its ESLint global ignore
   - removed `F541` and `E731` from the backend lint ignore baseline by fixing all violations

## Remaining recommendations

1. Enforce branch protection with required status checks (`backend-tests`, `frontend-tests`, `security-scan`, `code-quality`).
2. Add CodeQL/static analysis workflow for deeper code-level vulnerability scanning.
3. Replace broad lint suppressions over time with targeted fixes to reduce hidden risk.
