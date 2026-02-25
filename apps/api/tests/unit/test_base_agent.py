import pytest

from src.ai.agents.base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentType,
    ActionRecommendation,
    ConfidenceLevel,
)


class DummyAgent(BaseAgent[AgentResult]):
    @property
    def agent_type(self):
        return AgentType.TRIAGE

    @property
    def system_prompt(self):
        return "system"

    async def process(self, context: AgentContext) -> AgentResult:
        return AgentResult(agent_type=self.agent_type, summary="ok")


@pytest.mark.unit
def test_base_agent_cache_and_builders():
    agent = DummyAgent(api_key=None)
    context = AgentContext(session_id="sess-1", user_id="user")

    key = agent._get_cache_key(context)
    assert key

    result = AgentResult(agent_type=AgentType.TRIAGE, summary="done")
    agent._set_cache(context, result)
    cached = agent._check_cache(context)
    assert cached is result

    chain = agent.build_reasoning_chain(
        [{"description": "step", "evidence": ["a"], "conclusion": "ok", "confidence": 0.7}]
    )
    assert chain[0].description == "step"

    citations = agent.build_citations([{"source_type": "regulation", "reference": "AML"}])
    assert citations[0].reference == "AML"

    assert agent.calculate_confidence_level(0.9) == ConfidenceLevel.HIGH


@pytest.mark.unit
def test_agent_context_to_dict_includes_tenant_and_input_data():
    context = AgentContext(
        session_id="sess-ctx",
        user_id="user-1",
        tenant_id="tenant-1",
        input_data={"action": "answer_question"},
    )
    payload = context.to_dict()
    assert payload["tenant_id"] == "tenant-1"
    assert payload["input_data"] == {"action": "answer_question"}


@pytest.mark.unit
def test_base_agent_auto_act():
    agent = DummyAgent(api_key=None)

    result = AgentResult(
        agent_type=AgentType.TRIAGE,
        confidence=0.95,
        confidence_level=ConfidenceLevel.HIGH,
        recommendation=ActionRecommendation.FALSE_POSITIVE,
    )
    assert agent.should_auto_act(result) is True

    result2 = AgentResult(
        agent_type=AgentType.TRIAGE,
        confidence=0.85,
        confidence_level=ConfidenceLevel.HIGH,
        recommendation=ActionRecommendation.ESCALATE,
    )
    assert agent.should_auto_act(result2) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_base_agent_call_claude_mock_response(monkeypatch):
    agent = DummyAgent(api_key=None)
    # Force deterministic mock path regardless of local env keys.
    agent.is_configured = False
    context = AgentContext(session_id="sess-2")

    response = await agent.call_claude("prompt", context)
    assert "summary" in response
    assert response.get("_meta")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_base_agent_call_claude_logs_usage_when_configured(monkeypatch):
    agent = DummyAgent(api_key=None)
    agent.is_configured = True

    class DummyMessages:
        def create(self, *args, **kwargs):
            return None

    class DummyClient:
        messages = DummyMessages()

    class DummyUsage:
        input_tokens = 12
        output_tokens = 8

    class DummyChunk:
        text = "hello"

    class DummyResponse:
        content = [DummyChunk()]
        usage = DummyUsage()
        model = "claude-sonnet-4-20250514"
        id = "msg_test"
        stop_reason = "end_turn"

    agent.client = DummyClient()

    called = {"count": 0}
    monkeypatch.setattr(
        "src.ai.agents.base.anthropic_breaker.call",
        lambda _fn, **kwargs: DummyResponse(),
    )
    monkeypatch.setattr(
        "src.ai.agents.base.log_anthropic_response_usage",
        lambda response, context: called.__setitem__("count", called["count"] + 1) or True,
    )

    context = AgentContext(session_id="sess-3", tenant_id="default", task_type="test_task")
    response = await agent.call_claude("prompt", context, json_mode=False)

    assert called["count"] == 1
    assert response["content"] == "hello"
