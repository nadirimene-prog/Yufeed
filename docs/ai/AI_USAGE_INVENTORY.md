# AI Usage Inventory (Production App)

This document tracks provider-billed AI call sites in `apps/api/src` and how they
are instrumented for `ai_usage_logs`.

## Tracked LLM Call Sites

| Area | File | Provider | Operation(s) | Tracking |
|---|---|---|---|---|
| Alert triage / investigation report | `apps/api/src/ai/alert_triage.py` | Anthropic | `alert_triage`, `investigation_report` | Yes |
| Regulatory enrichment | `apps/api/src/ai/regulatory_enrichment.py` | Anthropic | `regulatory_enrichment_context`, `sar_narrative_generation` | Yes |
| RAG answer generation | `apps/api/src/ai/rag_service.py` | Anthropic | `rag_answer_generation` | Yes |
| Impact analysis | `apps/api/src/ai/impact_analyzer.py` | Anthropic | `impact_analysis` | Yes |
| Policy generation (AI sections) | `apps/api/src/services/policy_generator.py` | Anthropic | `policy_generation_section` | Yes |
| Policy matcher refinement | `apps/api/src/services/policy_matcher.py` | Anthropic | `policy_match_refinement` | Yes |
| AML Officer agent base wrapper | `apps/api/src/ai/agents/base.py` | Anthropic | `agent.<agent_type>.<task_type>` | Yes |
| Document analyzer (classification/risk/obligations/deadline/summary) | `apps/api/src/ai/analyzer.py` | Anthropic/OpenAI | `document_analysis.*` sub-ops | Yes (usage events + caller logging) |

## AI-Adjacent (Not Provider-Billed LLM Calls)

| Area | File | Notes |
|---|---|---|
| Local embeddings | `apps/api/src/ai/embeddings.py` | Local `sentence-transformers`, not logged to `ai_usage_logs` |
| RAG retrieval / search | `apps/api/src/ai/rag_service.py` | OpenSearch retrieval only; no provider token billing |
| RAG indexing | `apps/api/src/ai/rag_indexer.py` | Chunking + indexing + embeddings |

## Telemetry Infrastructure

- Persistence and cost estimation: `apps/api/src/ai/cost_tracker.py`
- Shared instrumentation helpers: `apps/api/src/ai/usage_instrumentation.py`
- Aggregation API service: `apps/api/src/services/ai_cost_service.py`
- Usage API routes: `apps/api/src/api/ai_costs.py`

## Notes

- Dashboard count is currently shown as **Tracked AI usage (30d)**.
- `tracking_status` is returned as `partial` until the team completes runtime verification across all flows in staging.
- Scripts under `apps/api/scripts` are excluded from production telemetry guardrails.
