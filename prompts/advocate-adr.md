# 📐 Advocate: Generate Architecture Decision Record

> **Use when:** You're proposing a design decision and need a structured document for the review meeting. The ADR gives you a complete first draft with anticipated objections and pre-prepared responses — so by the time you walk into the design review, you've already had the argument.
>
> **How to use:** Copy everything below the line, replace `[PLACEHOLDER]` sections, paste into Copilot Chat or any LLM.
>
> **Recommended workflow:** Run the [Devil's Advocate](advocate-devil.md) first to stress-test your proposal. If the verdict is PROCEED, then generate the ADR.

---

## The Prompt

You are a principal software architect. Write a complete Architecture Decision Record for the proposal below.

Include anticipated review objections with pre-prepared responses — this document will be used in the design review meeting. Be thorough: the engineer using this will face questions from architects, engineering managers, and staff engineers who may prefer the current approach.

### Codebase Context

[PASTE YOUR README OR ARCHITECTURE SUMMARY HERE — include stack, scale, team size, existing patterns]

### Proposal

[DESCRIBE YOUR DESIGN IDEA IN 2-5 SENTENCES]

### Output Format

Write the ADR as a markdown document with these sections:

```markdown
# [Title]

**Status:** Proposed   ·   **Date:** [today]

## Context
[problem background — 3-5 sentences covering what's broken, what's changed, or what opportunity exists]

## Decision
[the chosen approach, clearly stated in 1-2 sentences]

## Rationale
- [reason 1 — why this approach over others]
- [reason 2]
- [reason 3]

## Alternatives Considered

### [Alternative A]
[description in 1-2 sentences]
**Why rejected:** [specific reason]

### [Alternative B]
[description in 1-2 sentences]
**Why rejected:** [specific reason]

## Trade-offs

| Benefit | Cost |
|---|---|
| [what you gain] | [what you give up or accept] |
| ... | ... |

## Consequences
[what changes downstream; what this enables; what this constrains; migration path if applicable]

## Anticipated Objections

| Objection | Response |
|---|---|
| "Why not just [existing approach]?" | [prepared response] |
| "This adds complexity to [area]" | [prepared response] |
| "What about [edge case]?" | [prepared response] |
| ... | ... |
```

---

## After Generating the ADR

1. **Review the ADR yourself** — the LLM's draft is a starting point, not a finished document. Add your own context and judgement.
2. **Take it to your design review** — you now have a structured document with pre-prepared responses to likely objections.
3. **After approval** — hand the ADR to Copilot or Devin for implementation:

```
Implement the architecture described in this ADR: [paste the ADR]
```

---

## The Advocate Workflow

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
3. Generate ADR (this template)
         │
         ▼
4. Review & take to design meeting
         │
         ▼
5. After approval → hand off to Copilot / Devin
```
