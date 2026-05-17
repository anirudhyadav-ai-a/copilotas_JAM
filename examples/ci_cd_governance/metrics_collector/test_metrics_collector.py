"""Tests for the metrics collector.

Phase 0 | CI/CD Governance — Metrics Collector
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "metrics_collector_main", Path(__file__).parent / "main.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

MetricsStore = _mod.MetricsStore
MetricsCollector = _mod.MetricsCollector
ReviewRecord = _mod.ReviewRecord
OverrideRecord = _mod.OverrideRecord
MetricsReport = _mod.MetricsReport


class TestMetricsStore:
    def test_record_review(self):
        store = MetricsStore()
        now = datetime.now(timezone.utc).isoformat()
        store.record_review(
            ReviewRecord(
                pr_number=1,
                repo="org/repo",
                verdict="PASS",
                score=9.0,
                reviewed_at=now,
            )
        )
        row = store._conn.execute("SELECT COUNT(*) FROM reviews").fetchone()
        assert row[0] == 1

    def test_record_block_creates_time_to_fix(self):
        store = MetricsStore()
        now = datetime.now(timezone.utc).isoformat()
        store.record_review(
            ReviewRecord(
                pr_number=1,
                repo="org/repo",
                verdict="BLOCK",
                score=2.0,
                reviewed_at=now,
            )
        )
        row = store._conn.execute("SELECT COUNT(*) FROM time_to_fix").fetchone()
        assert row[0] == 1

    def test_record_override(self):
        store = MetricsStore()
        now = datetime.now(timezone.utc).isoformat()
        store.record_override(
            OverrideRecord(
                pr_number=1,
                user="lead",
                reason="FP",
                original_verdict="BLOCK",
                overridden_at=now,
            )
        )
        row = store._conn.execute("SELECT COUNT(*) FROM overrides").fetchone()
        assert row[0] == 1

    def test_record_approval_computes_duration(self):
        store = MetricsStore()
        blocked_at = datetime.now(timezone.utc).isoformat()
        store.record_review(
            ReviewRecord(
                pr_number=1,
                repo="org/repo",
                verdict="BLOCK",
                score=2.0,
                reviewed_at=blocked_at,
            )
        )
        approved_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        store.record_approval(1, approved_at)
        row = store._conn.execute(
            "SELECT fix_duration_hours FROM time_to_fix WHERE pr_number = 1"
        ).fetchone()
        assert row is not None
        assert row[0] > 0


class TestMetricsCollector:
    def test_empty_report(self):
        store = MetricsStore()
        now = datetime.now(timezone.utc).isoformat()
        store.record_review(
            ReviewRecord(
                pr_number=1,
                repo="org/repo",
                verdict="PASS",
                score=8.0,
                reviewed_at=now,
            )
        )
        collector = MetricsCollector(store)
        report = collector.report(period_days=30)
        assert isinstance(report, MetricsReport)
        assert report.total_reviews >= 1
        assert report.block_rate == 0.0

    def test_report_with_blocks_and_overrides(self):
        store = MetricsStore()
        now = datetime.now(timezone.utc)
        for i in range(10):
            ts = (now - timedelta(days=i)).isoformat()
            verdict = "BLOCK" if i < 3 else "PASS"
            store.record_review(
                ReviewRecord(
                    pr_number=100 + i,
                    repo="org/repo",
                    verdict=verdict,
                    score=5.0 if verdict == "BLOCK" else 9.0,
                    reviewed_at=ts,
                )
            )
        store.record_override(
            OverrideRecord(
                pr_number=100,
                user="lead",
                reason="FP",
                original_verdict="BLOCK",
                overridden_at=now.isoformat(),
                rule_id="RULE-001",
            )
        )

        collector = MetricsCollector(store)
        report = collector.report(period_days=30)
        assert report.block_rate > 0
        assert report.override_rate > 0
        assert report.avg_score > 0
