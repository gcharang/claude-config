#!/usr/bin/env python3
"""QR decomposition for impl-docs phase.

INTENT.md requires separate files per phase.
This file contains ONLY impl-docs-specific item generation.
Shared logic lives in qr_decompose_base.py.

Impl-docs checks:
- CLAUDE.md format (tabular index)
- IK proximity audit (docs adjacent to code)
- Temporal contamination in comments
- README.md creation criteria
"""

from .qr_decompose_base import DecomposeBase


class ImplDocsDecompose(DecomposeBase):
    """QR decomposition for impl-docs phase."""

    PHASE = "impl-docs"

    def get_artifact_prompt(self) -> str:
        """Impl-docs reads plan.json, CLAUDE.md files, and README.md files."""
        return """Read plan.json from STATE_DIR:
  cat $STATE_DIR/plan.json | jq '.'

Also read documentation files in modified directories:
  - CLAUDE.md files
  - README.md files
  - Comments in source files

Focus on:
  - invisible_knowledge section
  - Modified directory list
  - CLAUDE.md format compliance"""

    def get_enumeration_guidance(self) -> str:
        """Return phase-specific enumeration guidance for Step 3."""
        return """For impl-docs, enumerate:
  - Each directory with modified files (directory path)
  - Each CLAUDE.md file that should exist (path)
  - Each README.md file that should exist (path)
  - Each invisible_knowledge item (count, topics)"""


def get_step_guidance(step: int, total_steps: int, module_path: str = None, **kwargs) -> dict:
    """Entry point for workflow execution."""
    module_path = module_path or "skills.planner.quality_reviewer.impl_docs_qr_decompose"
    decomposer = ImplDocsDecompose()
    return decomposer.get_step_guidance(step, total_steps, module_path=module_path, **kwargs)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Impl-Docs-Decompose: Generate verification items for post-impl documentation",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
        ],
    )
