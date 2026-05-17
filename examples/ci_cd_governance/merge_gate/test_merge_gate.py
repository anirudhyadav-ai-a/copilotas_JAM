"""Tests for the merge gate.

Phase 0 | CI/CD Governance — Merge Gate
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load pr_reviewer/main.py as "main" so that merge_gate's
# ``from main import ...`` resolves correctly.
_pr_path = Path(__file__).resolve().parent.parent / "pr_reviewer" / "main.py"
_pr_spec = importlib.util.spec_from_file_location("main", _pr_path)
_pr_mod = importlib.util.module_from_spec(_pr_spec)
_saved_main = sys.modules.get("main")
sys.modules["main"] = _pr_mod
_pr_spec.loader.exec_module(_pr_mod)

_spec = importlib.util.spec_from_file_location(
    "merge_gate_main", Path(__file__).parent / "main.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

if _saved_main is not None:
    sys.modules["main"] = _saved_main
else:
    sys.modules.pop("main", None)

PRVerdict = _pr_mod.PRVerdict
FileFinding = _pr_mod.FileFinding
MergePolicyEngine = _mod.MergePolicyEngine
MergePolicy = _mod.MergePolicy
MergeDecision = _mod.MergeDecision
GitHubStatusReporter = _mod.GitHubStatusReporter


class TestMergePolicyEngine:
    def test_allow_merge_passing_verdict(self):
        engine = MergePolicyEngine()
        verdict = PRVerdict(verdict="PASS", score=9.0, summary="Clean")
        decision = engine.evaluate(verdict)
        assert decision.allow_merge is True

    def test_block_on_must_fix(self):
        finding = FileFinding(
            file_path="a.py",
            line=1,
            severity="must-fix",
            category="security",
            description="Hardcoded secret",
        )
        verdict = PRVerdict(
            verdict="BLOCK",
            score=2.0,
            summary="Issues found",
            must_fix=[finding],
        )
        engine = MergePolicyEngine()
        decision = engine.evaluate(verdict)
        assert decision.allow_merge is False

    def test_block_on_low_score(self):
        policy = MergePolicy(min_score=7.0, block_on_must_fix=False)
        engine = MergePolicyEngine(policy)
        verdict = PRVerdict(verdict="WARN", score=5.0, summary="Low score")
        decision = engine.evaluate(verdict)
        assert decision.allow_merge is False
        assert "below threshold" in decision.reason

    def test_override_authorized_user(self):
        policy = MergePolicy(authorized_overriders=["lead-dev"])
        engine = MergePolicyEngine(policy)
        blocked = MergeDecision(allow_merge=False, reason="Blocked by policy")
        overridden = engine.apply_override(blocked, "lead-dev", "False positive")
        assert overridden.allow_merge is True
        assert overridden.overridden_by == "lead-dev"

    def test_override_unauthorized_user(self):
        policy = MergePolicy(authorized_overriders=["lead-dev"])
        engine = MergePolicyEngine(policy)
        blocked = MergeDecision(allow_merge=False, reason="Blocked by policy")
        result = engine.apply_override(blocked, "junior-dev", "Trust me")
        assert result.allow_merge is False
        assert "not authorized" in result.reason

    def test_override_already_passing(self):
        engine = MergePolicyEngine()
        passing = MergeDecision(allow_merge=True, reason="All good")
        result = engine.apply_override(passing, "anyone", "Reason")
        assert result.allow_merge is True


class TestGitHubStatusReporter:
    def test_post_status(self):
        reporter = GitHubStatusReporter(token="test", repo="org/repo")
        payload = reporter.post_status("abc1234", "success", "All checks passed")
        assert payload["state"] == "success"
        assert payload["context"] == "judge/review"

    def test_post_summary_comment(self):
        reporter = GitHubStatusReporter(token="test", repo="org/repo")
        verdict = PRVerdict(verdict="PASS", score=9.5, summary="Clean")
        comment = reporter.post_summary_comment(42, verdict)
        assert "PASS" in comment
