"""
Code Graph — Example 2: Impact Analyzer

Demonstrates:
  - Traversing CALLS edges in reverse to find all callers of a function
  - Computing blast radius score (0=isolated, 1=central to everything)
  - Circular dependency detection (DFS with in-stack tracking)
  - Test coverage mapping (which tests cover a given function)

Run:
    python -m copilotas_JAM.examples.code_graph.impact_analyzer.main [TARGET_SYMBOL]

Prerequisites:
    A populated code_graph.sqlite (run python_parser first)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Re-use the SQLiteStore from python_parser
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python_parser"))
from main import SQLiteStore  # noqa: E402

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ImpactResult:
    """Result of an impact analysis for a single symbol."""

    target: str
    direct_callers: list[str] = field(default_factory=list)
    transitive_callers: list[str] = field(default_factory=list)
    blast_radius_score: float = 0.0
    depth: int = 0


@dataclass
class CircularDep:
    """A circular dependency cycle."""

    cycle: list[str] = field(default_factory=list)


@dataclass
class TestMapping:
    """Maps a function to test files that cover it."""

    symbol: str
    test_files: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Impact Analyzer
# ---------------------------------------------------------------------------


class ImpactAnalyzer:
    """Traverse CALLS edges in reverse to find all callers of a symbol."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def analyze(self, target: str, max_depth: int = 5) -> ImpactResult:
        """BFS from target through reverse CALLS edges."""
        result = ImpactResult(target=target)
        visited: set[str] = set()
        frontier: list[tuple[str, int]] = [(target, 0)]

        callers = self._build_reverse_call_graph()

        while frontier:
            symbol, depth = frontier.pop(0)
            if symbol in visited or depth > max_depth:
                continue
            visited.add(symbol)

            for caller in callers.get(symbol, []):
                if caller not in visited:
                    if depth == 0:
                        result.direct_callers.append(caller)
                    result.transitive_callers.append(caller)
                    frontier.append((caller, depth + 1))
                    result.depth = max(result.depth, depth + 1)

        total_nodes = self._count_nodes()
        if total_nodes > 1:
            result.blast_radius_score = len(visited) / total_nodes
        return result

    def _build_reverse_call_graph(self) -> dict[str, list[str]]:
        """Build callee → [callers] mapping from edges."""
        reverse: dict[str, list[str]] = {}
        conn = self._store._conn
        cursor = conn.execute(
            "SELECT source_id, target_id FROM edges WHERE kind = 'CALLS'"
        )
        for source, target in cursor.fetchall():
            reverse.setdefault(target, []).append(source)
        return reverse

    def _count_nodes(self) -> int:
        conn = self._store._conn
        cursor = conn.execute("SELECT COUNT(*) FROM nodes")
        return cursor.fetchone()[0]


# ---------------------------------------------------------------------------
# Circular Dependency Detector
# ---------------------------------------------------------------------------


class CircularDependencyDetector:
    """Detect circular dependencies using DFS with in-stack tracking."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def detect(self) -> list[CircularDep]:
        """Find all cycles in the CALLS graph."""
        graph = self._build_call_graph()
        visited: set[str] = set()
        in_stack: set[str] = set()
        cycles: list[CircularDep] = []
        path: list[str] = []

        for node in graph:
            if node not in visited:
                self._dfs(node, graph, visited, in_stack, path, cycles)
        return cycles

    def _dfs(
        self,
        node: str,
        graph: dict[str, list[str]],
        visited: set[str],
        in_stack: set[str],
        path: list[str],
        cycles: list[CircularDep],
    ) -> None:
        visited.add(node)
        in_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                self._dfs(neighbor, graph, visited, in_stack, path, cycles)
            elif neighbor in in_stack:
                idx = path.index(neighbor)
                cycles.append(CircularDep(cycle=path[idx:] + [neighbor]))

        path.pop()
        in_stack.discard(node)

    def _build_call_graph(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {}
        conn = self._store._conn
        cursor = conn.execute(
            "SELECT source_id, target_id FROM edges WHERE kind = 'CALLS'"
        )
        for source, target in cursor.fetchall():
            graph.setdefault(source, []).append(target)
        return graph


# ---------------------------------------------------------------------------
# Test Coverage Mapper
# ---------------------------------------------------------------------------


class TestCoverageMapper:
    """Map functions to test files based on naming and import conventions."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def map_tests(self, symbol: str) -> TestMapping:
        """Find test files that likely cover the given symbol."""
        conn = self._store._conn
        cursor = conn.execute(
            "SELECT DISTINCT file_path FROM nodes WHERE kind = 'FUNCTION' "
            "AND (node_id LIKE '%test_%' OR file_path LIKE '%test_%')"
        )
        test_files: list[str] = []
        base_name = symbol.split(".")[-1]

        for (file_path,) in cursor.fetchall():
            # Check if the test file imports or references the symbol
            cursor2 = conn.execute(
                "SELECT 1 FROM edges WHERE source_id LIKE ? AND target_id LIKE ?",
                (f"%{file_path}%", f"%{base_name}%"),
            )
            if cursor2.fetchone():
                test_files.append(file_path)

            # Also match by naming convention (test_<module>)
            if base_name.lower() in file_path.lower():
                if file_path not in test_files:
                    test_files.append(file_path)

        return TestMapping(symbol=symbol, test_files=test_files)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "shared.llm_client.call_llm"
    db_path = "code_graph.sqlite"

    if not Path(db_path).exists():
        print(f"Database {db_path} not found. Run python_parser first.")
        print(
            "  python -m copilotas_JAM.examples.code_graph.python_parser.main <directory>"
        )
        return

    store = SQLiteStore(db_path)

    # Impact analysis
    analyzer = ImpactAnalyzer(store)
    result = analyzer.analyze(target, max_depth=5)
    print(f"\n=== Impact Analysis: {target} ===")
    print(f"Direct callers: {len(result.direct_callers)}")
    for c in result.direct_callers:
        print(f"  → {c}")
    print(f"Transitive callers: {len(result.transitive_callers)}")
    print(f"Blast radius score: {result.blast_radius_score:.2f}")
    print(f"Max depth: {result.depth}")

    # Circular dependencies
    detector = CircularDependencyDetector(store)
    cycles = detector.detect()
    print("\n=== Circular Dependencies ===")
    if cycles:
        for cd in cycles:
            print(f"  Cycle: {' → '.join(cd.cycle)}")
    else:
        print("  No circular dependencies found.")

    # Test coverage
    mapper = TestCoverageMapper(store)
    mapping = mapper.map_tests(target)
    print(f"\n=== Test Coverage: {target} ===")
    if mapping.test_files:
        for tf in mapping.test_files:
            print(f"  📝 {tf}")
    else:
        print("  No test files found covering this symbol.")


if __name__ == "__main__":
    main()
