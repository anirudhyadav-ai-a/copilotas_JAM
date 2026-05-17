"""Tests for the refactor planner.

Phase 0 | Code DOM — Refactor Planner
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load python_parser/main.py as "main" so that refactor_planner's
# ``from main import SQLiteStore`` resolves correctly.
_parser_path = Path(__file__).resolve().parent.parent / "python_parser" / "main.py"
_parser_spec = importlib.util.spec_from_file_location("main", _parser_path)
_parser_mod = importlib.util.module_from_spec(_parser_spec)
_saved_main = sys.modules.get("main")
sys.modules["main"] = _parser_mod
_parser_spec.loader.exec_module(_parser_mod)

_spec = importlib.util.spec_from_file_location(
    "refactor_planner_main", Path(__file__).parent / "main.py"
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
ChangeAdvisor = _mod.ChangeAdvisor
RefactorPlanner = _mod.RefactorPlanner
MermaidExporter = _mod.MermaidExporter
ComplexityScorer = _mod.ComplexityScorer
RepoStatsCollector = _mod.RepoStatsCollector


class TestChangeAdvisor:
    def test_advise_with_callers(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def target():\n    pass\ndef caller():\n    target()\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        advisor = ChangeAdvisor(store)
        actions = advisor.advise("app.py::target")
        assert isinstance(actions, list)

    def test_advise_no_callers(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def isolated():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        advisor = ChangeAdvisor(store)
        actions = advisor.advise("app.py::isolated")
        assert isinstance(actions, list)


class TestRefactorPlanner:
    def test_plan_rename(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def old_name():\n    pass\ndef caller():\n    old_name()\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        planner = RefactorPlanner(store)
        plan = planner.rename("app.py::old_name", "new_name")
        assert plan.old_name == "app.py::old_name"
        assert plan.new_name == "new_name"


class TestMermaidExporter:
    def test_export_flowchart(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def a():\n    b()\ndef b():\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        exporter = MermaidExporter(store)
        mermaid = exporter.dependency_flowchart()
        assert "graph" in mermaid

    def test_export_class_diagram(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "class Animal:\n    pass\nclass Dog(Animal):\n    pass\n"
        nodes, edges = parser.parse(source, "models.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        exporter = MermaidExporter(store)
        diagram = exporter.class_diagram()
        assert "classDiagram" in diagram


class TestComplexityScorer:
    def test_score_function(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def simple():\n    pass\ndef caller():\n    simple()\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        scorer = ComplexityScorer(store)
        scores = scorer.score_all()
        assert len(scores) > 0


class TestRepoStatsCollector:
    def test_collect_stats(self):
        store = SQLiteStore()
        parser = PythonParser()
        source = "def a():\n    b()\ndef b():\n    pass\nclass Foo:\n    pass\n"
        nodes, edges = parser.parse(source, "app.py")
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)

        collector = RepoStatsCollector(store)
        stats = collector.collect()
        assert stats.total_files >= 1
        assert stats.total_functions >= 2
        assert stats.total_classes >= 1
