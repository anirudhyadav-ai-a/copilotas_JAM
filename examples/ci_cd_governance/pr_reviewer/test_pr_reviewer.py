"""Tests for the PR reviewer pipeline.

Phase 0 | CI/CD Governance — PR Reviewer
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add the pr_reviewer directory to path for direct import
sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    DiffExtractor,
    DiffFile,
    FileFinding,
    FileLevelReviewer,
    FileVerdict,
    RubricLoader,
    VerdictAggregator,
    review_pr,
)

SAMPLE_DIFF = """\
diff --git a/app/auth.py b/app/auth.py
--- a/app/auth.py
+++ b/app/auth.py
@@ -10,6 +10,8 @@ class Auth:
+    API_KEY = "sk-secret123"
+    def validate(self, token):
+        try:
+            return self._decode(token)
+        except:
+            return None
"""

CLEAN_DIFF = """\
diff --git a/app/utils.py b/app/utils.py
--- a/app/utils.py
+++ b/app/utils.py
@@ -1,3 +1,5 @@
+def add(a: int, b: int) -> int:
+    return a + b
"""


# --- DiffExtractor ---


class TestDiffExtractor:
    def test_extract_single_file(self):
        extractor = DiffExtractor()
        files = extractor.extract(SAMPLE_DIFF)
        assert len(files) == 1
        assert files[0].path == "app/auth.py"
        assert files[0].additions > 0

    def test_extract_empty_diff(self):
        extractor = DiffExtractor()
        files = extractor.extract("")
        assert files == []

    def test_extract_multiple_files(self):
        diff_text = SAMPLE_DIFF + "\n" + CLEAN_DIFF
        extractor = DiffExtractor()
        files = extractor.extract(diff_text)
        assert len(files) == 2

    def test_counts_additions_and_deletions(self):
        extractor = DiffExtractor()
        files = extractor.extract(CLEAN_DIFF)
        assert files[0].additions == 2
        assert files[0].deletions == 0


# --- RubricLoader ---


class TestRubricLoader:
    def test_default_rubric(self):
        loader = RubricLoader()
        rubric = loader.load()
        assert "Security" in rubric
        assert "Correctness" in rubric

    def test_file_rubric(self, tmp_path):
        rubric_file = tmp_path / "rubric.md"
        rubric_file.write_text("# Custom Rubric\n- Rule 1")
        loader = RubricLoader(rubric_file)
        assert "Custom Rubric" in loader.load()


# --- FileLevelReviewer ---


class TestFileLevelReviewer:
    @pytest.mark.asyncio
    async def test_detects_hardcoded_secret(self):
        reviewer = FileLevelReviewer("rubric")
        diff_file = DiffFile(
            path="auth.py",
            hunks=['+API_KEY = "sk-secret123"'],
        )
        verdict = await reviewer.review(diff_file)
        assert verdict.verdict == "BLOCK"
        assert any(f.severity == "must-fix" for f in verdict.findings)

    @pytest.mark.asyncio
    async def test_clean_file_passes(self):
        reviewer = FileLevelReviewer("rubric")
        diff_file = DiffFile(
            path="utils.py",
            hunks=["+def add(a, b):\n+    return a + b"],
        )
        verdict = await reviewer.review(diff_file)
        assert verdict.verdict == "PASS"
        assert verdict.score > 9.0

    @pytest.mark.asyncio
    async def test_detects_bare_except(self):
        reviewer = FileLevelReviewer("rubric")
        diff_file = DiffFile(
            path="handler.py",
            hunks=["+try:\n+    do_thing()\n+except:\n+    pass"],
        )
        verdict = await reviewer.review(diff_file)
        assert any(f.category == "correctness" for f in verdict.findings)


# --- VerdictAggregator ---


class TestVerdictAggregator:
    def test_empty_verdicts(self):
        agg = VerdictAggregator()
        result = agg.aggregate([])
        assert result.verdict == "PASS"

    def test_block_propagates(self):
        agg = VerdictAggregator()
        verdicts = [
            FileVerdict(file_path="a.py", verdict="PASS", score=10.0),
            FileVerdict(
                file_path="b.py",
                verdict="BLOCK",
                score=3.0,
                findings=[
                    FileFinding("b.py", 5, "must-fix", "security", "Issue"),
                ],
            ),
        ]
        result = agg.aggregate(verdicts)
        assert result.verdict == "BLOCK"
        assert len(result.must_fix) == 1


# --- Full pipeline ---


class TestReviewPR:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_findings(self):
        result = await review_pr(SAMPLE_DIFF)
        assert result.verdict == "BLOCK"
        assert len(result.must_fix) >= 1

    @pytest.mark.asyncio
    async def test_full_pipeline_clean(self):
        result = await review_pr(CLEAN_DIFF)
        assert result.verdict == "PASS"
