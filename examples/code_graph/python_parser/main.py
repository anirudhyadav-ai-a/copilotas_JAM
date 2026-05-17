"""
Code Graph — Example 1: Python Parser & Graph Builder

Demonstrates:
  - Parsing Python files via the `ast` module
  - Extracting CodeNode objects (FILE, CLASS, FUNCTION, IMPORT)
  - Building CodeEdge objects (IMPORTS, CALLS, INHERITS)
  - Resolving relative imports to absolute module paths
  - Storing the graph in SQLite

Run:
    python -m copilotas_JAM.examples.code_graph.python_parser.main [TARGET_DIR]
"""

from __future__ import annotations

import ast
import hashlib
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CodeNode:
    """A structural element extracted from source code."""

    id: str
    type: str  # FILE, CLASS, FUNCTION, IMPORT
    name: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    signature: str | None = None
    docstring: str | None = None
    language: str = "python"
    content_hash: str | None = None


@dataclass
class CodeEdge:
    """A relationship between two CodeNode elements."""

    id: str
    source_id: str
    target_id: str
    type: str  # IMPORTS, CALLS, INHERITS
    call_site: int | None = None  # line number where the call/import occurs


def _node_id(file_path: str, name: str, line: int | None = None) -> str:
    """Deterministic node ID from file + name + line."""
    key = f"{file_path}:{name}:{line or 0}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Python AST parser
# ---------------------------------------------------------------------------


