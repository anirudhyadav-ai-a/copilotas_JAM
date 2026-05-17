"""
Code DOM — Example 4: Refactor Planner & Mermaid Export

Demonstrates:
  - Change advisor: "you changed X -> update Y (caller) + add test for Z"
  - Refactor planner: rename a function -> find all callers + test files to update
  - Mermaid diagram export: dependency graph, class diagram
  - Complexity heatmap: per-module complexity scores
  - Repo stats report: functions, avg complexity, test coverage %, coupling

Run:
    python -m copilotas_JAM.examples.code_dom.refactor_planner.main [SYMBOL]

Prerequisites:
    A populated code_dom.sqlite (run python_parser first)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python_parser"))
from main import SQLiteStore  # noqa: E402

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ChangeAction:
    """A follow-up action needed after a code change."""

    file_path: str
    symbol: str
    action: str  # "update_caller", "update_test", "update_import"
    reason: str


@dataclass
class RefactorPlan:
    """Plan for renaming a symbol across the codebase."""

    old_name: str
    new_name: str
    actions: list[ChangeAction] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len({a.file_path for a in self.actions})


@dataclass
class ComplexityScore:
    """Complexity metrics for a single function."""

    symbol: str
    file_path: str
    lines_of_code: int = 0
    call_count: int = 0  # number of outgoing calls
    caller_count: int = 0  # number of incoming calls
    coupling_score: float = 0.0


@dataclass
class RepoStats:
    """Aggregate repository statistics."""

    total_files: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_edges: int = 0
    avg_coupling: float = 0.0
    hotspots: list[ComplexityScore] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Change Advisor
# ---------------------------------------------------------------------------


class ChangeAdvisor:
    """Given changed nodes, generate follow-up action list."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def advise(self, changed_symbol: str) -> list[ChangeAction]:
        """Find all callers and tests that need updating."""
        conn = self._store._conn
        actions: list[ChangeAction] = []

        # Find callers
        cursor = conn.execute(
            "SELECT e.source_id, n.file_path FROM edges e "
            "JOIN nodes n ON e.source_id = n.node_id "
            "WHERE e.target_id = ? AND e.kind = 'CALLS'",
            (changed_symbol,),
        )
        for source_id, file_path in cursor.fetchall():
            actions.append(
                ChangeAction(
                    file_path=file_path or "",
                    symbol=source_id,
                    action="update_caller",
                    reason=f"Calls {changed_symbol} — verify compatibility",
                )
            )

        # Find test files
        cursor2 = conn.execute(
            "SELECT DISTINCT n.file_path, n.node_id FROM nodes n "
            "WHERE (n.file_path LIKE '%test_%' OR n.node_id LIKE '%test_%') "
            "AND n.kind = 'FUNCTION'"
        )
        base_name = changed_symbol.split(".")[-1]
        for file_path, node_id in cursor2.fetchall():
            if (
                base_name.lower() in (file_path or "").lower()
                or base_name.lower() in node_id.lower()
            ):
                actions.append(
                    ChangeAction(
                        file_path=file_path or "",
                        symbol=node_id,
                        action="update_test",
                        reason=f"Test likely covers {changed_symbol}",
                    )
                )

        return actions


# ---------------------------------------------------------------------------
# Refactor Planner
# ---------------------------------------------------------------------------


