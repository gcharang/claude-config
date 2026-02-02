#!/usr/bin/env python3
"""QR decomposition for plan-code phase.

INTENT.md requires separate files per phase.
This file contains ONLY plan-code-specific item generation.
Shared logic lives in qr_decompose_base.py.

Plan-code checks:
- Context line verification (diff context matches codebase)
- Diff format validation (RULE 0/1/2 compliance)
- Intent linkage (every code_intent has code_change)
- WHY comment decision_refs validity
"""

from .qr_decompose_base import DecomposeBase, TOTAL_STEPS


class PlanCodeDecompose(DecomposeBase):
    """QR decomposition for plan-code phase."""

    PHASE = "plan-code"

    def get_artifact_prompt(self) -> str:
        """Plan-code reads plan.json with focus on code_changes."""
        return """Read plan.json from STATE_DIR:
  cat $STATE_DIR/plan.json | jq '.'

Focus on:
  - milestones[].code_intents[]
  - milestones[].code_changes[]
  - code_changes[].diff (context lines, format)
  - code_changes[].why_comments[].decision_ref"""

    def get_enumeration_guidance(self) -> str:
        """Return phase-specific enumeration guidance for Step 3."""
        return """For plan-code, enumerate:
  - Each milestone's code_changes (milestone ID, count of changes)
  - For each code_change: ID, file path, has intent_ref?, has comments?
  - Files touched across all changes
  - Intent-to-change mapping (which intents have changes)"""


def get_step_guidance(step: int, module_path: str, **kwargs) -> dict:
    """Entry point for workflow execution."""
    decomposer = PlanCodeDecompose()
    return decomposer.get_step_guidance(step, TOTAL_STEPS, module_path=module_path, **kwargs)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Plan-Code-Decompose: Generate verification items for code changes",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
        ],
    )
