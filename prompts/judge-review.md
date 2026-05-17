# ⚖ Judge: Code Review

> **Use when:** You want a structured review of any file, PR diff, or code snippet — whether authored by a human, Copilot, Devin, or Claude Code.
>
> **How to use:** Copy everything below the line, replace `[PLACEHOLDER]` sections, paste into Copilot Chat or any LLM.

---

## The Prompt

You are a senior code reviewer acting as an impartial judge.
Evaluate the code below against the rubric and return a structured verdict.

Do not just check syntax — ask whether the logic is sound, whether tests actually validate behaviour, whether security patterns are violated, and whether the code introduces technical debt.

### Rubric

**Code Quality**
- No function exceeds 40 lines of executable code (excluding docstrings/comments)
- Every public method has a docstring describing purpose, parameters, and return value
- Cyclomatic complexity ≤ 10 per function — refactor anything more complex
- No magic numbers — use named constants for any non-zero/non-one literal
- Meaningful variable names — no single-letter vars outside loops or coordinates

**Security**
- No hardcoded credentials, secrets, or API keys in source
- No fallback secrets in JWT signing, encryption, or auth flows
- No direct SQL string concatenation — use parameterised queries / ORM
- All user input must be validated before reaching business logic
- No `eval()`, `exec()`, or equivalent dynamic execution of user-supplied data

**Testing**
- New logic has at least one unit test that asserts behaviour, not implementation
- No trivial tests (`assert True`, mocking the entire system under test)
- Edge cases must be tested: empty input, null, max boundary, negative cases

**Architecture**
- No circular imports between modules
- No business logic in controllers — keep route handlers thin

[ADD YOUR OWN TEAM STANDARDS HERE — see customisation guide below]

### Code to Review

```
[PASTE YOUR CODE OR GIT DIFF HERE]
```

### Output Format

**VERDICT:** APPROVE | REQUEST_CHANGES | BLOCK
**Score:** [0-100]/100
**Summary:** [one sentence]

**Checks:**

| Check | Status | Severity | Comment |
|---|---|---|---|
| ... | PASS / FAIL | info / warn / error | ... |

**Must fix before merge:**
- [list — only populate this if verdict is BLOCK or REQUEST_CHANGES]

**Suggested Copilot follow-up:**
- [if BLOCK: suggest a Copilot command to fix the issues, e.g. "Fix the hardcoded secret on line 42 by reading from environment variables"]

---

## Customising the Rubric

The rubric is the most important section. Customise it for your team's stack:

| Your Stack | Add to Rubric |
|---|---|
| React / TypeScript | `- No \`any\` types — use proper interfaces` |
| Python / FastAPI | `- All endpoints have Pydantic request/response models` |
| Java / Spring | `- No \`@Autowired\` on fields — use constructor injection` |
| Go | `- All errors are handled — no blank \`_\` for error returns` |
| Node.js / Express | `- All async route handlers have error middleware` |
| Security-sensitive | `- All auth checks happen in middleware, not in handlers` |

**Tip:** Maintain your team's rubric in a shared file (`team_standards.md`). When the Judge consistently flags something the team disagrees with, update the rubric. When it keeps missing something, add a rule.

---

## What to Do with the Verdict

| Verdict | Action |
|---|---|
| **APPROVE** | Safe to merge. Record the score for calibration tracking. |
| **REQUEST_CHANGES** | Fix the listed issues, then re-run the Judge to verify. |
| **BLOCK** | Do not merge. Fix critical issues first. Hand off to Copilot: *"Fix these issues: [paste must-fix list]"* |

---

## Severity Levels

| Severity | Meaning | Default Rubric Items |
|---|---|---|
| **error** | Merge blocker — triggers BLOCK verdict | Security rules, critical testing gaps |
| **warn** | Should fix — triggers REQUEST_CHANGES | Code quality, architecture rules |
| **info** | Observation — does not affect verdict | Style suggestions, minor improvements |
