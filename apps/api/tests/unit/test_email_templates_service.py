import pytest
from datetime import datetime, timezone

from src import email_templates
from src import email_service


class FakeSMTP:
    last_instance = None

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = False
        self.sent = []
        FakeSMTP.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = True

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.mark.unit
def test_email_templates_rendering():
    header = email_templates.get_email_header()
    footer = email_templates.get_email_footer()
    assert "<html" in header
    assert "</html>" in footer

    empty_digest = email_templates.daily_digest_template([])
    assert "No new documents" in empty_digest

    digest = email_templates.daily_digest_template(
        [
            {
                "title": "AML Doc",
                "celex": "32020R0001",
                "risk_level": "high",
                "compliance_domain": "aml",
            }
        ],
        date="January 01, 2024",
    )
    assert "HIGH RISK" in digest
    assert "AML" in digest

    watchlist = email_templates.watchlist_alert_template(
        "My Watchlist",
        [{"title": "Doc", "celex": "C1", "publication_date": "2024-01-01"}],
    )
    assert "My Watchlist" in watchlist
    assert "Doc" in watchlist

    compliance = email_templates.compliance_alert_template(
        [{"title": "High", "celex": "H1", "compliance_domain": "aml"}],
        [
            {
                "title": "Soon",
                "celex": "D1",
                "implementation_deadline": datetime(2024, 1, 2, tzinfo=timezone.utc),
            }
        ],
    )
    assert "HIGH RISK" in compliance
    assert "Upcoming Deadlines" in compliance
    assert "January" in compliance

    test_email = email_templates.test_email_template()
    assert "Test Email" in test_email


@pytest.mark.unit
def test_email_service_send(monkeypatch):
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "localhost", raising=False)
    monkeypatch.setattr(email_service.settings, "SMTP_PORT", 25, raising=False)
    monkeypatch.setattr(email_service.settings, "SMTP_TLS", True, raising=False)
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "user", raising=False)
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "pass", raising=False)
    monkeypatch.setattr(email_service.settings, "EMAILS_FROM_EMAIL", "from@example.com", raising=False)

    ok = email_service.send_email("to@example.com", "Subject", "<b>Hello</b>")
    assert ok is True

    smtp = FakeSMTP.last_instance
    assert smtp.started_tls is True
    assert smtp.logged_in is True
    assert smtp.sent


@pytest.mark.unit
def test_email_service_wrappers(monkeypatch):
    monkeypatch.setattr(email_service, "send_email", lambda *args, **kwargs: True)

    assert email_service.send_daily_digest(["a@example.com", "b@example.com"], []) == 2
    assert email_service.send_watchlist_alert(["a@example.com"], "Watch", []) == 1
    assert email_service.send_compliance_alert(["a@example.com"], [], []) == 1
    assert email_service.send_test_email("a@example.com") is True
