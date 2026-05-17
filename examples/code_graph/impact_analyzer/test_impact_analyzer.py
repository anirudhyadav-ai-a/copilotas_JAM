"""Tests for the impact analyzer.

Phase 0 | Code Graph — Impact Analyzer
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load python_parser/main.py as "main" so that impact_analyzer's
# ``from main import SQLiteStore`` resolves correctly.
_parser_path = Path(__file__).resolve().parent.parent / "python_parser" / "main.py"
_parser_spec = importlib.util.spec_from_file_location("main", _parser_path)
_parser_mod = importlib.util.module_from_spec(_parser_spec)
_saved_main = sys.modules.get("main")
sys.modules["main"] = _parser_mod
_parser_spec.loader.exec_module(_parser_mod)

_spec = importlib.util.spec_from_file_location(
    "impact_analyzer_main", Path(__file__).parent / "main.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

if _saved_main is not None:
    sys.modules["main"] = _saved_main
else:
    sys.modules.pop("main", None)

PythonParser = _parser_mod.PythonParser
SQLiteStore = _parser_mod.SQLiteStore
ImpactAnalyzer = _mod.ImpactAnalyzer
CircularDependencyDetector = _mod.CircularDependencyDetector
TestCoverageMapper = _mod.TestCoverageMapper


class TestImpactAnalyzer:
    def _build_store(self) -> SQLiteStore:
        store = SQLiteStore()
        parser = PythonParser()
        source = (
            "def core():\n    pass\n"
            "def caller_a():\n    core()\n"
            "def caller_b():\n    caller_a()\n"
        )
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)
        return store

    def test_analyze_returns_result(self):
        store = self._build_store()
        analyzer = ImpactAnalyzer(store)
        result = analyzer.analyze("app.py::core", max_depth=3)
        assert result.target == "app.py::core"
        assert isinstance(result.blast_radius_score, float)

    def test_blast_radius_isolated(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def isolated():\n    pass\n"
        nodes, edges = parser.parse(source, "lone.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        analyzer = ImpactAnalyzer(store)
        result = analyzer.analyze("lone.py::isolated", max_depth=3)
        assert result.direct_callers == []
        assert result.transitive_callers == []


class TestCircularDependencyDetector:
    def test_no_cycles(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def a():\n    b()\ndef b():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        detector = CircularDependencyDetector(store)
        cycles = detector.detect()
        assert cycles == []

    def test_empty_store(self):
        store = SQLiteStore()
        detector = CircularDependencyDetector(store)
        cycles = detector.detect()
        assert cycles == []


class TestCoverageMapperSuite:
    def test_maps_test_by_naming(self):
        store = SQLiteStore()
        parser = PythonParser()

        source = "def my_func():\n    pass\n"
        nodes, edges = parser.parse(source, "my_func.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        test_source = "def test_my_func():\n    my_func()\n"
        nodes2, edges2 = parser.parse(test_source, "test_my_func.py")
        store.upsert_nodes(nodes2)
        store.upsert_edges(edges2)

        mapper = TestCoverageMapper(store)
        mapping = mapper.map_tests("my_func")
        assert len(mapping.test_files) >= 1
