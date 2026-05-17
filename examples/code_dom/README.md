# Examples — Code DOM

> Runnable code samples demonstrating the structural graph pipeline: parse → build → analyze → query.

---

## The Four Examples

| Example | Folder | Status | What It Demonstrates |
|---------|--------|--------|---------------------|
| 1 | [`python_parser/`](python_parser/) | Implemented | Python AST → CodeNode/CodeEdge graph, import resolver, call graph, SQLite store |
| 2 | [`impact_analyzer/`](impact_analyzer/) | Implemented | Blast radius traversal (BFS), circular dependency detection (DFS), test coverage mapping |
| 3 | [`dead_code_finder/`](dead_code_finder/) | Implemented | Entry point resolution, graph reachability (BFS), orphan classes, unused imports |
| 4 | [`refactor_planner/`](refactor_planner/) | Implemented | Change advisor, rename propagation, Mermaid flowchart + class diagrams, complexity scoring, repo stats |

---

## Running Examples

Each example has a standalone `main.py`:

```bash
# Install from repo root
pip install -e ".[all]"

# Run individual examples
python -m copilotas_JAM.examples.code_dom.python_parser.main
python -m copilotas_JAM.examples.code_dom.impact_analyzer.main
python -m copilotas_JAM.examples.code_dom.dead_code_finder.main
python -m copilotas_JAM.examples.code_dom.refactor_planner.main
```

## Running Tests

```bash
pytest code_dom/ -v
```
