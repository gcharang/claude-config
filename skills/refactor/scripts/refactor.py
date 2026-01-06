#!/usr/bin/env python3
"""
Refactor Skill - Dimension-parallel refactoring analysis.

Six-phase workflow:
  1. Dispatch   - Launch parallel Explore agents (one per dimension)
  2. Triage     - Review findings, select promising dimensions
  3. Deep Dive  - Detailed analysis of selected dimensions
  4. Derive     - Propose improvements for confirmed findings
  5. Validate   - Test proposals against philosophy
  6. Synthesize - Prioritize and present recommendations

Usage:
    python3 refactor.py --step 1 --total-steps 6
"""

import argparse
import os
import sys


PHILOSOPHY = """
REFACTORING PHILOSOPHY (apply throughout):
  COMPOSABILITY: Small pieces that combine cleanly
  PRECISION: Names that create new semantic levels (Dijkstra)
  NO SPECULATION: Only abstract what you've seen repeated
  SIMPLICITY: The minimum needed for the current task
""".strip()


# Dimensions for parallel exploration
# Format: (id, title, focus, impact_weight)
# impact_weight: 3=structural (architecture, modules), 2=cross-cutting (types, errors), 1=local
DIMENSIONS = [
    ("naming", "Naming & Semantics", "Names that mislead, obscure intent, or operate at wrong abstraction level", 1),
    ("extraction", "Extraction & Composition", "Code that resists change due to duplication, mixed responsibilities, or complexity", 1),
    ("testability", "Testability", "Code that is difficult to test in isolation", 1),
    ("types", "Type & Interface Design", "Missing domain concepts, primitive obsession, leaky abstractions", 2),
    ("errors", "Error Handling", "Inconsistent, swallowed, or poorly-located error handling", 2),
    ("modules", "Module Boundaries", "Circular dependencies, wrong cohesion, layer violations", 3),
    ("modernization", "Modernization", "Outdated patterns, deprecated APIs, missed language features", 1),
    ("architecture", "Architecture", "Wrong boundaries, scaling bottlenecks, structural constraints", 3),
    ("readability", "Readability & LLM Comprehension", "Code that requires external context to understand, especially for LLMs", 1),
]


# =============================================================================
# XML Formatters (self-contained)
# =============================================================================


def format_step_header(step: int, total: int, title: str) -> str:
    """Render step header."""
    return f'<step_header script="refactor" step="{step}" total="{total}">{title}</step_header>'


def format_xml_mandate() -> str:
    """Return first-step guidance about XML format."""
    return """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>

DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
</xml_format_mandate>"""


def format_philosophy() -> str:
    """Format philosophy as XML."""
    lines = ['<philosophy scope="all_steps">']
    lines.append('  <principle name="COMPOSABILITY">Small pieces that combine cleanly</principle>')
    lines.append('  <principle name="PRECISION">Names that create new semantic levels (Dijkstra)</principle>')
    lines.append('  <principle name="NO_SPECULATION">Only abstract what you\'ve seen repeated</principle>')
    lines.append('  <principle name="SIMPLICITY">The minimum needed for the current task</principle>')
    lines.append("</philosophy>")
    return "\n".join(lines)


def format_current_action(actions: list[str]) -> str:
    """Render current action block."""
    lines = ["<current_action>"]
    lines.extend(actions)
    lines.append("</current_action>")
    return "\n".join(lines)


def format_invoke_after(command: str) -> str:
    """Render invoke after block."""
    return f"<invoke_after>\n{command}\n</invoke_after>"


