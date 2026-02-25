import pytest
from types import SimpleNamespace

from src.ai.rag_service import RAGService
from src.ai.regulatory_enrichment import RegulatoryEnrichmentService
from src.ai.impact_analyzer import ImpactAnalyzer
from src.services.policy_generator import PolicyGenerator
from src.services.policy_matcher import PolicyMatcher


class _DummyAnthropicResponse:
    def __init__(self, text: str, model: str = "claude-3-haiku-20240307"):
        self.content = [SimpleNamespace(text=text)]
        self.usage = SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        self.model = model
        self.id = "msg_test"
        self.stop_reason = "end_turn"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_generate_answer_logs_usage(monkeypatch):
    captured = {}

    class _DummyMessages:
        async def create(self, **kwargs):
            return _DummyAnthropicResponse("RAG answer", model=kwargs["model"])

    service = RAGService(None)
    service.client = SimpleNamespace(messages=_DummyMessages())

    monkeypatch.setattr(
        "src.ai.rag_service.log_anthropic_response_usage",
        lambda response, context: captured.update(
            {
                "model": response.model,
                "operation": context.operation,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "request_metadata": dict(context.request_metadata or {}),
            }
        )
        or True,
    )

    result = await service._generate_answer(
        "What changed?",
        [{"celex": "32024R0001", "title": "Reg", "chunk_text": "x", "score": 6.0}],
        filters={"compliance_domain": "aml"},
        tenant_id="default",
        user_id="user-1",
    )

    assert result["answer"] == "RAG answer"
    assert captured["operation"] == "rag_answer_generation"
    assert captured["tenant_id"] == "default"
    assert captured["user_id"] == "user-1"
    assert captured["request_metadata"]["filters_present"] is True
    assert captured["request_metadata"]["retrieved_chunks"] == 1


@pytest.mark.unit
def test_regulatory_enrichment_logs_context_and_sar_narrative_usage(db_session, monkeypatch):
    service = RegulatoryEnrichmentService(db_session)
    service.client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: _DummyAnthropicResponse("ok", kwargs["model"])
        )
    )

    calls = []
    monkeypatch.setattr(
        "src.ai.regulatory_enrichment.log_anthropic_response_usage",
        lambda response, context: calls.append(
            {
                "operation": context.operation,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "request_metadata": dict(context.request_metadata or {}),
            }
        )
        or True,
    )

    alert = SimpleNamespace(
        id=123,
        tenant_id="default",
        user_id="user-1",
        alert_type="velocity",
        severity="high",
        description="Unusual velocity pattern",
    )

    context = service._generate_regulatory_context(alert, None, None, [])
    narrative = service._generate_sar_narrative("SAR base context", alert=alert)

    assert context == "ok"
    assert narrative == "ok"
    ops = [c["operation"] for c in calls]
    assert "regulatory_enrichment_context" in ops
    assert "sar_narrative_generation" in ops
    assert all(c["tenant_id"] == "default" for c in calls)


@pytest.mark.unit
def test_impact_analyzer_logs_usage(monkeypatch):
    analyzer = ImpactAnalyzer()
    analyzer.client = SimpleNamespace(
        messages=SimpleNamespace(
            create=lambda **kwargs: _DummyAnthropicResponse(
                '{"overall_impact_level":"low","executive_summary":"","affected_areas":[],"key_changes":[],"action_items":[],"gaps":[],"resource_estimates":{}}',
                kwargs["model"],
            )
        )
    )

    captured = {}
    monkeypatch.setattr(
        "src.ai.impact_analyzer.log_anthropic_response_usage",
        lambda response, context: captured.update(
            {
                "operation": context.operation,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "document_id": context.document_id,
                "request_metadata": dict(context.request_metadata or {}),
            }
        )
        or True,
    )

    out = analyzer.analyze_impact(
        {"celex": "CELEX-1", "title": "Impact", "type": "regulation", "compliance_domain": "aml"},
        tenant_id="default",
        user_id="user-1",
        document_id=44,
    )

    assert out["overall_impact_level"] == "low"
    assert captured["operation"] == "impact_analysis"
    assert captured["document_id"] == 44
    assert captured["request_metadata"]["celex"] == "CELEX-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_generator_ai_section_logs_usage(db_session, monkeypatch):
    generator = PolicyGenerator(db_session)

    class _DummyMessages:
        async def create(self, **kwargs):
            return _DummyAnthropicResponse("Generated policy body", kwargs["model"])

    generator.client = SimpleNamespace(messages=_DummyMessages())

    captured = {}
    monkeypatch.setattr(
        "src.services.policy_generator.log_anthropic_response_usage",
        lambda response, context: captured.update(
            {
                "operation": context.operation,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "request_metadata": dict(context.request_metadata or {}),
            }
        )
        or True,
    )

    section = {"name": "Controls", "ai_instructions": "Write controls"}
    obligations = [
        SimpleNamespace(
            id=1,
            _doc_title="AML Regulation",
            _celex="32024R0001",
            article_ref="33",
            obligation_text="Banks shall maintain records and controls.",
        )
    ]
    text = await generator._generate_ai_section(
        section=section,
        obligations=obligations,
        variables={"institution_name": "Bank"},
        telemetry_context={
            "tenant_id": "default",
            "user_id": "user-1",
            "job_id": "job-1",
            "template_id": "tmpl-1",
        },
    )

    assert text == "Generated policy body"
    assert captured["operation"] == "policy_generation_section"
    assert captured["request_metadata"]["job_id"] == "job-1"
    assert captured["request_metadata"]["template_id"] == "tmpl-1"
    assert captured["request_metadata"]["obligation_count"] == 1


