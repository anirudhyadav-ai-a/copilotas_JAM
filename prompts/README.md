# Option A — Markdown Prompt Templates

> Zero setup. Copy a template, customise the `[PLACEHOLDER]` sections, paste into Copilot Chat or any LLM. Fully customisable — edit the prompts to fit your team's standards.

---

## 📋 Templates

| File | Role | Use When... |
|---|---|---|
| [`judge-review.md`](judge-review.md) | ⚖ Judge | You want a structured code review with a verdict (APPROVE / REQUEST_CHANGES / BLOCK) |
| [`advocate-adr.md`](advocate-adr.md) | 📐 Advocate | You need an Architecture Decision Record for a design review |
| [`advocate-devil.md`](advocate-devil.md) | 👿 Advocate | You want to stress-test a proposal before committing to it |
| [`mediate-design.md`](mediate-design.md) | 🤝 Mediator | Two engineers disagree and the team is stuck |
| [`team_standards.md`](team_standards.md) | Shared | Your team's coding rubric — **edit this** for your stack |

---

## 🚀 How to Use

1. **Open** the relevant template (Judge / Advocate / Mediator).
2. **Copy** it. Replace every `[PLACEHOLDER]` section with your actual code, proposal, or context.
3. **Paste** into Copilot Chat, Claude Code, Devin, or any LLM interface and send.

That's it. No API keys. No setup. No tooling.

Each template file includes:
- **The prompt** itself (copy-paste ready)
- **Customisation guide** — how to tailor the prompt for your stack
- **Verdict actions** — what to do with each possible output
- **Agent handoff** — how to feed the output into Copilot / Devin / Claude Code

---

## 🎯 Sharing with Your Team

Drop this `prompts/` folder into the root of your team's repo. Engineers reference templates via `prompts/judge-review.md`.

---

## 🔄 Recommended Workflow

```
1. Start with the Judge
   Run judge-review.md on your next PR.
   See if the verdict catches something useful.
         │
         ▼
2. Try the Advocate before your next design review
   Run advocate-devil.md to stress-test your proposal.
   If PROCEED → run advocate-adr.md to generate the ADR.
         │
         ▼
3. Use the Mediator when a disagreement stalls progress
   Run mediate-design.md with both positions.
   Share the synthesis with the team.
         │
         ▼
4. Measure after 4 weeks
   Use the scorecard in WORKING_PLAN.md Section 8.
   Present the score to leadership.
```

---

## Quick-Copy Prompts

> Below are condensed versions of each template for quick copy-paste. For full guidance (customisation tips, verdict actions, agent handoff), see the individual template files linked above.

### ⚖ Judge: Code Review

```markdown
# Judge: Code Review

You are a senior code reviewer acting as an impartial judge.
Evaluate the code below against the rubric and return a structured verdict.

Do not just check syntax — ask whether the logic is sound, whether tests
actually validate behaviour, whether security patterns are violated, and
whether the code introduces technical debt.

## Rubric

**Code Quality**
- No function exceeds 40 lines of executable code
- Every public method has a docstring
- Cyclomatic complexity ≤ 10 per function
- No magic numbers — use named constants
- Meaningful variable names — no single-letter vars outside loops

**Security**
- No hardcoded credentials, secrets, or API keys
- No fallback secrets in JWT signing or auth flows
- No direct SQL string concatenation — use parameterised queries
- All user input validated before reaching business logic
- No eval() or exec() on user-supplied data

**Testing**
- New logic has at least one unit test asserting behaviour
- No trivial tests (assert True, full-system mocks)
- Edge cases tested: empty input, null, boundaries

**Architecture**
- No circular imports
- No business logic in controllers

[ADD YOUR OWN TEAM STANDARDS HERE]

## Code to Review

\`\`\`
[PASTE YOUR CODE OR GIT DIFF HERE]
\`\`\`

## Output Format

**VERDICT:** APPROVE | REQUEST_CHANGES | BLOCK
**Score:** [0-100]/100
**Summary:** [one sentence]

**Checks:**

| Check | Status | Severity | Comment |
|---|---|---|---|
| ... | PASS / FAIL | info / warn / error | ... |

**Must fix before merge:**
- [only populate if BLOCK or REQUEST_CHANGES]

**Suggested Copilot follow-up:**
- [if BLOCK: suggest a Copilot command to fix the issues]
```

**Verdict actions:** APPROVE → merge. REQUEST_CHANGES → fix & re-run. BLOCK → fix critical issues, then hand off to Copilot: *"Fix these issues: [paste]"*.

---

### 📐 Advocate: Generate ADR

