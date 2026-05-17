"""
CI/CD Governance — Example 4: Metrics Collector

Demonstrates:
  - Storing review results in SQLite (reviews, overrides, time_to_fix tables)
  - Computing rolling metrics: reviews/day, block rate, override rate
  - False positive tracker: human override -> increment false_positive counter per rule
  - Time-to-fix: BLOCK timestamp -> APPROVE timestamp -> fix duration
  - Generating a metrics summary report

Run:
    python -m copilotas_JAM.examples.ci_cd_governance.metrics_collector.main
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ReviewRecord:
    """A single PR review record."""

    pr_number: int
    repo: str
    verdict: str  # PASS, WARN, BLOCK
    score: float
    reviewed_at: str
    reviewer: str = "judge"


@dataclass
class OverrideRecord:
    """A merge override record."""

    pr_number: int
    user: str
    reason: str
    original_verdict: str
    overridden_at: str
    rule_id: str = ""


@dataclass
class MetricsReport:
    """Rolling metrics summary."""

    period_days: int
    total_reviews: int
    verdict_distribution: dict[str, int]
    block_rate: float
    override_rate: float
    false_positive_rate: float
    avg_score: float
    median_time_to_fix_hours: float
    top_false_positive_rules: list[tuple[str, int]]


# ---------------------------------------------------------------------------
# Metrics Store
# ---------------------------------------------------------------------------


class MetricsStore:
    """SQLite-backed metrics storage."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_number INTEGER NOT NULL,
                repo TEXT NOT NULL,
                verdict TEXT NOT NULL,
                score REAL NOT NULL,
                reviewed_at TEXT NOT NULL,
                reviewer TEXT DEFAULT 'judge'
            );

            CREATE TABLE IF NOT EXISTS overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_number INTEGER NOT NULL,
                user TEXT NOT NULL,
                reason TEXT NOT NULL,
                original_verdict TEXT NOT NULL,
                overridden_at TEXT NOT NULL,
                rule_id TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS time_to_fix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_number INTEGER NOT NULL,
                blocked_at TEXT NOT NULL,
                approved_at TEXT,
                fix_duration_hours REAL
            );
            """)

    def record_review(self, review: ReviewRecord) -> None:
        self._conn.execute(
            "INSERT INTO reviews (pr_number, repo, verdict, score, reviewed_at, reviewer) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                review.pr_number,
                review.repo,
                review.verdict,
                review.score,
                review.reviewed_at,
                review.reviewer,
            ),
        )
        if review.verdict == "BLOCK":
            self._conn.execute(
                "INSERT INTO time_to_fix (pr_number, blocked_at) VALUES (?, ?)",
                (review.pr_number, review.reviewed_at),
            )
        self._conn.commit()

    def record_override(self, override: OverrideRecord) -> None:
        self._conn.execute(
            "INSERT INTO overrides (pr_number, user, reason, original_verdict, overridden_at, rule_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                override.pr_number,
                override.user,
                override.reason,
                override.original_verdict,
                override.overridden_at,
                override.rule_id,
            ),
        )
        self._conn.commit()

    def record_approval(self, pr_number: int, approved_at: str) -> None:
        """Record when a blocked PR is eventually approved."""
        row = self._conn.execute(
            "SELECT id, blocked_at FROM time_to_fix "
            "WHERE pr_number = ? AND approved_at IS NULL ORDER BY id DESC LIMIT 1",
            (pr_number,),
        ).fetchone()
        if row:
            blocked = datetime.fromisoformat(row[1])
            approved = datetime.fromisoformat(approved_at)
            hours = (approved - blocked).total_seconds() / 3600
            self._conn.execute(
                "UPDATE time_to_fix SET approved_at = ?, fix_duration_hours = ? WHERE id = ?",
                (approved_at, hours, row[0]),
            )
            self._conn.commit()


# ---------------------------------------------------------------------------
# Metrics Collector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Compute rolling metrics from the store."""

    def __init__(self, store: MetricsStore) -> None:
        self._store = store

    def report(self, period_days: int = 30) -> MetricsReport:
        """Generate a rolling metrics report."""
        conn = self._store._conn
        cutoff = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()

        # Verdict distribution
        rows = conn.execute(
            "SELECT verdict, COUNT(*) FROM reviews WHERE reviewed_at >= ? GROUP BY verdict",
            (cutoff,),
        ).fetchall()
        distribution = dict(rows)
        total = sum(distribution.values()) or 1

        # Block rate
        blocks = distribution.get("BLOCK", 0)
        block_rate = blocks / total

        # Override rate
        overrides = conn.execute(
            "SELECT COUNT(*) FROM overrides WHERE overridden_at >= ?",
            (cutoff,),
        ).fetchone()[0]
        override_rate = overrides / total

        # False positive rate (overrides / blocks)
        fp_rate = overrides / blocks if blocks > 0 else 0.0

        # Average score
        avg_row = conn.execute(
            "SELECT AVG(score) FROM reviews WHERE reviewed_at >= ?",
            (cutoff,),
        ).fetchone()
        avg_score = avg_row[0] or 0.0

        # Median time to fix
        fix_times = conn.execute(
            "SELECT fix_duration_hours FROM time_to_fix "
            "WHERE approved_at IS NOT NULL AND blocked_at >= ? "
            "ORDER BY fix_duration_hours",
            (cutoff,),
        ).fetchall()
        if fix_times:
            mid = len(fix_times) // 2
            median_ttf = fix_times[mid][0]
        else:
            median_ttf = 0.0

        # Top false positive rules
        fp_rules = conn.execute(
            "SELECT rule_id, COUNT(*) as cnt FROM overrides "
            "WHERE overridden_at >= ? AND rule_id != '' "
            "GROUP BY rule_id ORDER BY cnt DESC LIMIT 5",
            (cutoff,),
        ).fetchall()

        return MetricsReport(
            period_days=period_days,
            total_reviews=total,
            verdict_distribution=distribution,
            block_rate=block_rate,
            override_rate=override_rate,
            false_positive_rate=fp_rate,
            avg_score=avg_score,
            median_time_to_fix_hours=median_ttf,
            top_false_positive_rules=fp_rules,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=== Metrics Collector Demo ===\n")

    store = MetricsStore()
    collector = MetricsCollector(store)

    # Seed sample data
    now = datetime.now(timezone.utc)
    for i in range(50):
        ts = (now - timedelta(days=i % 25, hours=i)).isoformat()
        verdict = ["PASS", "PASS", "PASS", "WARN", "WARN", "BLOCK"][i % 6]
        store.record_review(
            ReviewRecord(
                pr_number=100 + i,
                repo="org/repo",
                verdict=verdict,
                score=5.0 + (i % 6),
                reviewed_at=ts,
            )
        )
        if verdict == "BLOCK" and i % 3 == 0:
            store.record_override(
                OverrideRecord(
                    pr_number=100 + i,
                    user="lead-dev",
                    reason="False positive",
                    original_verdict="BLOCK",
                    overridden_at=ts,
                    rule_id=f"RULE-{(i % 4) + 1:03d}",
                )
            )
            store.record_approval(
                100 + i, (now - timedelta(days=i % 25, hours=i - 3)).isoformat()
            )

    # Generate report
    report = collector.report(period_days=30)

    print(
        json.dumps(
            {
                "period": f"last_{report.period_days}_days",
                "total_reviews": report.total_reviews,
                "verdict_distribution": report.verdict_distribution,
                "block_rate": f"{report.block_rate:.1%}",
                "override_rate": f"{report.override_rate:.1%}",
                "false_positive_rate": f"{report.false_positive_rate:.1%}",
                "avg_score": round(report.avg_score, 1),
                "median_time_to_fix_hours": round(report.median_time_to_fix_hours, 1),
                "top_false_positive_rules": report.top_false_positive_rules,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
