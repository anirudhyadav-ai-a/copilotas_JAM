# Team Coding Standards

> This file is the **most important config in the Judgment Layer**.
> Treat it like code: version it, review changes in PR, evolve it.
> Every Judge run reads this rubric.

---

## Code Quality

1. **No function exceeds 40 lines** of executable code (excluding docstrings/comments).
2. **Every public method has a docstring** describing purpose, parameters, and return value.
3. **Cyclomatic complexity ≤ 10** per function — refactor anything more complex.
4. **No magic numbers** — use named constants for any non-zero/non-one literal.
5. **Meaningful variable names** — no single-letter vars outside loops or coordinates.

## Security

6. **No hardcoded credentials, secrets, or API keys** in source.
7. **No fallback secrets** in JWT signing, encryption, or auth flows.
8. **No direct SQL string concatenation** — use parameterised queries / ORM.
9. **All user input must be validated** before reaching business logic.
10. **No `eval()`, `exec()`, or equivalent dynamic execution** of user-supplied data.

## Testing

11. **New logic has at least one unit test** that asserts behaviour, not implementation.
12. **No trivial tests** (`assert True`, mocking the entire system under test).
13. **Edge cases must be tested:** empty input, null, max boundary, negative cases.
14. **Tests must be deterministic** — no time-dependent or order-dependent assertions.

## Architecture

15. **No circular imports** between modules.
16. **No business logic in controllers** — keep route handlers thin.
17. **Public APIs are versioned** — breaking changes require a new version.

## Process

18. **No TODOs in merged code** — convert to tracked tickets before merging.
19. **No commented-out code** — delete it; git remembers.
20. **No `print()` for logging** — use the team's logging framework.

---

## Notes

- **Severity levels:** Items 6-10 (security) and 11-13 (testing) are **error-level** — flag as BLOCK. The rest default to **warn-level** (REQUEST_CHANGES).
- **Customisation:** Edit this file freely. Add team-specific rules. Remove ones that don't fit your stack. The Judge will use whatever rubric you put here.
- **Calibration:** When the Judge consistently flags something the team disagrees with, update this file. When the Judge keeps missing something, add a rule.
