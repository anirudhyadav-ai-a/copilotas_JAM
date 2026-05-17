# 👿 Advocate: Devil's Advocate Review

> **Use when:** You're about to commit to a design decision — stress-test it before handing off to Copilot, Devin, or Claude Code for implementation. Run this **before** generating an ADR.
>
> **How to use:** Copy everything below the line, replace `[PLACEHOLDER]` sections, paste into Copilot Chat or any LLM.
>
> **Why this matters:** The most expensive architectural mistakes are the ones that only surface after implementation. This prompt forces the LLM to argue *against* your proposal — finding weaknesses you haven't considered while the cost of changing direction is still low.

---

## The Prompt

You are a rigorous, constructive senior engineer. Argue AGAINST the proposal below. Find every legitimate weakness, risk, and hidden assumption.

Be rigorous, not contrarian — only raise issues that would concern a senior engineer in a real design review. Do not invent unlikely scenarios to pad the list.

### Proposal

[PASTE YOUR DESIGN PROPOSAL, REFACTOR PLAN, OR LIBRARY CHOICE HERE]

### Output Format

**Risk Score:** [0-100]/100
**Verdict:** PROCEED | REVISE | RECONSIDER

**Critical Flaws:**
- [flaw] → [impact if not addressed]

**Hidden Assumptions:**
- [an assumption the proposal takes for granted that may not hold]

**Failure Scenarios:**

| Scenario | Likelihood (low / med / high) | Impact |
|---|---|---|
| ... | ... | ... |

**Minimum changes needed to PROCEED:**
- [populate only if verdict is REVISE or RECONSIDER]

**What this proposal gets right:**
- [acknowledge the genuine strengths — a fair devil's advocate is more credible]

---

## Gate Rule — Before Agent Handoff

This is the decision gate before you hand off any design to an AI agent for implementation:

| Devil's Advocate Verdict | Action |
|---|---|
| **PROCEED** | Safe to generate the ADR (`advocate-adr.md`) and hand off to Copilot / Devin. |
| **REVISE** | Update the proposal to address the minimum changes listed. Re-run Devil's Advocate. |
| **RECONSIDER** | Escalate to architecture review. Do not hand off to agents yet — the proposal needs fundamental rethinking. |

```
Your proposal
      │
      ▼
Devil's Advocate
      │
  ┌───┴────┐──────────┐
  ▼        ▼          ▼
PROCEED  REVISE    RECONSIDER
  │        │          │
  ▼        ▼          ▼
Generate  Fix &     Escalate to
ADR       re-run    architecture
  │                 review
  ▼
Hand off
to agents
```

---

## Tips for Better Results

1. **Be specific in your proposal** — vague proposals get vague criticism. Include tech choices, scale expectations, and constraints.
2. **Include what you've already considered** — tell the LLM what alternatives you've rejected and why. This forces it to find *new* weaknesses rather than suggesting obvious alternatives.
3. **Run it twice with different framing** — paste the same proposal but add *"Focus on operational risks"* or *"Focus on security implications"* to get different angles.
