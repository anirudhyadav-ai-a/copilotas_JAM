# Working Plan — Copilotas JAM: Judge, Advocate & Mediator

> **Companion implementation guide for the whitepaper:**
> *"Beyond the Code: LLM Copilot as Judge, Advocate & Mediator"*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [The Judge — How to Implement](#3-the-judge--how-to-implement)
4. [The Advocate — How to Implement](#4-the-advocate--how-to-implement)
5. [The Mediator — How to Implement](#5-the-mediator--how-to-implement)
6. [VS Code Extension — Build & Install Guide](#6-vs-code-extension--build--install-guide)
7. [Team Rollout Plan](#7-team-rollout-plan)
8. [Measuring Success — 4-Week Scorecard](#8-measuring-success--4-week-scorecard)
9. [Appendix](#9-appendix)

---

## 1. Introduction

### What Is the Judgment Layer?

GitHub Copilot, Devin, and Claude Code are optimised for **generation** — they write code, ship tasks, and reason over repositories. But none of them, by default, tells you whether the code is safe to merge, argues for the right architecture, or resolves the deadlock blocking your team.

The **Judgment Layer** fills this gap by repurposing the same LLMs that generate code into three new roles:

| Role | What It Does | Problem It Solves |
|---|---|---|
| ⚖ **Judge** | Reviews code against a rubric; returns structured verdicts | Generated code that compiles and passes tests — but is wrong |
| 📐 **Advocate** | Generates Architecture Decision Records; stress-tests proposals | Design decisions made without rigorous preparation |
| 🤝 **Mediator** | Finds synthesis between competing engineering positions | Team deadlocks that block sprints and stall agents |

### How It Works with Your Copilot

The Judgment Layer **piggybacks your existing Copilot setup**. It does not require separate API keys or external LLM services. It uses whichever LLM your organisation has configured behind Copilot — the same model, the same approved infrastructure, the same security boundary.

You interact with the roles in two ways:

- **Option A — Markdown Templates:** Copy a prompt, customise it, paste into Copilot Chat. Zero setup, fully customisable.
- **Option B — VS Code Extension:** Type `@judge`, `@advocate`, `@mediator`, or `@codedom` in Copilot Chat. Integrated experience, prompts baked in.
- **Option C — Python CLI:** Run the Code Graph and CI/CD Governance examples directly from the command line.

---

## 2. Architecture Overview

### The Piggyback Pattern

```
┌─────────────────────────────────────────────────────────┐
│  Engineer's VS Code                                     │
│                                                         │
│  ┌──────────────────────┐   ┌────────────────────────┐  │
│  │  Option A             │   │  Option B               │  │
│  │  Copy MD template     │   │  @judge / @advocate     │  │
│  │  ↓                    │   │  @mediator commands     │  │
│  │  Paste into           │   │  ↓                      │  │
│  │  Copilot Chat         │   │  Extension constructs   │  │
│  │  ↓                    │   │  prompt + context        │  │
│  │  Customise & send     │   │  ↓                      │  │
│  └──────────┬───────────┘   └──────────┬─────────────┘  │
│              │                          │                │
│              └──────────┬───────────────┘                │
│                         ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Copilot's LLM (your org's configured model)     │   │
│  │  No extra API keys — same approved infra          │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│                         ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Structured Output                                │   │
│  │  • Verdict (APPROVE / REQUEST_CHANGES / BLOCK)    │   │
│  │  • ADR document                                   │   │
│  │  • Synthesis + implementation steps               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Decision: Which Option to Use

| Factor | Option A (MD Templates) | Option B (VS Code Extension) |
|---|---|---|
| **Setup time** | Zero — copy and paste | 10-15 min install |
| **Customisable prompts** | Yes — edit freely | No — prompts baked into extension |
| **UX polish** | Manual copy/paste | `@` commands in Copilot Chat |
| **Best for** | Evaluation, custom workflows, sharing | Daily use, consistent team experience |
| **Recommendation** | Start here | Graduate to this after validation |

**Our advice:** Start with Option A to validate the concept with your team. Once proven, deploy Option B for a frictionless daily workflow.

---

## 3. The Judge — How to Implement

> **The problem:** Copilot generates 200 lines. They compile. Tests pass. You merge. Three weeks later, production breaks because the code silently misused an API parameter. Nobody read the code carefully enough — because it looked right.

> **The Judge:** Reads code against a rubric you define. Returns a structured verdict — not just "looks good", but severity-graded findings that can gate CI, feed into PR threads, or trigger a follow-up fix session.

---

### Option A — MD Template (Zero Setup, Fully Customisable)

> **Full template with customisation guide:** [`prompts/judge-review.md`](prompts/judge-review.md)
> **Quick reference (all templates on one page):** [`prompts/README.md`](prompts/README.md)

**How to use:**

1. Open [`prompts/judge-review.md`](prompts/judge-review.md)
2. Copy the prompt. Replace `[PLACEHOLDER]` sections with your code and rubric.
3. Paste into Copilot Chat and send.

The template includes:
- **Categorised rubric** — Code Quality, Security, Testing, Architecture sections with specific checks
- **Customisation guide** — stack-specific rules to add for React/TypeScript, Python/FastAPI, Java/Spring, Go, and more
- **Verdict actions** — what to do with APPROVE, REQUEST_CHANGES, and BLOCK outcomes
- **Severity levels** — how error/warn/info map to verdicts
- **Copilot follow-up** — suggested commands to hand issues directly to Copilot for fixing

#### What to Do with the Verdict

| Verdict | Action |
|---|---|
| **APPROVE** | Safe to merge. Record the score for calibration. |
| **REQUEST_CHANGES** | Fix the listed issues, re-run the Judge. |
| **BLOCK** | Do not merge. Fix critical issues first. Hand off to Copilot: *"Fix these issues: [paste must-fix list]"* |

---

### Option B — VS Code Extension

> **Full extension codebase:** [`vscodebase/`](vscodebase/) — build & install instructions in [`vscodebase/README.md`](vscodebase/README.md)

Type in Copilot Chat:
```
@judge is this implementation correct?
```
or:
```
@judge /review check for security issues
@judge /security
```

The extension:
1. Reads the currently active file / selection as context (or files attached via `#file`)
2. Loads the Judge role prompt (baked into [`vscodebase/src/prompts.ts`](vscodebase/src/prompts.ts))
3. Sends to Copilot's LLM via `vscode.lm.selectChatModels()` — no separate API keys
4. Streams a structured verdict back to the chat panel

**Build & install:** See [`vscodebase/README.md`](vscodebase/README.md) or [Section 6](#6-vs-code-extension--build--install-guide).

---

## 4. The Advocate — How to Implement

> **The problem:** You have a strong technical instinct that the team should use Redis Streams instead of Kafka. You're probably right. But you have one shot in tomorrow's design review to convince the architect and the staff engineer who built the existing Kafka setup. Without preparation, your instinct loses to their familiarity.

> **The Advocate:** Constructs the case. Generates a complete Architecture Decision Record with anticipated objections and pre-prepared responses. Run the Devil's Advocate variant first to stress-test your proposal before you commit to it publicly.

---

### Option A — MD Templates (Zero Setup, Fully Customisable)

Two templates work together:

| Template | Purpose | File |
|---|---|---|
| **ADR Generator** | Generate a complete Architecture Decision Record | [`prompts/advocate-adr.md`](prompts/advocate-adr.md) |
| **Devil's Advocate** | Stress-test a proposal before committing | [`prompts/advocate-devil.md`](prompts/advocate-devil.md) |

**How to use:**

1. **Start with Devil's Advocate** — open [`prompts/advocate-devil.md`](prompts/advocate-devil.md), paste your proposal, get a PROCEED / REVISE / RECONSIDER verdict.
2. **If PROCEED** — open [`prompts/advocate-adr.md`](prompts/advocate-adr.md), paste your proposal + codebase context, generate the full ADR.
3. **Take the ADR to your design review** — you now have a structured document with anticipated objections and pre-prepared responses.
4. **After approval** — hand the ADR to Copilot or Devin: *"Implement this ADR: [paste]"*.

The templates include:
- **ADR Generator:** Full output format with Context, Decision, Rationale, Alternatives, Trade-offs, Consequences, and Anticipated Objections sections
- **Devil's Advocate:** Risk scoring, critical flaws, hidden assumptions, failure scenarios, and a fairness section acknowledging proposal strengths
- **Workflow diagrams** showing the complete Advocate flow
- **Agent handoff instructions** for Copilot and Devin

#### The Advocate Workflow

```
1. Write your proposal (2-5 sentences)
         │
         ▼
2. Run Devil's Advocate first (advocate-devil.md)
         │
    ┌────┴─────┐
    │          │
 PROCEED    REVISE / RECONSIDER
    │          │
    │      Revise proposal,
    │      re-run Devil's Advocate
    │          │
    ▼          ▼
3. Generate ADR (advocate-adr.md)
         │
         ▼
4. Review & take to design meeting
         │
         ▼
5. After approval → hand off to Copilot / Devin
```

#### Gate Rule

| Devil's Advocate Verdict | Action |
|---|---|
| **PROCEED** | Safe to generate the ADR and hand off to agents. |
| **REVISE** | Update the proposal first. Re-run Devil's Advocate. |
| **RECONSIDER** | Escalate to architecture review. Do not hand off to agents yet. |

---

### Option B — VS Code Extension

> **Full extension codebase:** [`vscodebase/`](vscodebase/)

Type in Copilot Chat:
```
@advocate /adr We should migrate from REST to GraphQL because...
```
or:
```
@advocate /devil We should replace PostgreSQL with MongoDB because...
```

The extension constructs the appropriate prompt (ADR or Devil's Advocate from [`vscodebase/src/prompts.ts`](vscodebase/src/prompts.ts)), injects any `#file` references as codebase context, and streams the ADR or risk assessment directly in the chat panel.

**Build & install:** See [`vscodebase/README.md`](vscodebase/README.md) or [Section 6](#6-vs-code-extension--build--install-guide).

---

## 5. The Mediator — How to Implement

> **The problem:** Alice wants in-process caching with Redis fallback. Bob wants Redis-only with a thin client. Both are correct in different ways. The thread has been going for three days across Slack and Notion. Meanwhile, Copilot is sitting idle waiting for a clear architectural direction.

> **The Mediator:** Does not pick a winner. It reads both positions, identifies the genuine common ground, names the real disagreement (which is almost never the surface disagreement), proposes a synthesis that preserves the strongest elements of both, and suggests the smallest experiment that would validate the synthesis.

---

### Option A — MD Template (Zero Setup, Fully Customisable)

> **Full template with usage guide:** [`prompts/mediate-design.md`](prompts/mediate-design.md)
> **Quick reference:** [`prompts/README.md`](prompts/README.md)

**How to use:**

1. Open [`prompts/mediate-design.md`](prompts/mediate-design.md)
2. Fill in the Codebase Context, Engineer A Position, and Engineer B Position sections. **Include reasoning, not just conclusions** — the reasoning is where common ground hides.
3. Paste into Copilot Chat and send.

The template includes:
- **Structured output** — Common Ground, Real Disagreement, Position Strengths, Synthesis, Implementation Steps, Suggested Experiment
- **Usage guide** — step-by-step process from mediation output to team agreement to agent handoff
- **Agent handoff matrix** — which agent (Copilot / Devin / Claude Code) is best for which type of implementation
- **Tips for better mediation** — how to frame positions for better results

#### How to Use the Mediator Output

1. **Share the synthesis** with both engineers. It is a starting point, not a verdict.
2. **Run the suggested experiment** — the smallest test that would validate the synthesis before committing.
3. **Once the team agrees** → paste the Implementation Steps directly into a Copilot session or Devin task brief to execute.

---

### Option B — VS Code Extension

> **Full extension codebase:** [`vscodebase/`](vscodebase/)

Type in Copilot Chat:
```
@mediator /design
Position A: We should use in-process caching because...
Position B: We should use Redis-only because...
```
or for dependency conflicts:
```
@mediator /deps pandas>=2.0 conflicts with scikit-learn 1.2.x
```

The extension loads the appropriate Mediator prompt from [`vscodebase/src/prompts.ts`](vscodebase/src/prompts.ts), injects any `#file` context, and streams the synthesis with implementation steps.

**Build & install:** See [`vscodebase/README.md`](vscodebase/README.md) or [Section 6](#6-vs-code-extension--build--install-guide).

---

## 6. VS Code Extension — Build & Install Guide

> **Full extension codebase:** [`vscodebase/`](vscodebase/)
> **Detailed README:** [`vscodebase/README.md`](vscodebase/README.md)

The extension is a complete, buildable VS Code Copilot Chat Participant project. It registers `@judge`, `@advocate`, and `@mediator` as commands in Copilot Chat. The extension piggybacks your Copilot's LLM — no separate API keys required.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│  VS Code Extension (TypeScript)                          │
│                                                          │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │  @judge       │  │  @advocate     │  │  @mediator    │  │
│  │  participant  │  │  participant   │  │  participant  │  │
│  └──────┬───────┘  └──────┬────────┘  └──────┬───────┘  │
│         │                 │                   │          │
│         └────────┬────────┘───────────────────┘          │
│                  ▼                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Role Prompt Builder (src/prompts.ts)             │   │
│  │  • Load role-specific system prompt               │   │
│  │  • Inject active file / selection as context      │   │
│  │  • Handle #file references                        │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  vscode.lm.selectChatModels()                     │   │
│  │  → Picks from your org's available Copilot LLMs   │   │
│  │  → Sends constructed prompt via sendRequest()     │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Key APIs

| VS Code API | Purpose |
|---|---|
| `vscode.chat.createChatParticipant()` | Register `@judge`, `@advocate`, `@mediator` |
| `vscode.lm.selectChatModels()` | Access your org's configured Copilot LLM models |
| `model.sendRequest()` | Send the constructed prompt to the LLM |
| `request.references` | Get the files/selections the user attached with `#file` |
| `stream.markdown()` | Stream the structured response back to the chat panel |

### Project Structure

```
vscodebase/
├── package.json          ← Extension manifest + chat participant registration
├── tsconfig.json         ← TypeScript config
├── .gitignore
├── .vscodeignore         ← Files excluded from .vsix package
├── README.md             ← Full usage guide with examples
└── src/
    ├── extension.ts      ← Entry point: handler registration + LLM interaction
    └── prompts.ts        ← All baked-in role prompts (Judge, Advocate, Mediator)
```

### Key Source Files

| File | What It Contains |
|---|---|
| [`src/prompts.ts`](vscodebase/src/prompts.ts) | All role prompts — Judge review, Judge security, Advocate ADR, Advocate Devil's Advocate, Mediator design, Mediator deps |
| [`src/extension.ts`](vscodebase/src/extension.ts) | Handler functions for each role, model selection logic, file context injection, response streaming |
| [`package.json`](vscodebase/package.json) | Chat Participant declarations with commands and descriptions |

### Build & Install

```bash
cd copilotas_JAM/vscodebase

# 1. Install dependencies
npm install

# 2. Compile TypeScript
npm run compile

# 3. Package as .vsix
npm run package
# → produces copilotas-jam-0.1.0.vsix

# 4. Install in VS Code
code --install-extension copilotas-jam-0.1.0.vsix
```

### Available Commands

| Command | Description |
|---|---|
| `@judge` or `@judge /review` | Review active file against the rubric |
| `@judge /security` | OWASP Top-10 security audit |
| `@advocate /adr` | Generate Architecture Decision Record |
| `@advocate /devil` | Devil's Advocate stress test |
| `@mediator /design` | Design conflict mediation |
| `@mediator /deps` | Dependency version conflict resolution |

For full usage examples, see [`vscodebase/README.md`](vscodebase/README.md).

---

## 7. Team Rollout Plan

### Phase 1 — Validate (Week 1)

**Goal:** Prove the concept with 2-3 engineers using MD templates (Option A).

| Step | Action | Who |
|---|---|---|
| 1 | Copy `prompts/` folder to your team's shared repo | Lead |
| 2 | Customise the Judge rubric for your codebase | Lead + 1 senior |
| 3 | Each pilot engineer runs the Judge on 3 real PRs | 2-3 engineers |
| 4 | Each pilot engineer runs the Advocate on 1 real design proposal | Same engineers |
| 5 | Collect feedback: did the verdicts add value? | Lead |

**Success criteria:** At least one meaningful issue caught that would have been missed.

### Phase 2 — Deploy (Week 2-3)

**Goal:** Move from manual templates to the integrated VS Code extension (Option B).

| Step | Action | Who |
|---|---|---|
| 1 | Build and package the extension (see Section 6) | Lead / DevEx |
| 2 | Distribute the `.vsix` to the team | Lead |
| 3 | Team uses `@judge` on all new PRs for one sprint | All engineers |
| 4 | Run `@advocate devil` before every design review | Proposing engineers |
| 5 | Collect verdicts and override data | Lead |

**Success criteria:** 70%+ of the team is using at least one role weekly.

### Phase 3 — Measure & Scale (Week 4+)

**Goal:** Measure impact and expand to the wider team.

| Step | Action | Who |
|---|---|---|
| 1 | Fill in the 4-week scorecard | Lead |
| 2 | Review override rate — target 10-25% | Lead + team |
| 3 | Update `prompts/team_standards.md` rubric based on learnings | Team |
| 4 | Present scorecard to leadership | Lead |
| 5 | Expand to adjacent teams if score ≥ 36/60 | Lead |

**Success criteria:** Scorecard total ≥ 36/60 ("Solid adoption with focus areas").

### The Feedback Loop

```
                   ┌──────────┐
                   │ Engineer  │
                   │ writes    │
                   │ code      │
                   └─────┬────┘
                         ▼
              ┌──────────────────┐
              │  ⚖ Judge reviews  │
              │  against rubric   │
              └────────┬─────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      APPROVE    REQUEST_CHANGES   BLOCK
          │            │            │
          │            ▼            ▼
          │     Fix & re-run    Hand to Copilot:
          │     the Judge       "Fix these issues"
          │            │            │
          │            └────────────┘
          │                   │
          ▼                   ▼
    ┌──────────┐       ┌──────────┐
    │  Merge   │       │  Re-run  │
    │          │       │  Judge   │
    └──────────┘       └──────────┘
```

---

## 8. Measuring Success — 4-Week Scorecard

After four weeks of use, copy the table below into a new file (e.g. `scorecard-YYYY-QN.md`) and fill it in.

### The Measure Table

| Dimension | Metric | Baseline | Target | Actual (4 wk) | Score 1-5 |
|---|---|---|---|---|---|
| ⚖ Judge | Critical issues caught pre-merge | ___ | ≥ 5 | ___ | ___ |
| ⚖ Judge | PRs evaluated by Judge | 0 | ≥ 50 | ___ | ___ |
| ⚖ Judge | Hours saved on code review | 0 | ≥ 8 | ___ | ___ |
| ⚖ Judge | Override rate (calibration health) | n/a | 10-25% | ___% | ___ |
| 📐 Advocate | ADRs generated | ___ | ≥ 3 | ___ | ___ |
| 📐 Advocate | Proposals revised after Devil's Advocate | ___ | ≥ 2 | ___ | ___ |
| 📐 Advocate | Hours saved on design-review prep | 0 | ≥ 4 | ___ | ___ |
| 🤝 Mediator | Design conflicts resolved | ___ | ≥ 2 | ___ | ___ |
| 🤝 Mediator | Hours of team stalemate eliminated | 0 | ≥ 6 | ___ | ___ |
| 🤝 Mediator | Agent unblocks (Copilot / Devin / Claude Code) | 0 | ≥ 4 | ___ | ___ |
| Adoption | % of team using ≥ 1 role weekly | 0% | ≥ 70% | ___% | ___ |
| Adoption | Engineers contributing to team_standards.md | 0 | ≥ 3 | ___ | ___ |
| | | | | **TOTAL** | **___ / 60** |

**Scoring:** 5 = significantly exceeded · 4 = met target · 3 = approached (≥70%) · 2 = partial (≥30%) · 1 = no progress

### Headline Interpretation

| Total Score | Recommendation |
|---|---|
| **48-60** | High-impact rollout. Scale to adjacent teams. |
| **36-47** | Solid adoption with focus areas. Continue with improvements. |
| **24-35** | Early signal. Extend the pilot one more cycle. |
| **< 24** | Re-evaluate approach. Interview engineers to understand barriers. |

### Calibration Health — The Override Rate

The override rate is the credibility metric:

- **0% overrides** → Engineers have stopped reading the verdicts. Investigate.
- **80% overrides** → The rubric is wrong for this team. Update `team_standards.md`.
- **10-25% overrides** → Calibrated and engaged. **This is the signal leadership trusts.**

### The Three-Line Story for Your Slide

> *"In 4 weeks, our team caught **[X]** critical issues before merge, generated **[Y]** ADRs in design reviews, and resolved **[Z]** design deadlocks that would otherwise have cost days. Total scorecard: **[N]/60**."*

---

## 9. Appendix

### Connecting Roles to Agent Workflows

After running any role, the output can feed directly into your agent workflow:

| Role Output | Agent Handoff |
|---|---|
| Judge flags issues | → Paste into Copilot: *"Fix these issues: [paste must-fix list]"* |
| ADR generated | → Paste into Devin task brief: *"Implement this ADR: [paste]"* |
| Devil's Advocate → PROCEED | → Safe to hand off to any agent |
| Devil's Advocate → REVISE | → Update proposal first, do not hand off |
| Mediator synthesis agreed | → Paste implementation steps into Copilot / Claude Code session |

### Five Pitfalls the Judgment Layer Catches

| Pitfall | Which Role Catches It |
|---|---|
| **Blind trust** — accepting generated code without reading it | ⚖ Judge |
| **Underprepared decisions** — design choices made without rigour | 📐 Advocate |
| **Team deadlocks** — disputes that stall sprints and agents | 🤝 Mediator |
| **Untested edge cases** — code that only handles the happy path | ⚖ Judge |
| **Missing trade-off analysis** — choosing tech without comparing alternatives | 📐 Advocate |

### File Reference

| File | Purpose |
|---|---|
| `WORKING_PLAN.md` | This document — implementation guide |
| `BeyondTheCode_WhitePaper.docx` | The full whitepaper |
| **Option A — MD Templates** | |
| `prompts/README.md` | Option A guide + quick-copy prompts |
| `prompts/judge-review.md` | Judge template with customisation guide |
| `prompts/advocate-adr.md` | ADR generator template with workflow |
| `prompts/advocate-devil.md` | Devil's Advocate template with gate rule |
| `prompts/mediate-design.md` | Mediator template with agent handoff |
| **Option B — VS Code Extension** | |
| `vscodebase/README.md` | Extension build, install, and usage guide |
| `vscodebase/package.json` | Extension manifest + chat participant registration |
| `vscodebase/src/extension.ts` | Handler registration + LLM interaction |
| `vscodebase/src/prompts.ts` | All baked-in role prompts |
| **Shared** | |
| `prompts/team_standards.md` | Your team's rubric — **edit this** |

### Glossary

| Term | Meaning |
|---|---|
| **ADR** | Architecture Decision Record — a document capturing a design decision, its rationale, and alternatives considered |
| **Judgment Layer** | The combination of Judge, Advocate, and Mediator roles layered on top of AI code-generation tools |
| **Override Rate** | Percentage of Judge verdicts the team disagreed with — the calibration signal for your rubric |
| **Chat Participant** | A VS Code extension API that registers custom `@` commands in Copilot Chat |
| **Rubric** | The team's coding standards used by the Judge to evaluate code (`team_standards.md`) |
| **Verdict** | The Judge's structured output: APPROVE, REQUEST_CHANGES, or BLOCK |
| **Synthesis** | The Mediator's output — a unified path that preserves the best of competing positions |

---

*Engineering Excellence Series · 2025 · Copilotas JAM: Judge, Advocate & Mediator*
