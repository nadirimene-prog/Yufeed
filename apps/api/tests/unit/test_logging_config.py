import logging
import os

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from src.monitoring import logging_config


@pytest.mark.unit
def test_logging_helpers_and_context(monkeypatch):
    logging_config.clear_context()
    logging_config.set_request_id("req-1")
    logging_config.set_correlation_id("corr-1")
    logging_config.set_user_id("user-1")

    event = logging_config.add_app_context(logging.getLogger(__name__), "info", {})
    assert event["request_id"] == "req-1"
    assert event["correlation_id"] == "corr-1"
    assert event["user_id"] == "user-1"

    event = logging_config.add_timestamp(logging.getLogger(__name__), "info", {})
    assert event["timestamp"].endswith("Z")

    event = logging_config.add_log_level(logging.getLogger(__name__), "warning", {})
    assert event["level"] == "warn"

    logging_config.clear_context()


@pytest.mark.unit
def test_stdlib_logging_and_patch(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    logging_config.configure_stdlib_logging()

    logging_config._patch_logger_for_kwargs()
    logger = logging.getLogger("test_logger")
    logger.info("hello", extra_field="value")


@pytest.mark.unit
def test_get_logger_fallback(monkeypatch):
    monkeypatch.setattr(logging_config, "STRUCTLOG_AVAILABLE", False)
    logger = logging_config.get_logger("fallback")
    logger.info("event", foo="bar")
    logger.warning("warn", code=1)


@pytest.mark.unit
def test_logging_middleware_adds_headers():
    app = FastAPI()
    app.add_middleware(logging_config.LoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ping", headers={"x-request-id": "req-123"})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == "req-123"
    assert resp.headers.get("x-correlation-id") == "req-123"


@pytest.mark.unit
def test_sampled_logging_middleware():
    app = FastAPI()
    app.add_middleware(logging_config.SampledLoggingMiddleware, sample_rate=1.0)

    @app.get("/ping")
    def ping():
        return JSONResponse({"ok": True})

    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
