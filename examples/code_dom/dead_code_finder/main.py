"""
Code DOM — Example 3: Dead Code Finder

Demonstrates:
  - Graph reachability from defined entry points (main, API routes, exports)
  - Finding unreachable functions (no path from any entry point)
  - Finding unused imports (module imported but no symbol used)
  - Finding orphan classes (no instantiation, no inheritance)

Run:
    python -m copilotas_JAM.examples.code_dom.dead_code_finder.main [DIRECTORY]

Prerequisites:
    A populated code_dom.sqlite (run python_parser first)
"""

from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python_parser"))
from main import SQLiteStore  # noqa: E402

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DeadCodeReport:
    """Report of unreachable / unused code."""

    unreachable_functions: list[str] = field(default_factory=list)
    unused_imports: list[str] = field(default_factory=list)
    orphan_classes: list[str] = field(default_factory=list)
    total_nodes: int = 0
    reachable_nodes: int = 0

    @property
    def dead_code_percentage(self) -> float:
        if self.total_nodes == 0:
            return 0.0
        dead = len(self.unreachable_functions) + len(self.orphan_classes)
        return dead / self.total_nodes * 100


# ---------------------------------------------------------------------------
# Entry Point Resolver
# ---------------------------------------------------------------------------

ENTRY_PATTERNS = [
    "main",
    "__main__",
    "app",
    "create_app",
    "test_",
    "setup",
    "teardown",
]


class EntryPointResolver:
    """Find main functions, API routes, test functions as entry points."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def resolve(self) -> list[str]:
        """Return node_ids of all entry points."""
        conn = self._store._conn
        cursor = conn.execute("SELECT node_id, name FROM nodes WHERE kind = 'FUNCTION'")
        entries: list[str] = []
        for node_id, name in cursor.fetchall():
            if any(name.startswith(p) or name == p for p in ENTRY_PATTERNS):
                entries.append(node_id)

        # Also add module-level code (FILE nodes)
        cursor2 = conn.execute("SELECT node_id FROM nodes WHERE kind = 'FILE'")
        for (node_id,) in cursor2.fetchall():
            entries.append(node_id)

        return entries


# ---------------------------------------------------------------------------
# Reachability Analyzer
# ---------------------------------------------------------------------------


class ReachabilityAnalyzer:
    """BFS from entry points to mark all reachable nodes."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def find_reachable(self, entry_points: list[str]) -> set[str]:
        """BFS from entry points through all edge types."""
        graph = self._build_forward_graph()
        visited: set[str] = set()
        queue: deque[str] = deque(entry_points)

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        return visited

    def _build_forward_graph(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {}
        conn = self._store._conn
        cursor = conn.execute("SELECT source_id, target_id FROM edges")
        for source, target in cursor.fetchall():
            graph.setdefault(source, []).append(target)
        return graph


# ---------------------------------------------------------------------------
# Dead Code Finder
# ---------------------------------------------------------------------------


class DeadCodeFinder:
    """Combine entry point resolution + reachability to find dead code."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._resolver = EntryPointResolver(store)
        self._reachability = ReachabilityAnalyzer(store)

    def find(self) -> DeadCodeReport:
        """Find all unreachable functions, unused imports, orphan classes."""
        entry_points = self._resolver.resolve()
        reachable = self._reachability.find_reachable(entry_points)

        conn = self._store._conn
        report = DeadCodeReport()

        # All nodes
        all_nodes = conn.execute("SELECT node_id, kind FROM nodes").fetchall()
        report.total_nodes = len(all_nodes)
        report.reachable_nodes = len(reachable)

        for node_id, kind in all_nodes:
            if node_id in reachable:
                continue
            if kind == "FUNCTION":
                report.unreachable_functions.append(node_id)
            elif kind == "CLASS":
                report.orphan_classes.append(node_id)
            elif kind == "IMPORT":
                report.unused_imports.append(node_id)

        return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    db_path = "code_dom.sqlite"

    if not Path(db_path).exists():
        print(f"Database {db_path} not found. Run python_parser first.")
        print(
            "  python -m copilotas_JAM.examples.code_dom.python_parser.main <directory>"
        )
        return

    store = SQLiteStore(db_path)
    finder = DeadCodeFinder(store)
    report = finder.find()

    print("=== Dead Code Report ===")
    print(f"Total nodes: {report.total_nodes}")
    print(f"Reachable nodes: {report.reachable_nodes}")
    print(f"Dead code: {report.dead_code_percentage:.1f}%")

    if report.unreachable_functions:
        print(f"\nUnreachable functions ({len(report.unreachable_functions)}):")
        for f in report.unreachable_functions[:20]:
            print(f"  ✗ {f}")

    if report.unused_imports:
        print(f"\nUnused imports ({len(report.unused_imports)}):")
        for i in report.unused_imports[:20]:
            print(f"  ✗ {i}")

    if report.orphan_classes:
        print(f"\nOrphan classes ({len(report.orphan_classes)}):")
        for c in report.orphan_classes[:20]:
            print(f"  ✗ {c}")

    if not any(
        [report.unreachable_functions, report.unused_imports, report.orphan_classes]
    ):
        print("\nNo dead code found!")


if __name__ == "__main__":
    main()
