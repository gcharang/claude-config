#!/usr/bin/env python3
"""
Codebase Analysis Explore - Focus-area exploration for codebase understanding.

Four-step workflow:
  1. ORIENT   - Identify entry points for focus area
  2. MAP      - Build structural understanding
  3. EXTRACT  - Capture specific knowledge
  4. REPORT   - Synthesize into structured output

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
TOTAL_STEPS = 4


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: ORIENT ---------------------------------------------------------

ORIENT_INSTRUCTIONS = """\
ORIENT - Identify entry points for your focus area.

Your focus area was specified in your launching prompt.

ACTIONS:
  1. Glob for patterns matching focus area keywords
  2. Identify 3-8 candidate files as entry points
  3. Note language/framework indicators

EDGE CASE: If glob returns 0 matches, output empty entry points and proceed.

OUTPUT FORMAT:
```
ORIENTATION:
  Focus: [your focus area]
  Entry Points:
    - src/auth/login.py (main entry)
    - [3-8 files, or "No matches found"]
  Scope Estimate: N files
```"""

# --- STEP 2: MAP ------------------------------------------------------------

MAP_INSTRUCTIONS = """\
MAP - Build structural understanding from entry points.

INPUT: Use entry points from Step 1.

ACTIONS:
  1. Read key files identified in ORIENT
  2. Trace imports, calls, data flow
  3. Build component inventory
  4. Identify relationships between components

OUTPUT FORMAT:
```
STRUCTURE MAP:
  Components:
    - LoginHandler (src/auth/login.py) - entry point
  Relationships:
    - LoginHandler -> TokenService (calls)
  Patterns:
    - Repository pattern (3 occurrences)
```"""

# --- STEP 3: EXTRACT --------------------------------------------------------

EXTRACT_INSTRUCTIONS = """\
EXTRACT - Capture specific knowledge from structure map.

INPUT: Use structure map from Step 2.

ACTIONS:
  For each key component, answer:
  - HOW does this work? (mechanism)
  - WHY this approach? (design decision)

  Also identify:
  - Unclear areas needing further exploration
  - Edge cases or non-obvious behavior

OUTPUT FORMAT:
```
EXTRACTED KNOWLEDGE:
  TokenService:
    How: JWT-based with RSA signing, 1hr expiry
    Why: Stateless auth for horizontal scaling
  Decision (security): Refresh tokens stored in Redis
  Unclear: Token revocation mechanism not evident
```"""

# --- STEP 4: REPORT ---------------------------------------------------------

REPORT_INSTRUCTIONS = """\
REPORT - Synthesize findings into structured summary.

INPUT: All prior step outputs (orientation, structure map, extracted knowledge).

OUTPUT FORMAT (REQUIRED - all sections must be present):
```
EXPLORATION REPORT
Focus: [your focus area]

Summary: [1-2 sentence overview]

Structure:
  [Key components and their roles, or "No clear component structure identified"]

Patterns:
  [Observed architectural/code patterns, or "No significant patterns observed"]

Flows:
  [Data/request flow through the system, or "Data flow not traced"]

Decisions:
  [Technology/design choices with rationale, or "No explicit design decisions found"]

Gaps:
  [Areas that remain unclear, or "Focus area may not exist in codebase"]
```

COMPLETE - Return exploration report to orchestrator."""


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def build_next_command(step: int) -> str | None:
    """Build invoke command for next step."""
    if step >= TOTAL_STEPS:
        return None
    return f"python3 -m {MODULE_PATH} --step {step + 1}"


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

STEP_TITLES = {
    1: "Orient",
    2: "Map",
    3: "Extract",
    4: "Report",
}

STEP_INSTRUCTIONS = {
    1: ORIENT_INSTRUCTIONS,
    2: MAP_INSTRUCTIONS,
    3: EXTRACT_INSTRUCTIONS,
    4: REPORT_INSTRUCTIONS,
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_output(step: int) -> str:
    """Format output for given step."""
    if step not in STEP_TITLES:
        return f"ERROR: Invalid step {step}"

    title = STEP_TITLES[step]
    instructions = STEP_INSTRUCTIONS[step]
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
