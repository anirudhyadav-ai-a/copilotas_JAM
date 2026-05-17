# Examples — CI/CD Governance

> Runnable code samples demonstrating the full AI quality gate pipeline.

---

## The Four Examples

| Example | Folder | Status | What It Demonstrates |
|---------|--------|--------|---------------------|
| 1 | [`pr_reviewer/`](pr_reviewer/) | Implemented | Diff extraction → per-file Judge review → verdict aggregation (24 tests) |
| 2 | [`merge_gate/`](merge_gate/) | Implemented | Merge policy engine, GitHub status reporter, inline comments, override handling |
| 3 | [`webhook_handler/`](webhook_handler/) | Implemented | FastAPI webhook server, HMAC verification, event routing, async dispatch, /judge-override parsing |
| 4 | [`metrics_collector/`](metrics_collector/) | Implemented | SQLite metrics store, rolling KPIs (block rate, override rate, false positive rate, time-to-fix) |

---

## Running Examples

Each example has a standalone `main.py`:

```bash
# Install from repo root
pip install -e ".[all]"

# Run individual examples
python -m copilotas_JAM.examples.ci_cd_governance.pr_reviewer.main
python -m copilotas_JAM.examples.ci_cd_governance.merge_gate.main
python -m copilotas_JAM.examples.ci_cd_governance.webhook_handler.main
python -m copilotas_JAM.examples.ci_cd_governance.metrics_collector.main
```

Set required env vars:
```bash
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=...
```

## Running Tests

```bash
pytest ci_cd_governance/ -v
```
