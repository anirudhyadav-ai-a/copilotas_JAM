"""
CI/CD Governance — Example 2: Merge Gate

Demonstrates:
  - Posting a GitHub status check (pass / fail / pending) from a verdict
  - Posting inline PR review comments mapped to exact file:line positions
  - Posting a top-level PR summary comment with verdict + must-fix list
  - Merge policy engine: configurable BLOCK/score-threshold rules
  - Override handler: authorized users can override BLOCK with written reason

Run:
    python -m copilotas_JAM.examples.ci_cd_governance.merge_gate.main

Prerequisites:
    GITHUB_TOKEN set in environment (or .env)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pr_reviewer"))
from main import FileFinding, FileVerdict, PRVerdict  # noqa: E402

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class MergePolicy:
    """Configurable merge policy rules."""

    block_on_must_fix: bool = True
    min_score: float = 6.0
    require_all_pass: bool = False
    authorized_overriders: list[str] = field(default_factory=list)


@dataclass
class MergeDecision:
    """Final merge decision."""

    allow_merge: bool
    reason: str
    overridden_by: str | None = None


@dataclass
class Override:
    """A merge override record."""

    user: str
    reason: str
    pr_number: int
    original_verdict: str


# ---------------------------------------------------------------------------
# Merge Policy Engine
# ---------------------------------------------------------------------------


class MergePolicyEngine:
    """Evaluate PR verdict against merge policy rules."""

    def __init__(self, policy: MergePolicy | None = None) -> None:
        self._policy = policy or MergePolicy()

    def evaluate(self, verdict: PRVerdict) -> MergeDecision:
        """Check verdict against policy. Return merge decision."""
        if self._policy.block_on_must_fix and verdict.must_fix:
            return MergeDecision(
                allow_merge=False,
                reason=f"Blocked: {len(verdict.must_fix)} must-fix findings",
            )

        if verdict.score < self._policy.min_score:
            return MergeDecision(
                allow_merge=False,
                reason=f"Score {verdict.score:.1f} below threshold {self._policy.min_score}",
            )

        if self._policy.require_all_pass:
            non_pass = [fv for fv in verdict.file_verdicts if fv.verdict != "PASS"]
            if non_pass:
                return MergeDecision(
                    allow_merge=False,
                    reason=f"{len(non_pass)} file(s) did not pass review",
                )

        return MergeDecision(allow_merge=True, reason="All policy checks passed")

    def apply_override(
        self,
        decision: MergeDecision,
        user: str,
        reason: str,
    ) -> MergeDecision:
        """Override a BLOCK decision if user is authorized."""
        if decision.allow_merge:
            return decision

        if user in self._policy.authorized_overriders:
            return MergeDecision(
                allow_merge=True,
                reason=f"Override by {user}: {reason}",
                overridden_by=user,
            )

        return MergeDecision(
            allow_merge=False,
            reason=f"{decision.reason} (override denied: {user} not authorized)",
        )


# ---------------------------------------------------------------------------
# GitHub Status Reporter (simulated)
# ---------------------------------------------------------------------------


class GitHubStatusReporter:
    """Post status checks and comments to GitHub PRs."""

    def __init__(self, token: str | None = None, repo: str = "") -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._repo = repo

    def post_status(
        self, sha: str, state: str, description: str, context: str = "judge/review"
    ) -> dict[str, str]:
        """Simulate posting a commit status."""
        payload = {
            "state": state,
            "description": description[:140],
            "context": context,
        }
        print(f"  POST /repos/{self._repo}/statuses/{sha[:7]}")
        print(f"    {json.dumps(payload)}")
        return payload

    def post_summary_comment(self, pr_number: int, verdict: PRVerdict) -> str:
        """Generate and simulate posting a summary comment."""
        emoji = {"PASS": "✅", "WARN": "⚠️", "BLOCK": "🚫"}.get(verdict.verdict, "❓")
        lines = [
            f"## {emoji} Judge Review: {verdict.verdict}",
            f"**Score:** {verdict.score:.1f}/10.0",
            "",
        ]

        if verdict.must_fix:
            lines.append("### Must-Fix Findings")
            for f in verdict.must_fix:
                lines.append(
                    f"- **{f.severity}** `{f.file_path}:{f.line}` — {f.description}"
                )
            lines.append("")

        if verdict.file_verdicts:
            lines.append("### File Verdicts")
            lines.append("| File | Verdict | Score |")
            lines.append("|------|---------|-------|")
            for fv in verdict.file_verdicts:
                lines.append(f"| `{fv.file_path}` | {fv.verdict} | {fv.score:.1f} |")

        comment = "\n".join(lines)
        print(f"  POST /repos/{self._repo}/issues/{pr_number}/comments")
        print(f"    ({len(comment)} chars)")
        return comment

    def post_inline_comments(self, pr_number: int, findings: list[FileFinding]) -> int:
        """Simulate posting inline review comments."""
        count = 0
        for f in findings:
            if f.line is not None:
                print(
                    f"  POST inline: {f.file_path}:{f.line} [{f.severity}] {f.description}"
                )
                count += 1
        return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=== Merge Gate Demo ===\n")

    # Simulate a PR verdict
    findings = [
        FileFinding(
            file_path="auth.py",
            line=42,
            severity="must-fix",
            category="security",
            description="Hardcoded API key",
        ),
        FileFinding(
            file_path="handler.py",
            line=10,
            severity="warning",
            category="correctness",
            description="Bare except clause",
        ),
    ]

    file_verdicts = [
        FileVerdict(
            file_path="auth.py", verdict="BLOCK", score=3.0, findings=[findings[0]]
        ),
        FileVerdict(
            file_path="handler.py", verdict="WARN", score=7.0, findings=[findings[1]]
        ),
    ]

    verdict = PRVerdict(
        verdict="BLOCK",
        score=5.0,
        file_verdicts=file_verdicts,
        must_fix=[findings[0]],
        summary="1 must-fix finding blocks merge",
    )

    # Evaluate against policy
    policy = MergePolicy(
        block_on_must_fix=True,
        min_score=6.0,
        authorized_overriders=["lead-dev", "tech-lead"],
    )
    engine = MergePolicyEngine(policy)
    decision = engine.evaluate(verdict)
    print(f"Merge decision: allow={decision.allow_merge}, reason={decision.reason}")

    # Try override
    override_decision = engine.apply_override(
        decision, user="lead-dev", reason="False positive — key is from test fixtures"
    )
    print(
        f"After override: allow={override_decision.allow_merge}, reason={override_decision.reason}"
    )

    # Simulate GitHub posting
    print("\n--- GitHub Status Updates ---")
    reporter = GitHubStatusReporter(repo="anirudhyadav/whitepaper")
    reporter.post_status(
        sha="abc1234def5678",
        state="failure" if not decision.allow_merge else "success",
        description=decision.reason,
    )
    reporter.post_summary_comment(pr_number=42, verdict=verdict)
    reporter.post_inline_comments(pr_number=42, findings=findings)


if __name__ == "__main__":
    main()