class RefactorPlanner:
    """Plan a rename refactor across the codebase."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._advisor = ChangeAdvisor(store)

    def rename(self, old_name: str, new_name: str) -> RefactorPlan:
        """Generate a plan for renaming a symbol."""
        plan = RefactorPlan(old_name=old_name, new_name=new_name)
        plan.actions = self._advisor.advise(old_name)

        # Add import update actions
        conn = self._store._conn
        cursor = conn.execute(
            "SELECT source_id, n.file_path FROM edges e "
            "JOIN nodes n ON e.source_id = n.node_id "
            "WHERE e.target_id = ? AND e.kind = 'IMPORTS'",
            (old_name,),
        )
        for source_id, file_path in cursor.fetchall():
            plan.actions.append(
                ChangeAction(
                    file_path=file_path or "",
                    symbol=source_id,
                    action="update_import",
                    reason=f"Imports {old_name} — update to {new_name}",
                )
            )

        return plan


# ---------------------------------------------------------------------------
# Mermaid Exporter
# ---------------------------------------------------------------------------


class MermaidExporter:
    """Export dependency graph as Mermaid diagrams."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def dependency_flowchart(self, module: str | None = None) -> str:
        """Generate a Mermaid flowchart of call dependencies."""
        conn = self._store._conn
        query = "SELECT source_id, target_id, kind FROM edges WHERE kind = 'CALLS'"
        params: tuple[str, ...] = ()
        if module:
            query += " AND (source_id LIKE ? OR target_id LIKE ?)"
            params = (f"%{module}%", f"%{module}%")

        cursor = conn.execute(query, params)
        edges = cursor.fetchall()

        lines = ["graph LR"]
        seen: set[str] = set()
        for source, target, _ in edges[:50]:  # limit for readability
            key = f"{source}-->{target}"
            if key not in seen:
                safe_src = source.replace(".", "_").replace("/", "_")
                safe_tgt = target.replace(".", "_").replace("/", "_")
                lines.append(f"    {safe_src}[{source}] --> {safe_tgt}[{target}]")
                seen.add(key)

        return "\n".join(lines)

    def class_diagram(self) -> str:
        """Generate a Mermaid class diagram from CLASS + INHERITS edges."""
        conn = self._store._conn
        classes = conn.execute(
            "SELECT node_id, name FROM nodes WHERE kind = 'CLASS'"
        ).fetchall()
        inherits = conn.execute(
            "SELECT source_id, target_id FROM edges WHERE kind = 'INHERITS'"
        ).fetchall()

        lines = ["classDiagram"]
        for _, name in classes:
            lines.append(f"    class {name}")
        for child, parent in inherits:
            child_name = child.split(".")[-1]
            parent_name = parent.split(".")[-1]
            lines.append(f"    {parent_name} <|-- {child_name}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Complexity Scorer
# ---------------------------------------------------------------------------


class ComplexityScorer:
    """Score functions by coupling (call count + caller count)."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def score_all(self) -> list[ComplexityScore]:
        """Score all functions by complexity/coupling."""
        conn = self._store._conn
        functions = conn.execute(
            "SELECT node_id, file_path FROM nodes WHERE kind = 'FUNCTION'"
        ).fetchall()

        scores: list[ComplexityScore] = []
        for node_id, file_path in functions:
            outgoing = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE source_id = ? AND kind = 'CALLS'",
                (node_id,),
            ).fetchone()[0]
            incoming = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE target_id = ? AND kind = 'CALLS'",
                (node_id,),
            ).fetchone()[0]

            coupling = (outgoing + incoming) / max(outgoing + incoming, 1)
            scores.append(
                ComplexityScore(
                    symbol=node_id,
                    file_path=file_path or "",
                    call_count=outgoing,
                    caller_count=incoming,
                    coupling_score=coupling,
                )
            )

        return sorted(scores, key=lambda s: s.call_count + s.caller_count, reverse=True)

    def hotspots(self, top_n: int = 10) -> list[ComplexityScore]:
        """Return top N most coupled functions."""
        return self.score_all()[:top_n]


# ---------------------------------------------------------------------------
# Repo Stats
# ---------------------------------------------------------------------------


class RepoStatsCollector:
    """Collect aggregate repository statistics."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def collect(self) -> RepoStats:
        conn = self._store._conn
        stats = RepoStats()
        stats.total_files = conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE kind = 'FILE'"
        ).fetchone()[0]
        stats.total_functions = conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE kind = 'FUNCTION'"
        ).fetchone()[0]
        stats.total_classes = conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE kind = 'CLASS'"
        ).fetchone()[0]
        stats.total_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        scorer = ComplexityScorer(self._store)
        stats.hotspots = scorer.hotspots(5)
        all_scores = scorer.score_all()
        if all_scores:
            stats.avg_coupling = sum(s.coupling_score for s in all_scores) / len(
                all_scores
            )

        return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "shared.llm_client.call_llm"
    db_path = "code_dom.sqlite"

    if not Path(db_path).exists():
        print(f"Database {db_path} not found. Run python_parser first.")
        return

    store = SQLiteStore(db_path)

    # Change advisor
    advisor = ChangeAdvisor(store)
    actions = advisor.advise(target)
    print(f"=== Change Advisor: {target} ===")
    for a in actions:
        print(f"  [{a.action}] {a.symbol} — {a.reason}")

    # Refactor plan
    new_name = target.replace(target.split(".")[-1], "invoke_" + target.split(".")[-1])
    planner = RefactorPlanner(store)
    plan = planner.rename(target, new_name)
    print(f"\n=== Refactor Plan: {target} → {new_name} ===")
    print(f"Files affected: {plan.file_count}")
    for a in plan.actions:
        print(f"  [{a.action}] {a.file_path} :: {a.symbol}")

    # Mermaid
    exporter = MermaidExporter(store)
    print("\n=== Mermaid Dependency Graph ===")
    print(exporter.dependency_flowchart())

    # Repo stats
    collector = RepoStatsCollector(store)
    stats = collector.collect()
    print("\n=== Repo Stats ===")
    print(
        json.dumps(
            {
                "files": stats.total_files,
                "functions": stats.total_functions,
                "classes": stats.total_classes,
                "edges": stats.total_edges,
                "avg_coupling": round(stats.avg_coupling, 3),
                "hotspots": [s.symbol for s in stats.hotspots],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
