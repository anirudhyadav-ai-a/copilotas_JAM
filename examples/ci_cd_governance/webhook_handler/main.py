"""
CI/CD Governance — Example 3: Webhook Handler

Demonstrates:
  - FastAPI server receiving GitHub webhook events
  - HMAC-SHA256 signature verification (X-Hub-Signature-256)
  - Event routing: pull_request.opened -> review, pull_request.synchronize -> incremental
  - Async background task dispatch (return 200 immediately, review in background)
  - /judge-override comment command detection

Run:
    python -m copilotas_JAM.examples.ci_cd_governance.webhook_handler.main
    # Server starts on http://localhost:8090/webhooks/github

Prerequisites:
    pip install fastapi uvicorn
    GITHUB_WEBHOOK_SECRET set in environment (or .env)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    import uvicorn
    from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class WebhookEvent:
    """Parsed GitHub webhook event."""

    event_type: str
    action: str
    delivery_id: str
    repo: str
    sender: str
    payload: dict
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class OverrideCommand:
    """Parsed /judge-override command from a comment."""

    user: str
    reason: str
    pr_number: int


# ---------------------------------------------------------------------------
# Webhook Verifier
# ---------------------------------------------------------------------------


class WebhookVerifier:
    """Verify GitHub webhook HMAC-SHA256 signatures."""

    def __init__(self, secret: str | None = None) -> None:
        self._secret = (secret or os.environ.get("GITHUB_WEBHOOK_SECRET", "")).encode()

    def verify(self, body: bytes, signature: str) -> bool:
        """Verify X-Hub-Signature-256 header against request body."""
        if not self._secret:
            return True  # no secret configured = skip verification

        expected = "sha256=" + hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Event Router
# ---------------------------------------------------------------------------


class EventRouter:
    """Route GitHub events to appropriate handlers."""

    def route(self, event: WebhookEvent) -> str:
        """Determine which handler should process this event."""
        if event.event_type == "pull_request":
            if event.action in ("opened", "reopened"):
                return "full_review"
            elif event.action == "synchronize":
                return "incremental_review"
        elif event.event_type == "issue_comment":
            body = event.payload.get("comment", {}).get("body", "")
            if "/judge-override" in body:
                return "override_command"
        elif event.event_type == "pull_request_review":
            return "review_submitted"

        return "ignored"


# ---------------------------------------------------------------------------
# Override Command Parser
# ---------------------------------------------------------------------------


class OverrideCommandParser:
    """Parse /judge-override commands from issue comments."""

    def parse(self, event: WebhookEvent) -> OverrideCommand | None:
        """Extract override command from comment body."""
        comment = event.payload.get("comment", {})
        body = comment.get("body", "")

        if "/judge-override" not in body:
            return None

        # Extract reason after the command
        parts = body.split("/judge-override", 1)
        reason = parts[1].strip() if len(parts) > 1 else "No reason provided"
        # Take only the first line as reason
        reason = reason.split("\n")[0].strip() or "No reason provided"

        pr_number = event.payload.get("issue", {}).get("number", 0)
        user = comment.get("user", {}).get("login", "unknown")

        return OverrideCommand(user=user, reason=reason, pr_number=pr_number)


# ---------------------------------------------------------------------------
# Background Task Dispatcher
# ---------------------------------------------------------------------------

_event_log: list[dict] = []


async def process_review(event: WebhookEvent, review_type: str) -> None:
    """Background task: run the actual PR review."""
    pr = event.payload.get("pull_request", {})
    pr_number = pr.get("number", 0)
    _event_log.append(
        {
            "type": review_type,
            "pr": pr_number,
            "repo": event.repo,
            "time": event.received_at,
        }
    )
    print(f"  [bg] {review_type} review for PR #{pr_number} in {event.repo}")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------


def create_app() -> "FastAPI":
    """Create the webhook handler FastAPI app."""
    if not HAS_FASTAPI:
        raise ImportError("FastAPI and uvicorn are required")

    app = FastAPI(title="Judge Webhook Handler", version="0.1.0")
    verifier = WebhookVerifier()
    router = EventRouter()
    override_parser = OverrideCommandParser()

    @app.post("/webhooks/github")
    async def handle_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        x_github_event: str = Header(default="ping"),
        x_hub_signature_256: str = Header(default=""),
        x_github_delivery: str = Header(default=""),
    ) -> dict:
        body = await request.body()

        # Verify signature
        if not verifier.verify(body, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = json.loads(body)
        event = WebhookEvent(
            event_type=x_github_event,
            action=payload.get("action", ""),
            delivery_id=x_github_delivery,
            repo=payload.get("repository", {}).get("full_name", ""),
            sender=payload.get("sender", {}).get("login", ""),
            payload=payload,
        )

        handler = router.route(event)

        if handler == "full_review":
            background_tasks.add_task(process_review, event, "full")
            return {"status": "accepted", "handler": "full_review"}

        elif handler == "incremental_review":
            background_tasks.add_task(process_review, event, "incremental")
            return {"status": "accepted", "handler": "incremental_review"}

        elif handler == "override_command":
            cmd = override_parser.parse(event)
            return {
                "status": "accepted",
                "handler": "override",
                "user": cmd.user if cmd else "unknown",
                "reason": cmd.reason if cmd else "",
            }

        return {"status": "ignored", "event": x_github_event}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "events_processed": len(_event_log)}

    return app


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not HAS_FASTAPI:
        print("Install fastapi + uvicorn: pip install fastapi uvicorn")
        print("\nShowing simulated webhook flow instead:\n")

        # Simulate without FastAPI
        router = EventRouter()
        parser = OverrideCommandParser()

        events = [
            WebhookEvent(
                event_type="pull_request",
                action="opened",
                delivery_id="d1",
                repo="org/repo",
                sender="dev",
                payload={"pull_request": {"number": 42}},
            ),
            WebhookEvent(
                event_type="pull_request",
                action="synchronize",
                delivery_id="d2",
                repo="org/repo",
                sender="dev",
                payload={"pull_request": {"number": 42}},
            ),
            WebhookEvent(
                event_type="issue_comment",
                action="created",
                delivery_id="d3",
                repo="org/repo",
                sender="lead",
                payload={
                    "comment": {
                        "body": "/judge-override False positive in test fixture",
                        "user": {"login": "lead"},
                    },
                    "issue": {"number": 42},
                },
            ),
        ]

        for ev in events:
            handler = router.route(ev)
            print(f"Event: {ev.event_type}.{ev.action} -> handler: {handler}")
            if handler == "override_command":
                cmd = parser.parse(ev)
                if cmd:
                    print(f"  Override: user={cmd.user}, reason={cmd.reason}")

        return

    app = create_app()
    print("Starting webhook handler on http://localhost:8090")
    uvicorn.run(app, host="0.0.0.0", port=8090)


if __name__ == "__main__":
    main()
