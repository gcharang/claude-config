#!/usr/bin/env python3
"""
Codebase Analysis Skill - Understanding-focused comprehension workflow.

Four-step workflow:
  1. SCOPE      - Define understanding goals (single pass)
  2. SURVEY     - Initial exploration via Explore agents (single pass)
  3. DEEPEN     - Targeted deep-dives with confidence iteration (1-4 iterations)
  4. SYNTHESIZE - Structured summary output (single pass)

Only DEEPEN iterates based on confidence. Other steps execute once and advance.
"""

import argparse
import sys

from skills.lib.workflow.prompts import format_step, roster_dispatch


# ============================================================================
# SHARED PROMPTS
# ============================================================================

DISPATCH_CONTEXT = """\
Analysis goals from SCOPE step:
- User intent and what they want to understand
- Identified focus areas (architecture, components, flows, etc.)
- Defined objectives (1-3 specific goals)"""


# ============================================================================
# CONFIGURATION
# ============================================================================

MODULE_PATH = "skills.codebase_analysis.analyze"
SUBAGENT_MODULE_PATH = "skills.codebase_analysis.subagent"
MAX_DEEPEN_ITERATIONS = 4
TOTAL_STEPS = 4


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: SCOPE -----------------------------------------------------------

SCOPE_INSTRUCTIONS = """\
PARSE user intent:
  - What codebase(s) are we analyzing?
  - What is the user trying to understand?
  - Are there specific areas of interest mentioned?

IDENTIFY focus areas:
  - Architecture/structure understanding
  - Specific component/feature deep-dive
  - Technology stack assessment
  - Integration patterns
  - Data flows

DEFINE goals (1-3 specific objectives):
  - 'Understand how [system X] processes [Y]'
  - 'Map dependencies between [A] and [B]'
  - 'Document data flow from [input] to [output]'

DO NOT seek user confirmation. Goals are internal guidance.

ADVANCE: When goals defined, proceed to SURVEY."""

# --- STEP 2: SURVEY ----------------------------------------------------------

SURVEY_DISPATCH_AGENTS = [
    "[Focus area 1: e.g., 'authentication and session management']",
    "[Focus area 2: e.g., 'database access patterns']",
    "[Focus area 3: e.g., 'API request routing']",
    "[Focus area N: based on scope and codebase structure]",
]

SURVEY_DISPATCH_GUIDANCE = """\
DISPATCH GUIDANCE:

Single codebase, focused scope:
  - One Explore agent with specific focus

Large/broad scope:
  - Multiple parallel Explore agents by boundary
  - Example: frontend agent + backend agent + data agent

Multiple repositories:
  - One Explore agent per repository

Generate focus areas based on:
  1. User's stated understanding goals (from SCOPE)
  2. Codebase structure (from initial observation)
  3. Coverage of different system aspects"""

SURVEY_PROCESSING_INSTRUCTIONS = """\
WAIT for Explore results.

PROCESS findings:

STRUCTURE:
  - Directory organization
  - File patterns
  - Module boundaries

PATTERNS:
  - Architectural style (layered, microservices, monolithic)
  - Code organization patterns
  - Naming conventions

FLOWS:
  - Entry points
  - Request/data flow paths
  - Integration patterns

DECISIONS:
  - Technology choices
  - Framework usage
  - Dependencies

ADVANCE: When exploration complete, proceed to DEEPEN."""

# --- STEP 3: DEEPEN ----------------------------------------------------------

DEEPEN_INSTRUCTIONS = """\
DEEPEN understanding through direct exploration.

DO NOT dispatch agents. Use Read, Glob, Grep tools directly.

IDENTIFY areas needing deep understanding:

Prioritize by:
  - COMPLEXITY: Non-obvious behavior, intricate logic
  - NOVELTY: Unfamiliar patterns, unique approaches
  - CENTRALITY: Core to user's goals

SELECT 1-3 targets for this iteration:
  - Specific component/module
  - Particular data flow
  - Integration mechanism
  - Implementation pattern

EXPLORE each target:
  - Read key files directly
  - Trace execution paths
  - Understand data transformations
  - Map dependencies

EXTRACT understanding:
  - How does this component work?
  - What are the key mechanisms?
  - How does it integrate with other parts?

ASSESS confidence:
  - CERTAIN: Goals fully understood, ready for synthesis
  - HIGH: Strong understanding, minor gaps acceptable
  - MEDIUM: Reasonable understanding, some questions remain
  - LOW: Significant gaps, need more exploration
  - EXPLORING: Just starting, identifying targets

ADVANCE:
  - confidence == certain: Proceed to SYNTHESIZE
  - confidence != certain AND iteration < {max_iter}: Continue DEEPEN
  - iteration >= {max_iter}: Force proceed to SYNTHESIZE"""

# --- STEP 4: SYNTHESIZE ------------------------------------------------------

