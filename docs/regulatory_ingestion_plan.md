# Regulatory Ingestion Plan (EU + France)

## Scope
- **EU (Search-first)**: Eur-Lex search ingestion for PSP/EMI/PSAN scope (FR + EN), full historical coverage
- **EU (RSS)**: CELLAR ingestion feed filtered to Official Journal (L + C series), with safe fallback to all EU entries when OJ markers are missing
- **EU (OJ Act-by-Act)**: SPARQL ingestion of Official Journal act + signature metadata across all series
- **France**: Légifrance JORF feed (configurable RSS)

## Languages
- **EN + FR** for EU documents (configurable via `EURLEX_LANGUAGES`)
- **FR** for Légifrance (default)

## Schedule
- Weekly ingestion via Celery Beat (default Monday 08:00 UTC)
- Source-level schedule stored in `regulatory_sources`

## Data Flow
1. Fetch source RSS or search API (Eur-Lex Search, Cellar)
2. Normalize entries into canonical fields
3. Upsert `legal_documents` (metadata-only pass supported)
4. Store `legal_versions` + `legal_document_texts` per language (optional batch phase)
5. Record ingestion run in `ingestion_runs`
6. Store OJ act-by-act metadata in `official_journal_acts`

## Workflow (Compliance)
1. **Weekly ingest** creates/updates LegalDocument
2. **Analysis** extracts obligations into `regulatory_obligations`
3. **Head of Compliance** validates obligations (status → approved)
4. **Internal rules** created in `internal_rules`
5. **Policies/procedures** mapped in `policy_documents` and `policy_sections`
6. **Monitoring rules** linked via `internal_rule_mappings`

## Configuration (.env)
```
RSS_USER_AGENT=Yufeed/1.0
EURLEX_LANGUAGES=en,fr
EURLEX_SEARCH_TERMS_FR=prestataire de services de paiement;services de paiement;etablissement de monnaie electronique;monnaie electronique;prestataire de services sur actifs numeriques;actifs numeriques;crypto-actifs;psan;mica
EURLEX_SEARCH_TERMS_EN=payment service provider;payment services;electronic money institution;electronic money;crypto-asset service provider;virtual asset service provider;crypto-assets;emd2;psd2;psd3;mica;casp
EURLEX_SEARCH_PAGE_SIZE=100
EURLEX_OJ_START_DATE=2023-10-01
LEGIFRANCE_JORF_RSS_URL=
LEGIFRANCE_API_BASE_URL=
LEGIFRANCE_API_TOKEN= # optional (RSS works without token)
```

## Source Records
Each source is stored in `regulatory_sources` with:
- `source_key` (unique)
- `jurisdiction`, `language`, `source_type`
- `last_ingested_at`

## Notes
- EU ingestion uses CELLAR notification feed; content extraction uses EUR-Lex HTML for EN/FR.
- Légifrance documents are ingested as `FR-<hash>` internal IDs with
  the original identifier stored in `source_reference`.
- Légifrance API enrichment is optional; RSS ingestion works without a token.
- Eur-Lex Search ingestion is a metadata-first pipeline; full-text extraction runs in batches.

## Test Steps (Every Stage)
1. **Search ingestion (FR/EN)**: run metadata-only dry-run and verify `seen > 0`.
2. **Search ingestion write**: run without `--dry-run`, then verify new rows in `legal_documents`.
3. **OJ act-by-act**: run a 7-day sample with `--dry-run`, then verify act count > 0 for at least one day.
4. **OJ act-by-act write**: run without `--dry-run`, then verify `official_journal_acts` row count increases.
5. **Full-text batch**: select a small CELEX list and verify `legal_document_texts` rows + `word_count`.

---

## Implementation Status

**Date:** January 29, 2026  
**Status:** Phase 4 implementation plan ready

This ingestion plan is part of the larger **Regulatory Intelligence Pipeline** (Phase 4) which includes:

- **Phase 1:** Ingestion Enhancement (this document)
- **Phase 2:** AI Analysis & Obligation Extraction
- **Phase 3-10:** Policy Management, Internal Rules, Dashboard Integration

### Related Documentation

- Full implementation plan: `docs/product/regulatory-pipeline-plan.md`
- Product backlog (47 User Stories): `docs/product/regulatory-pipeline-backlog.md`
- Rollout validation: `docs/product/regulatory-pipeline-rollout.md`
- Policy taxonomy: `docs/product/policy-taxonomy.md`

### New Components Added

| Component | Description |
|-----------|-------------|
| `OJActFetcher` | Ingest OJ Act-by-Act via SPARQL |
| `BatchContentFetcher` | Backfill empty `full_text` fields |
| `regulatory_alerts.py` | Create alerts from approved obligations |
| `policy_writer.py` | AI-generated policy sections |
| `deadline_monitor.py` | Celery jobs for deadline tracking |
