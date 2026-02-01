import pytest

from src.monitoring import tracing


class DummySpan:
    def __init__(self):
        self.attributes = {}
        self.events = []
        self.exceptions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def add_event(self, name, attributes=None):
        self.events.append((name, attributes))

    def record_exception(self, exc):
        self.exceptions.append(exc)


class DummyTracer:
    def __init__(self, span):
        self.span = span

    def start_as_current_span(self, name):
        return self.span


class DummyTraceModule:
    def __init__(self, span):
        self._span = span

    def get_tracer(self, name=None):
        return DummyTracer(self._span)

    def get_current_span(self):
        return self._span


@pytest.mark.unit
def test_tracing_noop(monkeypatch):
    monkeypatch.setattr(tracing, "TRACE_AVAILABLE", False)
    tracer = tracing.get_tracer("x")
    with tracer.start_as_current_span("span"):
        pass

    # Decorator returns original when tracing disabled
    @tracing.traced()
    def add(a, b):
        return a + b

    assert add(1, 2) == 3


@pytest.mark.unit
def test_tracing_attributes_and_decorator(monkeypatch):
    span = DummySpan()
    dummy_trace = DummyTraceModule(span)
    monkeypatch.setattr(tracing, "TRACE_AVAILABLE", True)
    monkeypatch.setattr(tracing, "trace", dummy_trace)

    @tracing.traced(span_name="test.span", attributes={"service": "unit"})
    def work(x):
        return x * 2

    result = work(3)
    assert result == 6
    assert span.attributes.get("service") == "unit"
    assert span.attributes.get("success") is True

    tracing.add_span_attributes({"key": "value"})
    tracing.add_span_event("event", {"a": 1})
    tracing.record_exception(RuntimeError("boom"))
    assert span.attributes.get("key") == "value"
    assert span.events
    assert span.exceptions
