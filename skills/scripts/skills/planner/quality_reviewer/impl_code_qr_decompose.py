#!/usr/bin/env python3
"""QR decomposition for impl-code phase.

INTENT.md requires separate files per phase.
This file contains ONLY impl-code-specific item generation.
Shared logic lives in qr_decompose_base.py.

Impl-code checks:
- Acceptance criteria verification (factored: expectations vs observations)
- Cross-cutting concerns (shared state, error propagation)
- Code quality (all 8 quality documents)
- Intent marker validation
"""

from .qr_decompose_base import DecomposeBase


class ImplCodeDecompose(DecomposeBase):
    """QR decomposition for impl-code phase."""

    PHASE = "impl-code"

    def get_artifact_prompt(self) -> str:
        """Impl-code reads plan.json and modified files from codebase."""
        return """Read plan.json from STATE_DIR:
  cat $STATE_DIR/plan.json | jq '.'

Also read MODIFIED_FILES from codebase (paths from milestones).

Focus on:
  - milestones[].acceptance_criteria
  - Actual implemented code in modified files
  - Code quality (structure, patterns, documentation)"""

    def get_enumeration_guidance(self) -> str:
        """Return phase-specific enumeration guidance for Step 3."""
        return """For impl-code, enumerate:
  - Each milestone with acceptance_criteria (ID, criteria count)
  - Files modified per milestone
  - Cross-cutting concerns mentioned (error handling, logging, etc.)
  - Code quality aspects to verify"""


def get_step_guidance(step: int, total_steps: int, module_path: str = None, **kwargs) -> dict:
    """Entry point for workflow execution."""
    module_path = module_path or "skills.planner.quality_reviewer.impl_code_qr_decompose"
    decomposer = ImplCodeDecompose()
    return decomposer.get_step_guidance(step, total_steps, module_path=module_path, **kwargs)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Impl-Code-Decompose: Generate verification items for implemented code",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
        ],
    )
