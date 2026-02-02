#!/usr/bin/env python3
"""QR decomposition for plan-docs phase.

INTENT.md requires separate files per phase.
This file contains ONLY plan-docs-specific item generation.
Shared logic lives in qr_decompose_base.py.

Plan-docs checks:
- Documentation completeness (Tiers 3-6)
- WHY comment decision_ref validity
- Temporal contamination in ALL string fields
- Translation faithfulness (plan.json vs plan.md)
"""

from .qr_decompose_base import DecomposeBase, TOTAL_STEPS


class PlanDocsDecompose(DecomposeBase):
    """QR decomposition for plan-docs phase."""

    PHASE = "plan-docs"

    def get_artifact_prompt(self) -> str:
        """Plan-docs reads plan.json and plan.md for translation verification."""
        return """Read plan.json from STATE_DIR:
  cat $STATE_DIR/plan.json | jq '.'

Also read plan.md if it exists:
  cat $STATE_DIR/plan.md

Focus on:
  - milestones[].documentation{}
  - milestones[].code_changes[].comments
  - planning_context.decisions[]
  - readme_entries[]
  - ALL string fields (temporal contamination)"""

    def get_enumeration_guidance(self) -> str:
        """Return phase-specific enumeration guidance for Step 3."""
        return """For plan-docs, enumerate:
  - Each milestone's documentation section (ID, section count)
  - Each code_change with comments (ID, comment count)
  - Each decision_log entry (ID, has reasoning?)
  - readme_entries[] (path, content length)
  - All string fields in plan.json (for contamination scan)"""


def get_step_guidance(step: int, module_path: str, **kwargs) -> dict:
    """Entry point for workflow execution."""
    decomposer = PlanDocsDecompose()
    return decomposer.get_step_guidance(step, TOTAL_STEPS, module_path=module_path, **kwargs)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Plan-Docs-Decompose: Generate verification items for documentation completeness",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
        ],
    )
