# copilotas_JAM: Judge, Advocate & Mediator

> Complete, self-contained judgment layer: AI code review with structured verdicts, architecture decision records, design conflict mediation, structural codebase memory, and full CI/CD merge gate — all in one folder.

This folder is the complete reference implementation for *"Beyond the Code: LLM Copilot as Judge, Advocate & Mediator"*. It covers everything from zero-setup Markdown prompt templates through a VS Code extension to a full GitHub PR governance pipeline with code DOM impact analysis.

---

## Start Here

| Document | What It Is |
|---|---|
| [`WORKING_PLAN.md`](WORKING_PLAN.md) | **Implementation guide** — all 61 must-have features, architecture diagrams, decision frameworks |
| [`prompts/`](prompts/) | Zero-setup Markdown templates — copy, paste, run |
| [`vscodebase/`](vscodebase/) | VS Code extension with `@judge`, `@advocate`, `@mediator`, `@graph` chat participants |
| [`examples/`](examples/) | Python examples — code DOM, CI/CD governance |

---

## Folder Layout

```
copilotas_JAM/
├── WORKING_PLAN.md
├── README.md
├── Dockerfile
├── docker-compose.yml
├── ci.yml                          ← CI workflow template
│
├── tests/
│   └── test_copilotas_jam.py
│
├── prompts/                        ← Markdown templates (zero setup)
│   ├── judge-review.md
│   ├── advocate-adr.md
│   ├── advocate-devil.md
│   ├── mediate-design.md
│   └── team_standards.md
│
├── vscodebase/                     ← VS Code extension (TypeScript)
│   ├── src/extension.ts
│   └── src/prompts.ts
│
└── examples/
    ├── code_graph/                   ← structural memory: call graph, impact analyzer, dead code
    │   ├── python_parser/
    │   ├── impact_analyzer/
    │   ├── dead_code_finder/
    │   └── refactor_planner/
    └── ci_cd_governance/           ← Judge as CI gate: PR review, merge policy, webhooks
        ├── pr_reviewer/
        ├── merge_gate/
        ├── webhook_handler/
        └── metrics_collector/
```

---

## Sections Covered

### Judgment Layer — Core (18 features)
1. Structured code review with rubric (APPROVE / REQUEST_CHANGES / BLOCK)
2. Security audit (OWASP Top-10 focused)
3. ADR generation (Architecture Decision Records)
4. Devil's advocate stress-testing
5. Design conflict mediation
6. Dependency conflict resolution
7. Multi-model per role (Claude / GPT-4o / Gemini with fallback)
8. File context from active editor
9. Runtime-configurable rubric (.github/judge-rubric.md)
10. Full codebase context (callers, tests, imports via embeddings)
11. PR-level review (GitHub App)
12. CI merge gate (GitHub Actions status check)
13. Verdict history & persistence (SQLite)
14. Usage telemetry
15. Conversation memory (session-scoped)
16. Suggested fixes (code suggestions on BLOCK)
17. Batch review (multiple files → consolidated report)
18. Override tracking (human overrides → rubric calibration)

### Code Graph — Structural Memory (23 features — 5 implemented)
19. Python AST parser (classes, functions, imports, decorators)
20. TypeScript tree-sitter parser
21. CodeNode data model
22. CodeEdge data model
23. Import resolver (relative → absolute)
24. Call graph builder
25. Inheritance tree
26. Impact analyzer (blast radius from changed function)
27. Dead code finder
28. Circular dependency detector
29. Test coverage mapper
30. Complexity scorer (cyclomatic, cognitive, nesting, LOC)
31. Coupling analyzer (afferent, efferent, instability)
32. Persistent SQLite store
33. Incremental update (git-diff based)
34. Snapshot & diff
35. Structural history
36. Query API
37. Change advisor
38. Refactor planner
39. Mermaid diagram export
40. Complexity heatmap
41. Repo stats report

### CI/CD Governance — Judge as CI Gate (20 features — 5 implemented)
42. Diff extractor
43. PR reviewer (parallel per-file Judge review)
44. Verdict aggregator
45. GitHub status check reporter
46. Inline PR comment poster
47. PR summary poster
48. Rubric loader + schema validator
49. Rubric inheritance (org → repo → path-specific)
50. Merge policy engine
51. Override handler (authorized override + audit log)
52. Drift detection in CI
53. Agent config loader (.github/agents/*.md)
54. Agent registry
55. Metrics collector
56. False positive tracker
57. Time-to-fix tracker
58. Webhook handler (PR opened / synchronized / reviewed)
59. GitHub Actions workflows (judge-gate.yml, drift-check.yml, metrics-export.yml)
60. Suggested fix generator (PR suggestion blocks)
61. Multi-model per role with fallback chain

---

## Quick Start

```bash
# Option A — Markdown templates (zero setup)
# Open prompts/judge-review.md and follow instructions

# Option B — VS Code extension
cd vscodebase && npm install && npm run compile
# Then install the .vsix in VS Code

# Option C — Python examples
pip install -e ".[all]"
python -m copilotas_JAM.examples.code_graph.python_parser.main
python -m copilotas_JAM.examples.code_graph.dead_code_finder.main
python -m copilotas_JAM.examples.code_graph.refactor_planner.main
python -m copilotas_JAM.examples.ci_cd_governance.pr_reviewer.main
python -m copilotas_JAM.examples.ci_cd_governance.merge_gate.main
python -m copilotas_JAM.examples.ci_cd_governance.webhook_handler.main
python -m copilotas_JAM.examples.ci_cd_governance.metrics_collector.main

# Full stack (app + Redis + pgvector)
docker-compose up

# Tests
pytest copilotas_JAM/ -v
```

---

## License

MIT License
