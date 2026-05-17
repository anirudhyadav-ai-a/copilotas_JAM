"""
CI/CD Governance — Example 1: PR Reviewer

Demonstrates:
  - Extracting changed files + hunks from a git diff
  - Loading rubric from a Markdown file (with org fallback)
  - Running the Judge on each changed file in parallel (asyncio.gather)
  - Aggregating per-file verdicts into a single PR-level verdict

Run:
    python -m copilotas_JAM.examples.ci_cd_governance.pr_reviewer.main [DIFF_FILE]

Prerequisites:
    OPENAI_API_KEY or ANTHROPIC_API_KEY set in .env
"""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DiffFile:
    """A single file extracted from a git diff."""

    path: str
    hunks: list[str]
    additions: int = 0
    deletions: int = 0


@dataclass
class FileFinding:
    """A single finding from reviewing a file."""

    file_path: str
    line: int | None
    severity: str  # "info", "warning", "must-fix", "block"
    category: str  # "security", "correctness", "style", "performance"
    description: str


@dataclass
class FileVerdict:
    """The result of reviewing a single file."""

    file_path: str
    verdict: str  # "PASS", "WARN", "BLOCK"
    score: float  # 0.0 - 10.0
    findings: list[FileFinding] = field(default_factory=list)


@dataclass
class PRVerdict:
    """Aggregated verdict for the entire PR."""

    verdict: str  # "PASS", "WARN", "BLOCK"
    score: float
    file_verdicts: list[FileVerdict] = field(default_factory=list)
    must_fix: list[FileFinding] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Diff extraction
# ---------------------------------------------------------------------------


class DiffExtractor:
    """Parse a unified diff into DiffFile objects."""

    _FILE_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
    _HUNK_HEADER = re.compile(r"^@@.*@@")

    def extract(self, diff_text: str) -> list[DiffFile]:
        """Parse unified diff text into a list of DiffFile objects."""
        files: list[DiffFile] = []
        current: DiffFile | None = None
        current_hunk_lines: list[str] = []

        for line in diff_text.splitlines():
            file_match = self._FILE_HEADER.match(line)
            if file_match:
                if current and current_hunk_lines:
                    current.hunks.append("\n".join(current_hunk_lines))
                current = DiffFile(path=file_match.group(2), hunks=[])
                current_hunk_lines = []
                files.append(current)
                continue

            if current is None:
                continue

            if self._HUNK_HEADER.match(line):
                if current_hunk_lines:
                    current.hunks.append("\n".join(current_hunk_lines))
                current_hunk_lines = [line]
                continue

            current_hunk_lines.append(line)
            if line.startswith("+") and not line.startswith("+++"):
                current.additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                current.deletions += 1

        if current and current_hunk_lines:
            current.hunks.append("\n".join(current_hunk_lines))

        return files


# ---------------------------------------------------------------------------
# Rubric loader
# ---------------------------------------------------------------------------

DEFAULT_RUBRIC = """\
# Judge Rubric

## Security
- No hardcoded secrets or API keys
- No SQL injection or command injection vectors
- Input validation on user-facing parameters

## Correctness
- No off-by-one errors
- Null/None checks before dereference
- Error handling covers expected failure modes

## Style
- Consistent naming conventions
- No unused imports or dead code
- Docstrings on public functions

## Performance
- No unnecessary allocations in hot loops
- Avoid N+1 query patterns
- Use appropriate data structures
"""


class RubricLoader:
    """Load a review rubric from a Markdown file."""

    def __init__(self, rubric_path: Path | None = None) -> None:
        self._rubric_path = rubric_path

    def load(self) -> str:
        """Load rubric from file, or return the default rubric."""
        if self._rubric_path and self._rubric_path.exists():
            return self._rubric_path.read_text()
        return DEFAULT_RUBRIC


# ---------------------------------------------------------------------------
# File-level reviewer (mock LLM — no API key required for demo)
# ---------------------------------------------------------------------------