```markdown
# Advocate: Generate Architecture Decision Record

You are a principal software architect. Write a complete ADR for the
proposal below. Include anticipated review objections with pre-prepared
responses — this document will be used in the design review meeting.

Be thorough: the engineer using this will face questions from architects,
engineering managers, and staff engineers who may prefer the current approach.

## Codebase Context

[PASTE YOUR README OR ARCHITECTURE SUMMARY HERE — include stack, scale, team size]

## Proposal

[DESCRIBE YOUR DESIGN IDEA IN 2-5 SENTENCES]

## Output Format — write the ADR as markdown:

# [Title]
**Status:** Proposed   ·   **Date:** [today]

## Context
[problem background — 3-5 sentences]

## Decision
[the chosen approach, clearly stated]

## Rationale
- [reason 1]
- [reason 2]
- [reason 3]

## Alternatives Considered
### [Alternative A]
[description] · **Why rejected:** [reason]
### [Alternative B]
[description] · **Why rejected:** [reason]

## Trade-offs
| Benefit | Cost |
|---|---|
| ... | ... |

## Consequences
[what changes; what this enables; what this constrains]

## Anticipated Objections
| Objection | Response |
|---|---|
| ... | ... |
```

**After generating:** Review the ADR → take to design review → after approval, hand to Copilot/Devin: *"Implement this ADR: [paste]"*.

---

### 👿 Advocate: Devil's Advocate

```markdown
# Advocate: Devil's Advocate Review

You are a rigorous, constructive senior engineer. Argue AGAINST
the proposal below. Find every legitimate weakness, risk, and
hidden assumption. Be rigorous, not contrarian — only raise issues
that would concern a senior engineer in a real design review.

## Proposal

[PASTE YOUR DESIGN PROPOSAL, REFACTOR PLAN, OR LIBRARY CHOICE HERE]

## Output Format

**Risk Score:** [0-100]/100
**Verdict:** PROCEED | REVISE | RECONSIDER

**Critical Flaws:**
- [flaw] → [impact if not addressed]

**Hidden Assumptions:**
- [assumption that may not hold]

**Failure Scenarios:**
| Scenario | Likelihood (low / med / high) | Impact |
|---|---|---|
| ... | ... | ... |

**Minimum changes needed to PROCEED:**
- [only if verdict is REVISE or RECONSIDER]

**What this proposal gets right:**
- [acknowledge genuine strengths]
```

**Gate rule:** PROCEED → safe to generate ADR and hand off. REVISE → fix & re-run. RECONSIDER → escalate to architecture review, do not hand off to agents.

---

### 🤝 Mediator: Design Conflict

```markdown
# Mediator: Design Conflict Resolution

You are a neutral senior architect mediating a design disagreement.
Your goal is NOT to pick a winner. Find the synthesis that
preserves the strongest elements of both positions.

Be fair to both positions. Name the real disagreement — which is
almost never the surface disagreement.

## Codebase Context

[PASTE BRIEF SYSTEM DESCRIPTION — stack, scale, constraints]

## Engineer A Position

[PASTE POSITION A HERE — include their reasoning, not just conclusion]

## Engineer B Position

[PASTE POSITION B HERE — include their reasoning, not just conclusion]

## Output Format

**Common Ground:**
- [what both sides actually agree on]

**Real Disagreement:** [the actual crux in one sentence]

**Position A Strengths:**
- [strength 1]
- [strength 2]

**Position B Strengths:**
- [strength 1]
- [strength 2]

**Synthesis:**
[the recommended unified path]

**Implementation Steps:**
1. ...

**Suggested Experiment:** [smallest test to validate the synthesis]

**Still needs a human decision on:** [what the LLM cannot decide]
```

**After mediation:** Share synthesis with both engineers → run the experiment → once agreed, paste Implementation Steps into Copilot / Devin / Claude Code.

---

## 🔁 Connecting Roles to Agent Workflows

| Role Output | Agent Handoff |
|---|---|
| **Judge** flags issues | → Copilot: *"Fix these issues: [paste must-fix list]"* |
| **ADR** generated | → Devin: *"Implement the architecture in this ADR: [paste]"* |
| **Devil's Advocate** → PROCEED | → Safe to hand off to any agent |
| **Devil's Advocate** → REVISE | → Update proposal first, do not hand off |
| **Mediator** synthesis agreed | → Paste Implementation Steps into Copilot / Claude Code session |

---

## ⚡ Option A vs Option B

| | Option A (these templates) | Option B (VS Code Extension) |
|---|---|---|
| **Setup** | Zero | 10-15 min install |
| **Customisable prompts** | Yes — edit freely | No — prompts baked in |
| **UX** | Copy/paste | `@judge` / `@advocate` / `@mediator` in Copilot Chat |
| **Best for** | Evaluation, custom workflows | Daily use, consistent team experience |

**Recommendation:** Start with Option A to validate the concept. Graduate to Option B for a frictionless daily workflow. See [`WORKING_PLAN.md`](../WORKING_PLAN.md) for the full rollout guide.
