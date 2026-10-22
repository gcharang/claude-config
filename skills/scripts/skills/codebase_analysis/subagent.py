#!/usr/bin/env python3
"""
Codebase Analysis Explore - Focus-area exploration for codebase understanding.

Note: The focus area is NOT a CLI argument. The orchestrator provides focus
in the subagent's launching prompt. This script emits guidance that refers
to "the focus area" -- the agent knows what it is from its prompt context.
"""

import argparse
import sys

from skills.lib.workflow.prompts import format_step

# ============================================================================
# CONFIGURATION
# ============================================================================

MODULE_PATH = "skills.codebase_analysis.subagent"
TOTAL_STEPS = 2


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: EXPLORE --------------------------------------------------------

EXPLORE_INSTRUCTIONS = (
    "EXPLORE - Build an understanding of your focus area (named in your launching prompt).\n"
    "\n"
    "Find its entry points with Glob/Grep on the focus area's terms, read the key files, and\n"
    "trace imports, calls and data flow until you can say how the main components work and why\n"
    "they are built that way. Note what stays unclear. If nothing matches the focus area, say so."
)

# --- STEP 2: REPORT ---------------------------------------------------------

REPORT_INSTRUCTIONS = (
    "REPORT - Synthesize findings into structured summary.\n"
    "\n"
    "OUTPUT FORMAT (REQUIRED - all sections must be present):\n"
    "```\n"
    "EXPLORATION REPORT\n"
    "Focus: [your focus area]\n"
    "\n"
    "Summary: [1-2 sentence overview]\n"
    "\n"
    "Structure:\n"
    '  [Key components and their roles, or "No clear component structure identified"]\n'
    "\n"
    "Patterns:\n"
    '  [Observed architectural/code patterns, or "No significant patterns observed"]\n'
    "\n"
    "Flows:\n"
    '  [Data/request flow through the system, or "Data flow not traced"]\n'
    "\n"
    "Decisions:\n"
    '  [Technology/design choices with rationale, or "No explicit design decisions found"]\n'
    "\n"
    "Gaps:\n"
    '  [Areas that remain unclear, or "Focus area may not exist in codebase"]\n'
    "```\n"
    "\n"
    "COMPLETE - Return exploration report to orchestrator."
)


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def build_next_command(step: int) -> str | None:
    """Build invoke command for next step."""
    if step >= TOTAL_STEPS:
        return None
    return f"uv run python -m {MODULE_PATH} --step {step + 1}"


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

STATIC_STEPS = {
    1: ("Explore", EXPLORE_INSTRUCTIONS),
    2: ("Report", REPORT_INSTRUCTIONS),
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_output(step: int) -> str:
    """Format output for given step."""
    if step not in STATIC_STEPS:
        return f"ERROR: Invalid step {step}"

    title, instructions = STATIC_STEPS[step]
    next_cmd = build_next_command(step)
    return format_step(instructions, next_cmd or "", title=f"CODEBASE EXPLORE - {title}")


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Codebase Analysis Explore - Focus-area exploration",
    )
    parser.add_argument("--step", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1 or args.step > TOTAL_STEPS:
        sys.exit(f"ERROR: --step must be 1-{TOTAL_STEPS}")

    print(format_output(args.step))


if __name__ == "__main__":
    main()
