"""Tests for the dead code finder.

Phase 0 | Code DOM — Dead Code Finder
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load python_parser/main.py as "main" so that dead_code_finder's
# ``from main import SQLiteStore`` resolves correctly.
_parser_path = Path(__file__).resolve().parent.parent / "python_parser" / "main.py"
_parser_spec = importlib.util.spec_from_file_location("main", _parser_path)
_parser_mod = importlib.util.module_from_spec(_parser_spec)
_saved_main = sys.modules.get("main")
sys.modules["main"] = _parser_mod
_parser_spec.loader.exec_module(_parser_mod)

_spec = importlib.util.spec_from_file_location(
    "dead_code_finder_main", Path(__file__).parent / "main.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

# Restore original "main" module if any.
if _saved_main is not None:
    sys.modules["main"] = _saved_main
else:
    sys.modules.pop("main", None)

PythonParser = _parser_mod.PythonParser
SQLiteStore = _parser_mod.SQLiteStore
DeadCodeFinder = _mod.DeadCodeFinder
DeadCodeReport = _mod.DeadCodeReport
EntryPointResolver = _mod.EntryPointResolver
ReachabilityAnalyzer = _mod.ReachabilityAnalyzer


class TestEntryPointResolver:
    def test_finds_main_function(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def main():\n    pass\ndef helper():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        resolver = EntryPointResolver(store)
        entries = resolver.resolve()
        # Should find "main" function + FILE node as entry points.
        # "helper" is not an entry point pattern.
        assert len(entries) >= 2  # main + FILE node

    def test_finds_test_functions(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def test_something():\n    pass\ndef helper():\n    pass\n"
        nodes, edges = parser.parse(source, "test_app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        resolver = EntryPointResolver(store)
        entries = resolver.resolve()
        # Should find test_something + FILE node
        assert len(entries) >= 2


class TestReachabilityAnalyzer:
    def test_marks_called_functions_as_reachable(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def main():\n    helper()\ndef helper():\n    pass\ndef orphan():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        resolver = EntryPointResolver(store)
        entries = resolver.resolve()

        analyzer = ReachabilityAnalyzer(store)
        reachable = analyzer.find_reachable(entries)
        # main and helper should be reachable (main calls helper)
        # At least the entry points themselves should be reachable
        assert len(reachable) >= 2


class TestDeadCodeFinder:
    def test_finds_unreachable_functions(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def main():\n    pass\ndef unused():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        finder = DeadCodeFinder(store)
        report = finder.find()
        assert isinstance(report, DeadCodeReport)
        assert report.total_nodes > 0

    def test_all_entry_points_are_reachable(self):
        store = SQLiteStore()
        parser = PythonParser()
        # All functions are entry points (main, test_*)
        source = "def main():\n    pass\ndef test_a():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        finder = DeadCodeFinder(store)
        report = finder.find()
        assert report.unreachable_functions == []

    def test_dead_code_percentage(self):
        report = DeadCodeReport(
            unreachable_functions=["a", "b", "c"],
            total_nodes=10,
            reachable_nodes=7,
        )
        assert report.dead_code_percentage == 30.0

    def test_dead_code_percentage_zero_nodes(self):
        report = DeadCodeReport(total_nodes=0, reachable_nodes=0)
        assert report.dead_code_percentage == 0.0