def format_parallel_dispatch(explore_script_path: str) -> str:
    """Format the parallel dispatch block for step 1."""
    lines = [f'<parallel_dispatch agent="Explore" model="sonnet" count="{len(DIMENSIONS)}">']
    lines.append("  <instruction>")
    lines.append(f"    Launch {len(DIMENSIONS)} Explore sub-agents IN PARALLEL (single message, {len(DIMENSIONS)} Task tool calls).")
    lines.append("    Each agent explores ONE dimension. Use model='sonnet' for efficiency.")
    lines.append("  </instruction>")
    lines.append("")
    lines.append("  <template>")
    lines.append("    Explore the codebase for refactoring opportunities in the $DIMENSION dimension.")
    lines.append("    Focus on: $FOCUS")
    lines.append("")
    lines.append(f"    Start: python3 {explore_script_path} --step 1 --total-steps 2 --dimension $DIMENSION_ID")
    lines.append("  </template>")
    lines.append("")
    lines.append("  <dimensions>")
    for dim_id, dim_title, dim_focus, _ in DIMENSIONS:
        lines.append(f'    <dim id="{dim_id}" focus="{dim_focus}">{dim_title}</dim>')
    lines.append("  </dimensions>")
    lines.append("</parallel_dispatch>")
    return "\n".join(lines)


def format_expected_output(sections: dict[str, str]) -> str:
    """Render expected output block."""
    lines = ["<expected_output>"]
    for name, content in sections.items():
        lines.append(f'  <section name="{name}">')
        for line in content.split("\n"):
            lines.append(f"    {line}" if line else "")
        lines.append("  </section>")
    lines.append("</expected_output>")
    return "\n".join(lines)


def format_forbidden(actions: list[str]) -> str:
    """Render forbidden actions block."""
    lines = ["<forbidden>"]
    for action in actions:
        lines.append(f"  <action>{action}</action>")
    lines.append("</forbidden>")
    return "\n".join(lines)


def format_dimension_retrieval(dimensions_script_path: str) -> str:
    """Format the dimension retrieval block for Step 3."""
    lines = ['<retrieve_dimension_context>']
    lines.append("  BEFORE cross-checking, retrieve full context for each selected dimension.")
    lines.append("  This provides heuristics and detection questions to guide verification.")
    lines.append("")
    lines.append("  For EACH dimension in SELECTED_DIMENSIONS from Step 2, invoke:")
    lines.append(f"    python3 {dimensions_script_path} --dimension $DIM_ID")
    lines.append("")
    lines.append("  Example for 3 selected dimensions (naming, architecture, types):")
    lines.append(f"    python3 {dimensions_script_path} --dimension naming")
    lines.append(f"    python3 {dimensions_script_path} --dimension architecture")
    lines.append(f"    python3 {dimensions_script_path} --dimension types")
    lines.append("")
    lines.append("  The output contains:")
    lines.append("    - heuristics: What patterns to look for")
    lines.append("    - detection_questions: Questions to ask when verifying")
    lines.append("    - examples: Before/after patterns")
    lines.append("")
    lines.append("  Use this context to guide your cross-checking in this step.")
    lines.append("</retrieve_dimension_context>")
    return "\n".join(lines)


# =============================================================================
# Step Definitions
# =============================================================================


