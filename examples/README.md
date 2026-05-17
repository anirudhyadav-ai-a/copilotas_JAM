# Examples — copilotas_JAM

> Python examples for structural codebase memory (Code Graph) and AI-powered CI/CD governance.

---

## Code Graph — Structural Memory

| Example | Folder | What It Demonstrates |
|---------|--------|---------------------|
| Python Parser | [`code_graph/python_parser/`](code_graph/python_parser/) | Python AST → CodeNode/CodeEdge graph, import resolver, call graph |
| Impact Analyzer | [`code_graph/impact_analyzer/`](code_graph/impact_analyzer/) | Blast radius traversal, dead code finder, circular dependency detector |
| Dead Code Finder | [`code_graph/dead_code_finder/`](code_graph/dead_code_finder/) | Graph reachability from entry points, orphan classes, unused imports |
| Refactor Planner | [`code_graph/refactor_planner/`](code_graph/refactor_planner/) | Rename propagation, change advisor, Mermaid diagram export |

## CI/CD Governance — Judge as CI Gate

| Example | Folder | What It Demonstrates |
|---------|--------|---------------------|
| PR Reviewer | [`ci_cd_governance/pr_reviewer/`](ci_cd_governance/pr_reviewer/) | Diff extraction → parallel per-file Judge review → verdict aggregation |
| Merge Gate | [`ci_cd_governance/merge_gate/`](ci_cd_governance/merge_gate/) | GitHub status check reporter + merge policy engine |
| Webhook Handler | [`ci_cd_governance/webhook_handler/`](ci_cd_governance/webhook_handler/) | FastAPI webhook server, event routing, async job dispatch |
| Metrics Collector | [`ci_cd_governance/metrics_collector/`](ci_cd_governance/metrics_collector/) | Reviews/day, block rate, override rate, time-to-fix |

---

## Running Examples

```bash
pip install -e ".[all]"

# Code Graph
python -m copilotas_JAM.examples.code_graph.python_parser.main
python -m copilotas_JAM.examples.code_graph.impact_analyzer.main
python -m copilotas_JAM.examples.code_graph.dead_code_finder.main
python -m copilotas_JAM.examples.code_graph.refactor_planner.main

# CI/CD Governance
python -m copilotas_JAM.examples.ci_cd_governance.pr_reviewer.main
python -m copilotas_JAM.examples.ci_cd_governance.merge_gate.main
python -m copilotas_JAM.examples.ci_cd_governance.webhook_handler.main
python -m copilotas_JAM.examples.ci_cd_governance.metrics_collector.main
```

```bash
pytest copilotas_JAM/ -v
```