@pytest.mark.unit
def test_policy_matcher_llm_refine_logs_usage(monkeypatch):
    import src.services.policy_matcher as policy_matcher_module
    import anthropic

    calls = []

    class _DummyAnthropic:
        def __init__(self, api_key=None):
            self.messages = SimpleNamespace(
                create=lambda **kwargs: _DummyAnthropicResponse(
                    '{"items":[{"policy_document_id":1,"confidence":0.9,"reasoning":"best fit"}]}',
                    kwargs["model"],
                )
            )

    monkeypatch.setattr(policy_matcher_module, "get_current_tenant", lambda: "default")
    monkeypatch.setattr(
        policy_matcher_module,
        "log_anthropic_response_usage",
        lambda response, context: calls.append(
            {
                "operation": context.operation,
                "request_metadata": dict(context.request_metadata or {}),
            }
        )
        or True,
    )
    monkeypatch.setattr(policy_matcher_module.settings, "POLICY_MATCH_ENABLE_LLM_REFINEMENT", True)
    monkeypatch.setattr(policy_matcher_module.settings, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(anthropic, "Anthropic", _DummyAnthropic)

    matcher = PolicyMatcher.__new__(PolicyMatcher)

    refined = matcher._llm_refine(
        "Banks must monitor suspicious transactions",
        [
            {
                "policy_document_id": 1,
                "policy_id": "POL-1",
                "name": "AML Policy",
                "score": 0.4,
                "confidence": 0.4,
                "reasoning": "semantic",
            }
        ],
    )

    assert refined[0]["confidence"] == pytest.approx(0.9)
    assert calls[0]["operation"] == "policy_match_refinement"
    assert calls[0]["request_metadata"]["candidate_count"] == 1


@pytest.mark.unit
def test_policy_matcher_persists_and_reuses_policy_embeddings(monkeypatch):
    import src.services.policy_matcher as policy_matcher_module

    policy_matcher_module._POLICY_EMBED_CACHE.clear()

    class _FakeDB:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    class _FakeEmbeddingProvider:
        def __init__(self):
            self.model_name = "BAAI/bge-m3"
            self.calls = 0

        def embed_texts(self, texts):
            self.calls += 1
            return [[0.1, 0.2, 0.3] for _ in texts]

    db = _FakeDB()
    provider = _FakeEmbeddingProvider()

    matcher = PolicyMatcher.__new__(PolicyMatcher)
    matcher.db = db
    matcher.user_id = "2"
    matcher.embedding_provider = provider

    policy = SimpleNamespace(
        id=42,
        policy_id="P-42",
        name="Test Policy",
        content="AML controls and suspicious transaction reporting",
        metadata_json={},
        updated_at=None,
    )

    rows = matcher._prime_policy_embedding_cache([policy])
    assert provider.calls == 1
    assert len(rows) == 1

    matcher._persist_policy_embedding_cache(rows)
    assert db.commits == 1
    assert "_yufeed_policy_embeddings" in policy.metadata_json

    policy_matcher_module._POLICY_EMBED_CACHE.clear()
    provider.embed_texts = lambda texts: pytest.fail("embed_texts should not be called")

    rows2 = matcher._prime_policy_embedding_cache([policy])
    assert rows2 == []


@pytest.mark.unit
def test_policy_matcher_low_latency_skips_llm_refine(monkeypatch):
    matcher = PolicyMatcher.__new__(PolicyMatcher)
    matcher.embedding_provider = SimpleNamespace(available=True, model_name="BAAI/bge-m3")
    matcher._embed_text = lambda text: [1.0, 0.0]
    matcher._prime_policy_embedding_cache = lambda policies: []
    matcher._persist_policy_embedding_cache = lambda rows: None
    matcher._cached_policy_embedding = lambda policy: [1.0, 0.0]
    matcher._llm_refine = lambda *args, **kwargs: pytest.fail("_llm_refine should not be called")

    policy = SimpleNamespace(
        id=1,
        policy_id="POL-1",
        name="AML Policy",
        metadata_json={"category": "AML/CFT"},
        updated_at=None,
    )
    out = matcher._semantic_suggestions(
        "monitor suspicious activity",
        [policy],
        limit=3,
        enable_llm_refinement=False,
    )

    assert out
    assert out[0]["match_method"] == "semantic"
    assert out[0]["policy_id"] == "POL-1"


@pytest.mark.unit
def test_policy_matcher_budget_skips_llm_refine(monkeypatch):
    import src.services.policy_matcher as policy_matcher_module

    matcher = PolicyMatcher.__new__(PolicyMatcher)
    matcher.embedding_provider = SimpleNamespace(available=True, model_name="BAAI/bge-m3")
    matcher._embed_text = lambda text: [1.0, 0.0]
    matcher._prime_policy_embedding_cache = lambda policies: []
    matcher._persist_policy_embedding_cache = lambda rows: None
    matcher._cached_policy_embedding = lambda policy: [1.0, 0.0]
    matcher._llm_refine = lambda *args, **kwargs: pytest.fail("_llm_refine should not be called")

    times = iter([0.0, 1.0])  # ~1000ms elapsed before refine
    monkeypatch.setattr(policy_matcher_module.time, "perf_counter", lambda: next(times))

    policy = SimpleNamespace(
        id=1,
        policy_id="POL-1",
        name="AML Policy",
        metadata_json={"category": "AML/CFT"},
        updated_at=None,
    )
    out = matcher._semantic_suggestions(
        "monitor suspicious activity",
        [policy],
        limit=3,
        llm_refine_budget_ms=10,
    )

    assert out
    assert out[0]["match_method"] == "semantic"