STEPS = {
    1: {
        "title": "Dispatch",
        "brief": "Launch parallel Explore agents (one per dimension)",
    },
    2: {
        "title": "Triage",
        "brief": "Review findings, select promising dimensions",
        "actions": [
            "Review ALL dimension findings from Step 1.",
            "",
            "DIMENSION REFERENCE (focus + impact weight):",
            "  architecture (3): Wrong boundaries, scaling bottlenecks, structural constraints",
            "  modules (3):      Circular dependencies, wrong cohesion, layer violations",
            "  types (2):        Missing domain concepts, primitive obsession, leaky abstractions",
            "  errors (2):       Inconsistent, swallowed, or poorly-located error handling",
            "  naming (1):       Names that mislead, obscure intent, or wrong abstraction level",
            "  extraction (1):   Code resisting change: duplication, mixed responsibilities",
            "  testability (1):  Code difficult to test in isolation",
            "  modernization (1): Outdated patterns, deprecated APIs, missed language features",
            "  readability (1):  Code requiring external context to understand",
            "",
            "SELECTION HEURISTIC (pick 3-5 dimensions max):",
            "",
            "  1. Eliminate dimensions with severity=none",
            "  2. Compute score = severity_score * count * impact_weight",
            "     where severity_score: high=3, medium=2, low=1",
            "  3. Rank by score descending",
            "  4. ARCHITECTURE ESCAPE HATCH: If architecture or modules is high severity,",
            "     include it regardless of rank (structural issues affect everything)",
            "  5. Take top 3-5; trim if more",
            "",
            "BUILD RANKING TABLE:",
            "",
            "  | Dimension | Severity | Count | Weight | Score | Selected? |",
            "  |-----------|----------|-------|--------|-------|-----------|",
            "",
            "OUTPUT:",
            "  SELECTED_DIMENSIONS: [list of 3-5 dimension IDs, ordered by score]",
            "  RATIONALE: Why these dimensions matter most",
            "  DEFERRED: [dimensions with low/no findings]",
        ],
    },
    3: {
        "title": "Deep Dive",
        "brief": "Detailed analysis of selected dimensions",
        "needs_dimension_retrieval": True,  # Flag for format_output
        "actions": [
            "For EACH selected dimension from Step 2:",
            "",
            "CROSS-CHECK findings using the retrieved heuristics:",
            "  - Re-read the code locations",
            "  - Verify evidence is accurate",
            "  - Apply detection questions from dimension definition",
            "  - Confirm issue is real (not false positive)",
            "",
            "TRACE to root causes:",
            "  - Do multiple findings share a root cause?",
            "  - Which findings are symptoms vs causes?",
            "",
            "GATHER additional evidence if needed:",
            "  - Use Glob/Grep to find related patterns",
            "  - Look for the 3+ instances rule (for duplication)",
            "",
            "OUTPUT (for Step 4):",
            "  CONFIRMED: [findings that passed cross-check]",
            "  REMOVED: [findings that were false positives + why]",
            "  ROOT_CAUSES: [which findings share root cause]",
        ],
    },
    4: {
        "title": "Derive",
        "brief": "Propose improvements for confirmed findings",
        "actions": [
            "For each CONFIRMED finding from Step 3:",
            "",
            "BEFORE proposing, you MUST:",
            "  1. QUOTE the finding with location and evidence",
            "  2. If claiming duplication, QUOTE all instances",
            "  3. State which dimension this addresses",
            "",
            "THEN propose:",
            "",
            "  [PROPOSAL] Brief title",
            "  Addresses: <dimension> finding at <location>",
            "  Mechanism: rename / extract / introduce type / restructure",
            "  The concept: <what domain concept does this name?>",
            "",
            "MECHANISM GUIDE BY DIMENSION:",
            "",
            "  NAMING -> Rename to express WHAT not HOW",
            "  EXTRACTION -> Extract function/class, reduce params",
            "  TESTABILITY -> Inject dependency, separate concerns",
            "  TYPES -> Introduce value object, define interface",
            "  ERRORS -> Normalize pattern, add context, right level",
            "  MODULES -> Break cycle, introduce facade, relocate",
            "  MODERNIZATION -> Update syntax, use language feature",
            "  ARCHITECTURE -> Introduce layer, define boundary",
            "",
            "OUTPUT: Proposals tied to specific, quoted findings.",
        ],
    },
    5: {
        "title": "Validate",
        "brief": "Test proposals against philosophy",
        "actions": [
            "For each proposal from Step 4, test against philosophy:",
            "",
            format_philosophy(),
            "",
            "COMPOSABILITY:",
            "  - Can this piece be combined with others?",
            "  - Does it have a clean, minimal interface?",
            "  - Or does it require special handling / knowledge of internals?",
            "",
            "PRECISION (Dijkstra test):",
            "  - Does the name create a NEW semantic level?",
            "  - Can you reason precisely about it without seeing implementation?",
            "  - Red flags: Helper, Utils, Manager, Handler, Base, Common",
            "",
            "NO SPECULATION:",
            "  - Have I seen this pattern 3+ times?",
            "  - Or am I speculating from one instance?",
            "",
            "SIMPLICITY:",
            "  - Is this the SIMPLEST thing that removes the friction?",
            "  - Am I predicting futures that may not come?",
            "  - Would a senior engineer say 'just inline this'?",
            "",
            "OUTPUT:",
            "  VALIDATED: [proposals that PASS all tests]",
            "  KILLED: [proposals that failed + WHY]",
        ],
    },
    6: {
        "title": "Synthesize",
        "brief": "Prioritize and present recommendations",
        "actions": [
            "From Step 5's VALIDATED proposals:",
            "",
            "RANK by impact and effort:",
            "",
            "  HIGH IMPACT + LOW EFFORT (do first):",
            "    - Rename for precision (improves readability)",
            "    - Extract small helper (reduces duplication)",
            "    - Modernize syntax (quick win)",
            "",
            "  HIGH IMPACT + HIGH EFFORT (plan carefully):",
            "    - Introduce domain type",
            "    - Decompose god function",
            "    - Restructure module boundaries",
            "",
            "  LOW IMPACT (defer or skip):",
            "    - Cosmetic changes",
            "    - Proposals with weak evidence",
            "",
            "FORMAT each recommendation:",
            "",
            "  ## [PRIORITY] Title",
            "  DIMENSION: <which dimension>",
            "  FINDING: <what's wrong, with quoted code>",
            "  INSIGHT: <what concept is hiding here?>",
            "  PROPOSAL: <specific action: rename X, extract Y, introduce Z>",
            "  EVIDENCE: <why this isn't premature -- show 3+ instances>",
            "",
            "WARN about risks:",
            "  - Changes affecting public API",
            "  - Refactors needing test updates",
            "  - Cross-cutting changes",
        ],
    },
}