SYNTHESIZE_INSTRUCTIONS = """\
OUTPUT structured summary:

# Codebase Understanding Summary

## Structure
[Directory organization, module boundaries, component relationships]

## Patterns
[Architectural patterns, design patterns, code organization]

## Flows
[Request flows, data flows, integration patterns]

## Decisions
[Technology choices, framework selections, architectural decisions]

## Context
[Purpose, constraints, trade-offs, evolution]

Ensure:
  - Summary addresses user's original intent
  - All sections present with concrete findings
  - Framing is understanding-focused (not auditing)
  - Facts and observations (not judgments)"""


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def build_survey_body() -> str:
    """Build SURVEY instructions with roster_dispatch().

    Orchestrator receives dispatch template. At runtime, orchestrator:
    1. Analyzes codebase structure (SCOPE)
    2. Generates 2-5 focus areas
    3. Dispatches agents in parallel with actual script invocation
    """
    invoke_cmd = f'python3 -m {SUBAGENT_MODULE_PATH} --step 1'

    dispatch_text = roster_dispatch(
        agent_type="general-purpose",
        agents=SURVEY_DISPATCH_AGENTS,
        command=invoke_cmd,
        shared_context=DISPATCH_CONTEXT,
        model="haiku",
        instruction="Determine 2-5 focus areas from SCOPE analysis. "
                    "Each agent's unique task is its focus area description. "
                    "The focus area goes in the agent's prompt text, NOT as a CLI arg. "
                    "The subagent script refers to 'your focus area' -- "
                    "the agent knows it from prompt context.",
    )

    return f"{dispatch_text}\n\n{SURVEY_DISPATCH_GUIDANCE}\n\n{SURVEY_PROCESSING_INSTRUCTIONS}"


def build_deepen_body(iteration: int) -> str:
    """Build DEEPEN instructions with iteration context."""
    return DEEPEN_INSTRUCTIONS.format(max_iter=MAX_DEEPEN_ITERATIONS)


# Pre-computed survey body (all inputs are module-level constants)
_SURVEY_BODY = build_survey_body()


def _format_step_3(confidence: str, iteration: int) -> tuple[str, str]:
    """Dynamic formatter for step 3 (Deepen) -- handles iteration/exit logic."""
    if confidence == "certain":
        return ("Deepen Complete", "Deep understanding achieved.\n\nPROCEED to SYNTHESIZE step.")
    if iteration >= MAX_DEEPEN_ITERATIONS:
        return (
            "Deepen Complete",
            f"Maximum DEEPEN iterations reached ({iteration}/{MAX_DEEPEN_ITERATIONS}).\n\n"
            "FORCE transition to SYNTHESIZE.",
        )
    return (f"Deepen (Iteration {iteration} of {MAX_DEEPEN_ITERATIONS})", build_deepen_body(iteration))


def build_next_command(step: int, confidence: str, iteration: int) -> str | None:
    """Build the invoke command for the next step."""
    base_cmd = f'python3 -m {MODULE_PATH}'

    if step == 1:
        return f'{base_cmd} --step 2'
    if step == 2:
        return f'{base_cmd} --step 3 --iteration 1 --confidence exploring'
    if step == 3:
        if confidence == "certain" or iteration >= MAX_DEEPEN_ITERATIONS:
            return f'{base_cmd} --step 4'
        return f'{base_cmd} --step 3 --iteration {iteration + 1} --confidence {{exploring|low|medium|high|certain}}'
    if step == 4:
        return None
    return None


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

STATIC_STEPS = {
    1: ("Scope", SCOPE_INSTRUCTIONS),
    2: ("Survey", _SURVEY_BODY),
    4: ("Synthesize", SYNTHESIZE_INSTRUCTIONS),
}

DYNAMIC_STEPS = {
    3: _format_step_3,
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_output(step: int, confidence: str, iteration: int) -> str:
    """Format output for the given step."""
    if step in STATIC_STEPS:
        title, instructions = STATIC_STEPS[step]
    elif step in DYNAMIC_STEPS:
        title, instructions = DYNAMIC_STEPS[step](confidence, iteration)
    else:
        return f"ERROR: Invalid step {step}"

    next_cmd = build_next_command(step, confidence, iteration)
    return format_step(instructions, next_cmd or "", title=f"CODEBASE ANALYSIS - {title}")


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Codebase Analysis - Understanding-focused comprehension workflow",
        epilog="Steps: SCOPE (1) -> SURVEY (2) -> DEEPEN (3) -> SYNTHESIZE (4)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument(
        "--confidence",
        type=str,
        choices=["exploring", "low", "medium", "high", "certain"],
        default="exploring",
        help="Current confidence level (DEEPEN step only)",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=1,
        help="Iteration count (DEEPEN step only, max 4)",
    )
    args = parser.parse_args()

    if args.step < 1 or args.step > TOTAL_STEPS:
        sys.exit(f"ERROR: --step must be 1-{TOTAL_STEPS}")
    if args.iteration < 1:
        sys.exit("ERROR: --iteration must be >= 1")

    print(format_output(args.step, args.confidence, args.iteration))


if __name__ == "__main__":
    main()
