"""Reusable constraint strings for planner orchestration.

Constants for static constraints, functions for parameterized output.
"""

ORCHESTRATOR_CONSTRAINT = (
    "You are the ORCHESTRATOR. You delegate, you never implement.\n"
    "PROHIBITED: Read, Edit, Write tools. REQUIRED: Task tool dispatch only."
)

ORCHESTRATOR_CONSTRAINT_EXTENDED = (
    ORCHESTRATOR_CONSTRAINT + "\n"
    "\n"
    "SCRIPT-MODE DISPATCH: give each sub-agent only what this step prints for it (its Task\n"
    "line and invoke block), plus the <user_response> when relaying an answer. Add no task\n"
    "descriptions, goals, or context of your own: the script gives the sub-agent its instructions."
)


def format_state_banner(checkpoint: str, iteration: int, mode: str) -> str:
    """QR state context banner.

    WHY needed: Fix/review steps need workflow position context. LLM sees
    which phase, iteration count (for convergence tracking), and mode.
    """
    return f"STATE: {checkpoint} | iteration={iteration} | mode={mode}"