class FileLevelReviewer:
    """Review a single file's diff against a rubric.

    This demo uses heuristic pattern matching instead of an LLM call
    so it runs without API keys. In production, replace the `_review`
    method with an LLM call using the rubric as the system prompt.
    """

    _PATTERNS: list[tuple[str, str, str, str]] = [
        # (regex, severity, category, description)
        (
            r"(?i)\b(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]",
            "must-fix",
            "security",
            "Possible hardcoded secret",
        ),
        (
            r"\beval\s*\(",
            "warning",
            "security",
            "Use of eval() — consider ast.literal_eval or a safe parser",
        ),
        (
            r"except\s*:",
            "warning",
            "correctness",
            "Bare except clause — catch specific exceptions",
        ),
        (
            r"except\s+Exception\s*:",
            "info",
            "correctness",
            "Broad exception catch — consider narrowing",
        ),
        (r"# ?TODO", "info", "style", "Unresolved TODO comment"),
        (r"import \*", "warning", "style", "Wildcard import — import specific names"),
        (
            r"\.execute\([^)]*%s",
            "must-fix",
            "security",
            "SQL string interpolation — use parameterized queries",
        ),
        (
            r"os\.system\(",
            "warning",
            "security",
            "os.system() — use subprocess.run with shell=False",
        ),
    ]

    def __init__(self, rubric: str) -> None:
        self._rubric = rubric

    async def review(self, diff_file: DiffFile) -> FileVerdict:
        """Review a single file and return a verdict."""
        findings: list[FileFinding] = []
        # Only scan added lines — ignore deletions and context lines.
        added_lines: list[str] = []
        for hunk in diff_file.hunks:
            for line in hunk.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    added_lines.append(line[1:])
        full_text = "\n".join(added_lines)

        for pattern, severity, category, description in self._PATTERNS:
            for match in re.finditer(pattern, full_text):
                line_num = full_text[: match.start()].count("\n") + 1
                findings.append(
                    FileFinding(
                        file_path=diff_file.path,
                        line=line_num,
                        severity=severity,
                        category=category,
                        description=description,
                    )
                )

        has_block = any(f.severity == "block" for f in findings)
        has_must_fix = any(f.severity == "must-fix" for f in findings)
        has_warning = any(f.severity == "warning" for f in findings)

        if has_block or has_must_fix:
            verdict = "BLOCK"
            score = max(
                0.0,
                5.0 - len([f for f in findings if f.severity in ("block", "must-fix")]),
            )
        elif has_warning:
            verdict = "WARN"
            score = max(
                5.0, 8.0 - len([f for f in findings if f.severity == "warning"]) * 0.5
            )
        else:
            verdict = "PASS"
            score = 10.0 - len([f for f in findings if f.severity == "info"]) * 0.2

        return FileVerdict(
            file_path=diff_file.path,
            verdict=verdict,
            score=max(0.0, min(10.0, score)),
            findings=findings,
        )


# ---------------------------------------------------------------------------
# Verdict aggregator
# ---------------------------------------------------------------------------


class VerdictAggregator:
    """Aggregate per-file verdicts into a single PR verdict."""

    def aggregate(self, file_verdicts: list[FileVerdict]) -> PRVerdict:
        """Produce a PR-level verdict from file verdicts."""
        if not file_verdicts:
            return PRVerdict(verdict="PASS", score=10.0, summary="No files to review.")

        any_block = any(v.verdict == "BLOCK" for v in file_verdicts)
        any_warn = any(v.verdict == "WARN" for v in file_verdicts)

        avg_score = sum(v.score for v in file_verdicts) / len(file_verdicts)

        must_fix = []
        for v in file_verdicts:
            must_fix.extend(
                f for f in v.findings if f.severity in ("must-fix", "block")
            )

        if any_block:
            verdict = "BLOCK"
        elif any_warn:
            verdict = "WARN"
        else:
            verdict = "PASS"

        summary_lines = [
            f"Reviewed {len(file_verdicts)} file(s) — verdict: **{verdict}** (score: {avg_score:.1f}/10)"
        ]
        if must_fix:
            summary_lines.append(f"\n{len(must_fix)} must-fix finding(s):")
            for f in must_fix:
                summary_lines.append(
                    f"  - [{f.severity}] {f.file_path}:{f.line} — {f.description}"
                )

        return PRVerdict(
            verdict=verdict,
            score=avg_score,
            file_verdicts=file_verdicts,
            must_fix=must_fix,
            summary="\n".join(summary_lines),
        )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def review_pr(diff_text: str, rubric_path: Path | None = None) -> PRVerdict:
    """Run the full PR review pipeline."""
    extractor = DiffExtractor()
    diff_files = extractor.extract(diff_text)

    if not diff_files:
        return PRVerdict(
            verdict="PASS", score=10.0, summary="No changed files found in diff."
        )

    rubric = RubricLoader(rubric_path).load()
    reviewer = FileLevelReviewer(rubric)

    # Review all files in parallel
    file_verdicts = await asyncio.gather(*(reviewer.review(df) for df in diff_files))

    aggregator = VerdictAggregator()
    return aggregator.aggregate(list(file_verdicts))


async def main() -> None:
    """Demo: review a sample diff."""
    if len(sys.argv) > 1:
        diff_path = Path(sys.argv[1])
        if not diff_path.exists():
            print(f"File not found: {diff_path}")
            return
        diff_text = diff_path.read_text()
    else:
        # Sample diff for demonstration
        diff_text = """\
diff --git a/app/auth.py b/app/auth.py
--- a/app/auth.py
+++ b/app/auth.py
@@ -10,6 +10,12 @@ class Auth:
+    API_KEY = "sk-secret123"  # hardcoded secret
+
+    def validate(self, token):
+        try:
+            return self._decode(token)
+        except:
+            return None

diff --git a/app/db.py b/app/db.py
--- a/app/db.py
+++ b/app/db.py
@@ -5,3 +5,6 @@ class DB:
+    def query(self, user_input):
+        sql = "SELECT * FROM users WHERE name = '%s'" % user_input
+        return self.conn.execute(sql)
"""

    pr_verdict = await review_pr(diff_text)
    print(pr_verdict.summary)
    print(f"\nOverall: {pr_verdict.verdict} ({pr_verdict.score:.1f}/10)")

    if pr_verdict.file_verdicts:
        print("\nPer-file breakdown:")
        for fv in pr_verdict.file_verdicts:
            print(f"  {fv.file_path}: {fv.verdict} ({fv.score:.1f})")
            for finding in fv.findings:
                print(
                    f"    [{finding.severity}] L{finding.line}: {finding.description}"
                )


if __name__ == "__main__":
    asyncio.run(main())