# =============================================================================
# Output Formatting
# =============================================================================


def format_output(step: int, total_steps: int) -> str:
    """Format output for display."""
    info = STEPS.get(step, STEPS[6])
    is_complete = step >= total_steps
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    explore_script_path = os.path.join(script_dir, "explore.py")
    dimensions_script_path = os.path.join(script_dir, "dimensions.py")

    parts = []

    # Step header
    parts.append(format_step_header(step, total_steps, info["title"]))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        parts.append(format_xml_mandate())
        parts.append("")

    # Dimension retrieval for step 3
    if step == 3:
        parts.append(format_dimension_retrieval(dimensions_script_path))
        parts.append("")

    # Build actions
    actions = []

    # Philosophy for all steps
    actions.append(format_philosophy())
    actions.append("")

    if step == 1:
        # Step 1: Parallel dispatch
        actions.append("IDENTIFY the scope from user's request:")
        actions.append("  - Could be: file(s), directory, subsystem, entire codebase")
        actions.append("")
        actions.append(format_parallel_dispatch(explore_script_path))
        actions.append("")
        actions.append(f"WAIT for all {len(DIMENSIONS)} agents to complete before proceeding.")
        actions.append("")
        actions.append(format_expected_output({
            "Per dimension": "FINDINGS with severity (none/low/medium/high)",
            "Format": "<dimension_summary> blocks from each Explore agent",
        }))
    else:
        # Other steps use actions from STEPS dict
        if "actions" in info:
            actions.extend(info["actions"])

    parts.append(format_current_action(actions))
    parts.append("")

    # Invoke after
    if is_complete:
        parts.append("COMPLETE - Present recommendations to user.")
    else:
        next_step = step + 1
        parts.append(format_invoke_after(
            f"python3 {script_path} --step {next_step} --total-steps {total_steps}"
        ))

    return "\n".join(parts)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Skill - Dimension-parallel refactoring analysis",
        epilog="Phases: dispatch -> triage -> deep-dive -> derive -> validate -> synthesize",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 6:
        sys.exit("ERROR: --total-steps must be >= 6 (6 phases in workflow)")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps))


if __name__ == "__main__":
    main()
