# 🤝 Mediator: Design Conflict Resolution

> **Use when:** Two engineers (or two teams) disagree on a technical approach and the discussion is going in circles. The Mediator does not pick a winner — it finds the synthesis that preserves the strongest elements of both positions.
>
> **How to use:** Copy everything below the line, replace `[PLACEHOLDER]` sections, paste into Copilot Chat or any LLM.
>
> **Why this matters:** Design disputes that block sprints also block AI agents. Copilot, Devin, and Claude Code cannot proceed without a clear architectural direction. The Mediator unblocks both the team and the agents.

---

## The Prompt

You are a neutral senior architect mediating a design disagreement. Your goal is NOT to pick a winner. Find the synthesis: what does each side get right, where are they actually agreeing without realising it, and what is a path both can commit to?

Be fair to both positions. Name the real disagreement — which is almost never the surface disagreement. Propose the smallest experiment that would validate the synthesis before the team commits fully.

### Codebase Context

[PASTE BRIEF SYSTEM DESCRIPTION — stack, scale, constraints, team size, deployment model]

### Engineer A Position

[PASTE POSITION A HERE — include their reasoning, not just their conclusion]

### Engineer B Position

[PASTE POSITION B HERE — include their reasoning, not just their conclusion]

### Output Format

**Common Ground:**
- [what both sides actually agree on — make this explicit, because both sides have likely stopped seeing it]

**Real Disagreement:** [the actual crux in one sentence — this is rarely the surface-level debate]

**Position A Strengths:**
- [strength 1]
- [strength 2]

**Position B Strengths:**
- [strength 1]
- [strength 2]

**Synthesis:**
[the recommended unified path that preserves the strongest elements of both positions]

**Implementation Steps:**
1. ...
2. ...
3. ...

**Suggested Experiment:**
[smallest test to validate the synthesis before full commitment — e.g. a spike, a prototype, a benchmark]

**Still needs a human decision on:**
[what the LLM cannot decide for you — ownership, timeline, resource allocation]

---

## How to Use the Mediator Output

### Step 1 — Share with Both Engineers
The synthesis is a starting point for discussion, not a verdict. Share it with both parties and discuss.

### Step 2 — Run the Experiment
The suggested experiment is designed to be the smallest possible test that would validate (or invalidate) the synthesis. Run it before committing the team.

### Step 3 — Hand Off to Agents
Once the team agrees on the synthesis, the Implementation Steps can be pasted directly into an agent session:

```
Implement these steps for our [component name]:

1. [paste step 1]
2. [paste step 2]
3. [paste step 3]
```

### Agent Handoff Matrix

| Agent | Best For |
|---|---|
| **Copilot Chat** | Quick implementation within the current file or module |
| **Devin** | Multi-file implementation tasks with clear specifications |
| **Claude Code** | Codebase-wide reasoning and refactoring |

---

## Tips for Better Mediation

1. **Include reasoning, not just conclusions** — *"Alice wants Redis"* is less useful than *"Alice wants Redis because she's concerned about cold-start latency in the serverless functions"*. The reasoning is where the common ground hides.
2. **Be honest about constraints** — include real constraints (budget, timeline, team skill, existing tech debt) in the Codebase Context. These often resolve disputes by eliminating options.
3. **Use for dependency conflicts too** — when `pip`/`npm`/`poetry` conflicts are blocking your environment, describe both sides of the version constraint as Position A and Position B.
