#!/usr/bin/env python3
"""QR decomposition for plan-design phase.

INTENT.md requires separate files per phase.
This file contains ONLY plan-design-specific item generation.
Shared logic lives in qr_decompose_base.py.

Plan-design checks:
- Decision log completeness (all non-obvious elements documented)
- Policy default verification (user-specified backing required)
- Milestone structure (code_intents present)
- Reference integrity (decision_refs valid)
"""

from .qr_decompose_base import DecomposeBase, TOTAL_STEPS


class PlanDesignDecompose(DecomposeBase):
    """QR decomposition for plan-design phase."""

    PHASE = "plan-design"

    def get_artifact_prompt(self) -> str:
        """Plan-design reads plan.json with focus on planning_context and milestones."""
        return """Read plan.json from STATE_DIR:
  cat $STATE_DIR/plan.json | jq '.'

Focus on:
  - planning_context.decisions
  - planning_context.constraints
  - planning_context.risks
  - milestones[].code_intents
  - invisible_knowledge"""

    def get_enumeration_guidance(self) -> str:
        """Return phase-specific enumeration guidance for Step 3."""
        return """For plan-design, enumerate:
  - Each decision in planning_context.decisions (ID, decision text)
  - Each constraint in planning_context.constraints (ID, type)
  - Each risk in planning_context.risks (ID, risk text)
  - Each milestone (ID, name, count of code_intents)
  - Each code_intent with decision_refs (ID, which decisions referenced)"""


def get_step_guidance(step: int, module_path: str, **kwargs) -> dict:
    """Entry point for workflow execution."""
    decomposer = PlanDesignDecompose()
    return decomposer.get_step_guidance(step, TOTAL_STEPS, module_path=module_path, **kwargs)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Plan-Design-Decompose: Generate verification items for plan completeness",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
        ],
    )