class PythonParser:
    """Parse a single Python file into CodeNode and CodeEdge lists."""

    def parse(
        self, source: str, file_path: str
    ) -> tuple[list[CodeNode], list[CodeEdge]]:
        """Parse *source* and return (nodes, edges)."""
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return [], []

        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []

        content_hash = hashlib.sha256(source.encode()).hexdigest()[:12]

        # FILE node
        file_node_id = _node_id(file_path, "__file__")
        nodes.append(
            CodeNode(
                id=file_node_id,
                type="FILE",
                name=Path(file_path).name,
                file_path=file_path,
                start_line=1,
                end_line=len(source.splitlines()),
                content_hash=content_hash,
            )
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_id = _node_id(file_path, node.name, node.lineno)
                nodes.append(
                    CodeNode(
                        id=cls_id,
                        type="CLASS",
                        name=node.name,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        docstring=ast.get_docstring(node),
                        content_hash=content_hash,
                    )
                )

                # INHERITS edges
                for base in node.bases:
                    base_name = _base_name(base)
                    if base_name:
                        base_id = _node_id(file_path, base_name)
                        edges.append(
                            CodeEdge(
                                id=uuid.uuid4().hex[:16],
                                source_id=cls_id,
                                target_id=base_id,
                                type="INHERITS",
                                call_site=node.lineno,
                            )
                        )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = _function_signature(node)
                fn_id = _node_id(file_path, node.name, node.lineno)
                nodes.append(
                    CodeNode(
                        id=fn_id,
                        type="FUNCTION",
                        name=node.name,
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        signature=sig,
                        docstring=ast.get_docstring(node),
                        content_hash=content_hash,
                    )
                )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imp_id = _node_id(file_path, alias.name, node.lineno)
                    nodes.append(
                        CodeNode(
                            id=imp_id,
                            type="IMPORT",
                            name=alias.name,
                            file_path=file_path,
                            start_line=node.lineno,
                        )
                    )
                    edges.append(
                        CodeEdge(
                            id=uuid.uuid4().hex[:16],
                            source_id=file_node_id,
                            target_id=imp_id,
                            type="IMPORTS",
                            call_site=node.lineno,
                        )
                    )

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imp_id = _node_id(file_path, full_name, node.lineno)
                    nodes.append(
                        CodeNode(
                            id=imp_id,
                            type="IMPORT",
                            name=full_name,
                            file_path=file_path,
                            start_line=node.lineno,
                        )
                    )
                    edges.append(
                        CodeEdge(
                            id=uuid.uuid4().hex[:16],
                            source_id=file_node_id,
                            target_id=imp_id,
                            type="IMPORTS",
                            call_site=node.lineno,
                        )
                    )

        # CALLS edges — scan function bodies for Call nodes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                caller_id = _node_id(file_path, node.name, node.lineno)
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        callee_name = _call_name(child)
                        if callee_name:
                            callee_id = _node_id(file_path, callee_name)
                            edges.append(
                                CodeEdge(
                                    id=uuid.uuid4().hex[:16],
                                    source_id=caller_id,
                                    target_id=callee_id,
                                    type="CALLS",
                                    call_site=getattr(child, "lineno", None),
                                )
                            )

        return nodes, edges


def _base_name(node: ast.expr) -> str | None:
    """Extract base class name from an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return (
            f"{_base_name(node.value)}.{node.attr}"
            if isinstance(node.value, (ast.Name, ast.Attribute))
            else node.attr
        )
    return None


def _call_name(node: ast.Call) -> str | None:
    """Extract function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a signature string from a function definition."""
    args = []
    for arg in node.args.args:
        annotation = ""
        if arg.annotation:
            annotation = f": {ast.unparse(arg.annotation)}"
        args.append(f"{arg.arg}{annotation}")
    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return_ann = ""
    if node.returns:
        return_ann = f" -> {ast.unparse(node.returns)}"
    return f"{prefix}def {node.name}({', '.join(args)}){return_ann}"


# ---------------------------------------------------------------------------
# SQLite store
# ---------------------------------------------------------------------------


class SQLiteStore:
    """Persist Code Graph nodes and edges in a SQLite database."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                signature TEXT,
                docstring TEXT,
                language TEXT DEFAULT 'python',
                content_hash TEXT,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS edges (
                edge_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                call_site INTEGER,
                FOREIGN KEY (source_id) REFERENCES nodes(node_id),
                FOREIGN KEY (target_id) REFERENCES nodes(node_id)
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        """)

    def upsert_nodes(self, nodes: list[CodeNode]) -> int:
        """Insert or replace nodes. Returns count of upserted rows."""
        self._conn.executemany(
            """INSERT OR REPLACE INTO nodes
               (node_id, kind, name, file_path, start_line, end_line, signature, docstring, language, content_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    n.id,
                    n.type,
                    n.name,
                    n.file_path,
                    n.start_line,
                    n.end_line,
                    n.signature,
                    n.docstring,
                    n.language,
                    n.content_hash,
                )
                for n in nodes
            ],
        )
        self._conn.commit()
        return len(nodes)

    def upsert_edges(self, edges: list[CodeEdge]) -> int:
        """Insert or replace edges. Returns count of upserted rows."""
        self._conn.executemany(
            """INSERT OR REPLACE INTO edges
               (edge_id, source_id, target_id, kind, call_site)
               VALUES (?, ?, ?, ?, ?)""",
            [(e.id, e.source_id, e.target_id, e.type, e.call_site) for e in edges],
        )
        self._conn.commit()
        return len(edges)

    def stats(self) -> dict:
        """Return summary statistics of the stored graph."""
        node_counts = dict(
            self._conn.execute(
                "SELECT kind, COUNT(*) FROM nodes GROUP BY kind"
            ).fetchall()
        )
        edge_counts = dict(
            self._conn.execute(
                "SELECT kind, COUNT(*) FROM edges GROUP BY kind"
            ).fetchall()
        )
        total_nodes = sum(node_counts.values())
        total_edges = sum(edge_counts.values())
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts,
        }

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse Python files in a target directory and print graph stats."""
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        # Default: parse the intelligence_tiers phase as a demo
        target_dir = Path(__file__).parents[3].parent / "intelligence_tiers"

    if not target_dir.exists():
        print(f"Directory not found: {target_dir}")
        return

    parser = PythonParser()
    store = SQLiteStore()  # in-memory for demo

    file_count = 0
    for py_file in sorted(target_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        source = py_file.read_text(errors="replace")
        nodes, edges = parser.parse(source, str(py_file))
        store.upsert_nodes(nodes)
        store.upsert_edges(edges)
        file_count += 1

    stats = store.stats()
    print(f"\nCode Graph — Parsed {file_count} files from {target_dir.name}/")
    print(f"  Nodes: {stats['total_nodes']}")
    for ntype, count in sorted(stats["nodes_by_type"].items()):
        print(f"    {ntype}: {count}")
    print(f"  Edges: {stats['total_edges']}")
    for etype, count in sorted(stats["edges_by_type"].items()):
        print(f"    {etype}: {count}")

    store.close()


if __name__ == "__main__":
    main()
