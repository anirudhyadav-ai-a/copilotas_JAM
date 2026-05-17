"""Tests for the webhook handler.

Phase 0 | CI/CD Governance — Webhook Handler
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "webhook_handler_main", Path(__file__).parent / "main.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

WebhookEvent = _mod.WebhookEvent
WebhookVerifier = _mod.WebhookVerifier
EventRouter = _mod.EventRouter
OverrideCommandParser = _mod.OverrideCommandParser


class TestWebhookVerifier:
    def test_no_secret_skips_verification(self):
        verifier = WebhookVerifier(secret="")
        assert verifier.verify(b"any body", "any signature") is True

    def test_valid_signature(self):
        import hashlib
        import hmac

        secret = "test-secret"
        body = b'{"action": "opened"}'
        expected = (
            "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        )

        verifier = WebhookVerifier(secret=secret)
        assert verifier.verify(body, expected) is True

    def test_invalid_signature(self):
        verifier = WebhookVerifier(secret="test-secret")
        assert verifier.verify(b"body", "sha256=invalid") is False


class TestEventRouter:
    def test_route_pr_opened(self):
        router = EventRouter()
        event = WebhookEvent(
            event_type="pull_request",
            action="opened",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={},
        )
        assert router.route(event) == "full_review"

    def test_route_pr_reopened(self):
        router = EventRouter()
        event = WebhookEvent(
            event_type="pull_request",
            action="reopened",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={},
        )
        assert router.route(event) == "full_review"

    def test_route_pr_synchronize(self):
        router = EventRouter()
        event = WebhookEvent(
            event_type="pull_request",
            action="synchronize",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={},
        )
        assert router.route(event) == "incremental_review"

    def test_route_override_comment(self):
        router = EventRouter()
        event = WebhookEvent(
            event_type="issue_comment",
            action="created",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={"comment": {"body": "/judge-override reason"}},
        )
        assert router.route(event) == "override_command"

    def test_route_ignored_event(self):
        router = EventRouter()
        event = WebhookEvent(
            event_type="push",
            action="",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={},
        )
        assert router.route(event) == "ignored"

    def test_route_review_submitted(self):
        router = EventRouter()
        event = WebhookEvent(
            event_type="pull_request_review",
            action="submitted",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={},
        )
        assert router.route(event) == "review_submitted"


class TestOverrideCommandParser:
    def test_parse_override(self):
        parser = OverrideCommandParser()
        event = WebhookEvent(
            event_type="issue_comment",
            action="created",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={
                "comment": {
                    "body": "/judge-override False positive in test fixture",
                    "user": {"login": "lead-dev"},
                },
                "issue": {"number": 42},
            },
        )
        cmd = parser.parse(event)
        assert cmd is not None
        assert cmd.user == "lead-dev"
        assert cmd.reason == "False positive in test fixture"
        assert cmd.pr_number == 42

    def test_parse_no_override(self):
        parser = OverrideCommandParser()
        event = WebhookEvent(
            event_type="issue_comment",
            action="created",
            delivery_id="d1",
            repo="org/repo",
            sender="dev",
            payload={"comment": {"body": "LGTM", "user": {"login": "dev"}}},
        )
        cmd = parser.parse(event)
        assert cmd is None
