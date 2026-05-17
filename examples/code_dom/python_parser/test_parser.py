"""Tests for the Python parser and SQLite store.

Phase 0 | Code DOM — Python Parser
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load main.py directly to avoid sys.path pollution across test files
_spec = importlib.util.spec_from_file_location(
    "python_parser_main", Path(__file__).parent / "main.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

CodeEdge = _mod.CodeEdge
CodeNode = _mod.CodeNode
PythonParser = _mod.PythonParser
SQLiteStore = _mod.SQLiteStore
_node_id = _mod._node_id


# --- PythonParser ---


class TestPythonParser:
    def test_parse_empty_source(self):
        parser = PythonParser()
        nodes, edges = parser.parse("", "empty.py")
        assert len(nodes) == 1  # FILE node only
        assert nodes[0].type == "FILE"

    def test_parse_function(self):
        source = "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
        parser = PythonParser()
        nodes, edges = parser.parse(source, "greet.py")
        fn_nodes = [n for n in nodes if n.type == "FUNCTION"]
        assert len(fn_nodes) == 1
        assert fn_nodes[0].name == "greet"
        assert "name: str" in fn_nodes[0].signature

    def test_parse_class_with_inheritance(self):
        source = "class Dog(Animal):\n    pass\n"
        parser = PythonParser()
        nodes, edges = parser.parse(source, "dog.py")
        cls_nodes = [n for n in nodes if n.type == "CLASS"]
        assert len(cls_nodes) == 1
        assert cls_nodes[0].name == "Dog"
        inherits = [e for e in edges if e.type == "INHERITS"]
        assert len(inherits) == 1

    def test_parse_imports(self):
        source = "import os\nfrom pathlib import Path\n"
        parser = PythonParser()
        nodes, edges = parser.parse(source, "imports.py")
        import_nodes = [n for n in nodes if n.type == "IMPORT"]
        assert len(import_nodes) == 2
        names = {n.name for n in import_nodes}
        assert "os" in names
        assert "pathlib.Path" in names

    def test_parse_syntax_error(self):
        parser = PythonParser()
        nodes, edges = parser.parse("def broken(:", "bad.py")
        assert nodes == []
        assert edges == []

    def test_calls_edges(self):
        source = "def foo():\n    bar()\n    baz()\n"
        parser = PythonParser()
        nodes, edges = parser.parse(source, "calls.py")
        call_edges = [e for e in edges if e.type == "CALLS"]
        assert len(call_edges) == 2

    def test_async_function(self):
        source = "async def fetch(url: str) -> bytes:\n    pass\n"
        parser = PythonParser()
        nodes, edges = parser.parse(source, "async.py")
        fn_nodes = [n for n in nodes if n.type == "FUNCTION"]
        assert len(fn_nodes) == 1
        assert "async def" in fn_nodes[0].signature


# --- SQLiteStore ---


class TestSQLiteStore:
    def test_upsert_and_stats(self):
        store = SQLiteStore()
        nodes = [
            CodeNode(id="n1", type="FILE", name="a.py", file_path="a.py"),
            CodeNode(id="n2", type="FUNCTION", name="foo", file_path="a.py"),
        ]
        edges = [
            CodeEdge(id="e1", source_id="n1", target_id="n2", type="CALLS"),
        ]
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)
        stats = store.stats()
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1
        assert stats["nodes_by_type"]["FILE"] == 1
        assert stats["edges_by_type"]["CALLS"] == 1
        store.close()

    def test_upsert_is_idempotent(self):
        store = SQLiteStore()
        node = CodeNode(id="n1", type="FILE", name="a.py", file_path="a.py")
        store.upsert_nodes([node])
        store.upsert_nodes([node])
        stats = store.stats()
        assert stats["total_nodes"] == 1
        store.close()


# --- Deterministic node ID ---


class TestNodeId:
    def test_same_input_same_id(self):
        assert _node_id("f.py", "foo", 10) == _node_id("f.py", "foo", 10)

    def test_different_input_different_id(self):
        assert _node_id("f.py", "foo", 10) != _node_id("f.py", "bar", 10)
