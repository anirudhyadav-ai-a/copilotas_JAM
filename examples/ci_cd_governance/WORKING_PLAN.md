# Working Plan — CI/CD Governance: AI Quality Gates

> **Companion implementation guide for the whitepaper:**
> *"CI/CD Governance: AI Quality Gates"*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [PR Review Pipeline](#2-pr-review-pipeline)
3. [GitHub Integration](#3-github-integration)
4. [Rubric System](#4-rubric-system)
5. [Merge Policy Engine](#5-merge-policy-engine)
6. [Override & Audit System](#6-override--audit-system)
7. [Agent Config & Registry](#7-agent-config--registry)
8. [Metrics & Analytics](#8-metrics--analytics)
9. [Webhook Handler](#9-webhook-handler)
10. [GitHub Actions Workflows](#10-github-actions-workflows)
11. [Decision Framework](#11-decision-framework)
12. [Appendix](#12-appendix)

---

## 1. Introduction

### The Problem: AI Reviews Without Teeth

AI code review today is advisory at best. It lives in chat, not in the merge pipeline.

```
Current state:
  Developer opens Copilot Chat
  Pastes code
  Gets suggestions
  Ignores half of them
  Merges anyway
          ↓
  BLOCK verdict means nothing if there's no gate
```

**CI/CD Governance** wires the Judge directly into the merge pipeline. Every PR gets reviewed. Every BLOCK prevents merge. Every override is logged. The rubric is code — versioned, diff'd, and reviewable.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CI/CD GOVERNANCE PIPELINE                     │
│                                                                  │
│  GitHub Event (PR opened / synchronized)                        │
│       │                                                          │
│       ▼                                                          │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐            │
│  │  Webhook   │   │    Diff    │   │   Rubric     │            │
│  │  Handler   │──▶│  Extractor │──▶│   Loader     │            │
│  │            │   │            │   │  (+ validator│            │
│  └────────────┘   └────────────┘   │  + inherit.) │            │
│                         │          └──────┬───────┘            │
│                         ▼                 │                      │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              PR REVIEWER (per changed file)          │        │
│  │                                                      │        │
│  │  file_1.py → Judge(rubric) → APPROVE (score: 92)   │        │
│  │  file_2.py → Judge(rubric) → REQUEST_CHANGES (71)  │        │
│  │  file_3.py → Judge(rubric) → BLOCK (score: 41)     │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                        │
│                         ▼                                        │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐            │
│  │  Verdict   │   │   Merge    │   │  GitHub      │            │
│  │ Aggregator │──▶│   Policy   │──▶│  Status +    │            │
│  │            │   │   Engine   │   │  Comments    │            │
│  └────────────┘   └────────────┘   └──────────────┘            │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │              METRICS STORE (SQLite / DB)            │         │
│  │  reviews | verdicts | overrides | time_to_fix      │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. PR Review Pipeline

### 2.1 Diff Extractor

```
Feature 1: Diff Extractor
───────────────────────────
Command: git diff --merge-base origin/main HEAD

Output per changed file:
{
  "file_path": "src/billing/calculator.py",
  "change_type": "modified",    # added | modified | deleted | renamed
  "hunks": [
    {
      "old_start": 42, "old_lines": 15,
      "new_start": 42, "new_lines": 22,
      "diff_text": "@@ -42,15 +42,22 @@\n ..."
    }
  ],
  "file_classification": "source",  # source | test | config | docs
  "language": "python"
}
```

### 2.2 PR Reviewer

```
Feature 2: PR Reviewer
────────────────────────
For each changed source file:
  1. Fetch full file content (not just the diff — Judge needs context)
  2. Load applicable rubric (see Feature 7-9)
  3. Optionally: fetch related context from codebase_context/ (callers, tests)
  4. Call Judge → get structured verdict

Parallelism: review all files concurrently (asyncio.gather)
Timeout: 60s per file, 300s for full PR review
```

### 2.3 Verdict Aggregator

```
Feature 3: Verdict Aggregator
───────────────────────────────
Input:  list of per-file verdicts
Output: single PR-level verdict

Rules:
  - Any BLOCK file → PR verdict = BLOCK
  - No BLOCK, any REQUEST_CHANGES → PR verdict = REQUEST_CHANGES
  - All APPROVE → PR verdict = APPROVE

PR score = weighted average of file scores
  (weighting: source files 2×, test files 1×, config files 0.5×)

Key findings = union of all MUST_FIX findings across files
```

---

## 3. GitHub Integration

### 3.1 GitHub Status Check Reporter

```
Feature 4: GitHub Status Check Reporter
──────────────────────────────────────────
POST /repos/{owner}/{repo}/statuses/{sha}

State mapping:
  APPROVE           → state: "success"
  REQUEST_CHANGES   → state: "failure"
  BLOCK             → state: "failure"
  In-progress       → state: "pending"

Payload:
{
  "state": "failure",
  "description": "Judge: BLOCK (score: 41/100) — 2 critical findings",
  "context": "ai-judge/code-review",
  "target_url": "https://your-dashboard/review/{review_id}"
}
```

### 3.2 Inline PR Comment Poster

```
Feature 5: Inline PR Comment Poster
──────────────────────────────────────
POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews

Each finding → one inline comment at the exact file:line

Payload:
{
  "body": "Overall verdict: BLOCK",
  "event": "REQUEST_CHANGES",
  "comments": [
    {
      "path": "src/billing/calculator.py",
      "line": 67,                     ← line in the NEW file
      "side": "RIGHT",
      "body": "CRITICAL: SQL query built via string concatenation — SQL injection risk (OWASP A03). Use parameterized queries.\n\n**Suggested fix:**\n```suggestion\n    cursor.execute('SELECT * FROM orders WHERE id = %s', (order_id,))\n```"
    }
  ]
}

Diff position mapping:
  Finding.line → calculate diff hunk position
  GitHub requires "position in the diff", not line number
  → Use diff parser to map line → position
```

### 3.3 PR Summary Poster

```
Feature 6: PR Summary Poster
──────────────────────────────
POST /repos/{owner}/{repo}/issues/{pull_number}/comments

Template:
## AI Judge Review — BLOCK (Score: 41/100)

| File | Verdict | Score |
|------|---------|-------|
| `calculator.py` | 🔴 BLOCK | 41 |
| `orders.py` | 🟡 REQUEST_CHANGES | 71 |
| `config.py` | 🟢 APPROVE | 94 |

### Must Fix Before Merge
1. **SQL Injection** in `calculator.py:67` — use parameterized queries
2. **Missing input validation** in `calculator.py:89` — validate order_id before DB call

### Suggested Fixes Available
See inline comments for copy-paste fix suggestions.

> Rubric: `.github/judge-rubric.md` | Model: claude-sonnet-4-6 | Reviewed: 2026-05-05 14:22 UTC
```

---

## 4. Rubric System

### 4.1 Rubric Loader

```
Feature 7: Rubric Loader
──────────────────────────
Load order (first found wins, with inheritance):
  1. .github/judge-rubric.md (repo-specific)
  2. Organization default rubric (fetched via GitHub org API or env var)
  3. Built-in default rubric (shipped with this package)

Rubric format: Markdown with structured sections
```

### 4.2 Rubric Schema Validator

```
Feature 8: Rubric Schema Validator
────────────────────────────────────
Required sections:
  ## Code Quality      (weight: configurable, default 25%)
  ## Security          (weight: configurable, default 30%)
  ## Testing           (weight: configurable, default 25%)
  ## Architecture      (weight: configurable, default 20%)

Valid severity levels: CRITICAL | HIGH | MEDIUM | LOW | INFO
Valid verdicts: APPROVE | REQUEST_CHANGES | BLOCK

Validation errors → logged as warnings, fallback to default rubric
```

### 4.3 Rubric Inheritance

```
Feature 9: Rubric Inheritance
───────────────────────────────
Path-based overrides:
  org_default_rubric.md          ← base
    └── .github/judge-rubric.md  ← overrides org default
          └── src/auth/*         ← stricter: security weight 60%, auto-BLOCK on any HIGH

Merge strategy:
  - Child sections override parent sections (not append)
  - Child weights override parent weights
  - Child thresholds override parent thresholds
  - Unspecified sections inherited from parent
```

---

## 5. Merge Policy Engine

```
Feature 10: Merge Policy Engine
──────────────────────────────────
Configurable rules in .github/judge-policy.yaml:

rules:
  - condition: verdict == "BLOCK"
    action: block_merge
    message: "AI Judge returned BLOCK verdict. Fix critical findings before merging."

  - condition: verdict == "REQUEST_CHANGES"
    action: require_recheck
    message: "Address requested changes and re-trigger review."

  - condition: score < 60
    action: block_merge
    message: "Review score below minimum threshold (60/100)."

  - condition: has_finding_severity("CRITICAL")
    action: block_merge
    message: "Critical findings must be resolved."

  - condition: changed_files_match("src/auth/*") and score < 85
    action: block_merge
    message: "Auth code requires score ≥ 85."
```

---

## 6. Override & Audit System

```
Feature 11: Override Handler
───────────────────────────────
Authorized users (defined in .github/judge-policy.yaml):
  authorized_overriders:
    - role: ADMIN
    - user: lead-engineer-github-login

Override flow:
  1. User comments on PR: "/judge-override Reason: deadline, fix tracked in #456"
  2. Webhook receives comment event
  3. Verify user is in authorized_overriders
  4. Log override: {pr, commit_sha, user, reason, timestamp, verdict_overridden}
  5. Post status check: success (with "OVERRIDE" label)
  6. Emit alert to configured Slack/email channel

Audit log schema (SQLite):
  overrides(pr_number, commit_sha, user, reason, original_verdict, timestamp)
```

---

## 7. Agent Config & Registry

```
Feature 13 + 14: Agent Config Loader & Registry
─────────────────────────────────────────────────
Config file format (.github/agents/security-reviewer.md):

---
name: security-reviewer
persona: Senior security engineer specializing in OWASP Top 10
tools:
  - codebase_context
  - code_dom.impact_analyzer
scope:
  - src/auth/
  - src/payments/
trigger:
  - changed_files_match("src/auth/*")
model: claude-sonnet-4-6
temperature: 0.1
---

# Security Reviewer Agent

You are a senior security engineer...

Registry:
  AgentRegistry.load(".github/agents/")
  AgentRegistry.get("security-reviewer")
  AgentRegistry.invoke("security-reviewer", context=pr_diff)
```

---

## 8. Metrics & Analytics

```
Feature 15-17: Metrics Collector
───────────────────────────────────
Schema:

CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    pr_number INTEGER,
    repo TEXT,
    verdict TEXT,
    score REAL,
    files_reviewed INTEGER,
    duration_seconds REAL,
    model TEXT,
    created_at TIMESTAMP
);

CREATE TABLE overrides (
    id TEXT PRIMARY KEY,
    review_id TEXT REFERENCES reviews(id),
    user TEXT,
    reason TEXT,
    created_at TIMESTAMP
);

CREATE TABLE time_to_fix (
    pr_number INTEGER,
    blocked_at TIMESTAMP,
    approved_at TIMESTAMP,
    fix_duration_seconds REAL
);

Dashboard metrics:
  - Reviews per day (rolling 30-day)
  - Verdict distribution: APPROVE / REQUEST_CHANGES / BLOCK (%)
  - Block rate trend (is Judge getting stricter or looser?)
  - Override rate (humans disagreeing with Judge → rubric calibration signal)
  - Median time-to-fix after BLOCK
  - False positive rate (overrides / blocks)
  - Average score by file type / author / rubric section
```

---

## 9. Webhook Handler

```
Feature 18: Webhook Handler
─────────────────────────────
FastAPI endpoint: POST /webhooks/github

Event routing:
  pull_request.opened          → trigger full PR review
  pull_request.synchronize     → trigger incremental review (changed files only)
  pull_request_review.submitted → if human APPROVE after BLOCK, log as override
  issue_comment.created        → check for /judge-override command

Security:
  Verify X-Hub-Signature-256 header (HMAC-SHA256 of payload with webhook secret)
  Reject events with invalid signature immediately

Async processing:
  Webhook returns 200 immediately
  Dispatch review job to background task queue
  Status: "pending" posted to GitHub while review runs
```

---

## 10. GitHub Actions Workflows

### judge-gate.yml

```yaml
# Feature 19: judge-gate.yml
name: AI Judge Gate

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  judge-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # need full history for git diff --merge-base

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e ".[all]"

      - name: Run Judge review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m ci_cd_governance.run_pr_review \
            --pr ${{ github.event.pull_request.number }} \
            --sha ${{ github.event.pull_request.head.sha }} \
            --repo ${{ github.repository }}
```

### drift-check.yml

```yaml
# Feature 12: drift-check.yml
name: Prompt Drift Check

on:
  schedule:
    - cron: '0 9 * * 1'   # Monday 9am UTC
  workflow_dispatch:

jobs:
  drift-detection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run drift suite
        run: python -m prompt_versioning.examples.drift_detector.main
      - name: Post results to Slack
        if: failure()
        run: python -m ci_cd_governance.notify_slack --channel "#ai-alerts"
```

---

## 11. Decision Framework

### When to block vs warn?

```
Finding severity   Action
─────────────────  ──────────────────────────────────────
CRITICAL           Always BLOCK — no exceptions (SQL injection, hardcoded secrets)
HIGH               BLOCK by default; rubric can downgrade to REQUEST_CHANGES
MEDIUM             REQUEST_CHANGES — must address before next review
LOW                Comment only — informational
INFO               Comment only — style suggestions
```

### Rubric override decision tree

```
Human overrides Judge verdict?
  ├── Reason: "Acknowledged, fix tracked in ticket" → log as planned_fix_override
  ├── Reason: "False positive, X pattern is intentional" → log as false_positive
  └── Reason: blank or "deadline" → log as deadline_override, flag for rubric review

If false_positive_rate > 20% for a specific rubric rule → flag for rubric recalibration
```

---

## 12. Appendix

### Dependencies

```
# GitHub integration
PyGithub>=2.0     # GitHub REST API client
cryptography>=41  # webhook HMAC signature verification

# Web server (webhook handler)
fastapi>=0.110
uvicorn>=0.27

# Database
# SQLite — built-in

# Background tasks
celery>=5.3  # optional, for distributed webhook processing
redis>=5.0   # optional, Celery broker
```

### Environment Variables

```bash
GITHUB_TOKEN=ghp_...           # GitHub personal access token or App token
GITHUB_WEBHOOK_SECRET=...       # Webhook HMAC secret
ANTHROPIC_API_KEY=...           # For Judge reviews
JUDGE_RUBRIC_PATH=.github/judge-rubric.md
JUDGE_MIN_SCORE=60              # PRs below this score are blocked
JUDGE_MODEL=claude-sonnet-4-6
METRICS_DB_PATH=./governance.sqlite
```

---

## Implementation Status

| Example | Status | Key Classes |
|---------|--------|-------------|
| `pr_reviewer/` | Implemented | `DiffExtractor`, `RubricLoader`, `FileLevelReviewer`, `VerdictAggregator`, `review_pr()` |
| `merge_gate/` | Implemented | `MergePolicyEngine` (verdict evaluation), `GitHubStatusReporter` (API simulation) |
| `webhook_handler/` | Implemented | `WebhookVerifier` (HMAC-SHA256), `EventRouter`, `OverrideCommandParser`, FastAPI app |
| `metrics_collector/` | Implemented | `MetricsStore` (SQLite), `MetricsCollector`, rolling KPIs (block rate, override rate, false positive rate, median time-to-fix) |
