import pytest

from src.ai import usage_instrumentation as ui


class _DummySession:
    def close(self):
        return None


class _DummyAnthropicUsage:
    input_tokens = 100
    output_tokens = 25
    cache_creation_input_tokens = 10
    cache_read_input_tokens = 5


class _DummyAnthropicResponse:
    usage = _DummyAnthropicUsage()
    model = "claude-3-haiku-20240307"
    id = "msg_123"
    stop_reason = "end_turn"


@pytest.mark.unit
def test_log_anthropic_response_usage_includes_cache_tokens(monkeypatch):
    calls = {}

    monkeypatch.setattr(ui, "SessionLocal", lambda: _DummySession())

    def fake_log_usage(**kwargs):
        calls.update(kwargs)
        return object()

    monkeypatch.setattr(ui, "log_usage", fake_log_usage)

    persisted = ui.log_anthropic_response_usage(
        _DummyAnthropicResponse(),
        context=ui.UsageLogContext(
            tenant_id="tenant_1",
            operation="test_op",
            user_id="user_1",
            request_metadata={"x": 1},
        ),
    )

    assert persisted is True
    assert calls["provider"] == "anthropic"
    assert calls["model"] == "claude-3-haiku-20240307"
    # 100 + 10 + 5 cache tokens
    assert calls["prompt_tokens"] == 115
    assert calls["completion_tokens"] == 25
    assert calls["tenant_id"] == "tenant_1"
    assert calls["operation"] == "test_op"
    assert calls["response_metadata"]["response_id"] == "msg_123"


@pytest.mark.unit
def test_log_usage_events_skips_when_tenant_missing(monkeypatch):
    monkeypatch.setattr(ui, "SessionLocal", lambda: _DummySession())
    monkeypatch.setattr(ui, "log_usage", lambda **kwargs: object())

    count = ui.log_usage_events(
        [
            {
                "provider": "anthropic",
                "model": "claude-3-haiku-20240307",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "operation": "x",
            }
        ],
        default_context=ui.UsageLogContext(tenant_id=None),
    )
    assert count == 0
