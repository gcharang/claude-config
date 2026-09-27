"""Regression tests for targeted doc/code consistency claims (bug_004 and bug_013
of the 2026-04-17 ultrareview).

These are small, intentional doc checks — not a general doc-lint.
"""

from pathlib import Path

import pytest

from skills.lib.workflow.ast import nodes as ast_nodes

# skills/scripts/tests/ → skills/scripts/
_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def _read(relpath: str) -> str:
    return (_SCRIPTS_ROOT / relpath).read_text()


class TestAstClaudeMdNodeTypes:
    """ast/CLAUDE.md must describe every public node type in nodes.__all__."""

    def test_every_public_node_is_documented(self):
        claude_md = _read("skills/lib/workflow/ast/CLAUDE.md")
        documented_candidates = set(ast_nodes.__all__) - {"Node", "Document"}
        missing = [name for name in documented_candidates if name not in claude_md]
        assert not missing, (
            f"Node types in nodes.__all__ but not mentioned in ast/CLAUDE.md: {missing}"
        )

    def test_false_all_specialized_removed_claim_absent(self):
        """The load-bearing false sentence must not return."""
        claude_md = _read("skills/lib/workflow/ast/CLAUDE.md")
        assert "All specialized nodes (HeaderNode, ActionsNode" not in claude_md


class TestQrReadmeStepCountWording:
    """quality_reviewer/README.md must describe the dynamic step formula."""

    _README = "skills/planner/quality_reviewer/README.md"

    def test_drops_5_step_claim(self):
        assert "5-step verify workflow" not in _read(self._README)

    def test_mentions_dynamic_formula(self):
        text = _read(self._README)
        # Accept either the formula "2 + 2*N" or the word "dynamic" as the
        # load-bearing signal that the claim has been corrected.
        assert ("2 + 2*N" in text) or ("dynamic" in text.lower()), (
            "QR README must describe the step count as dynamic (formula 2 + 2*N)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
