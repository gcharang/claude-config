#!/usr/bin/env python3
"""
Refactor Explore - Dimension-specific exploration for refactoring analysis.

Two-step workflow per dimension:
  1. Exploration - Search for issues using dimension-specific heuristics
  2. Synthesis   - Format findings with severity assessment

Usage:
    python3 explore.py --step 1 --total-steps 2 --dimension naming
"""

import argparse
import os
import sys

# Import shared dimension definitions
from dimensions import DIMENSIONS, DIMENSION_ORDER


# =============================================================================
# XML Formatters (self-contained)
# =============================================================================


def format_step_header(step: int, total: int, title: str, dimension: str) -> str:
    """Render step header with dimension context."""
    return f'<step_header script="explore" step="{step}" total="{total}" dimension="{dimension}">{title}</step_header>'


def format_xml_mandate() -> str:
    """Return first-step guidance about XML format."""
    return """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>

DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
</xml_format_mandate>"""


def format_current_action(actions: list[str]) -> str:
    """Render current action block."""
    lines = ["<current_action>"]
    lines.extend(actions)
    lines.append("</current_action>")
    return "\n".join(lines)


def format_invoke_after(command: str) -> str:
    """Render invoke after block."""
    return f"<invoke_after>\n{command}\n</invoke_after>"


def format_heuristics(heuristics: list[str]) -> str:
    """Format heuristics as XML."""
    lines = ["<heuristics>"]
    for h in heuristics:
        lines.append(f"  <heuristic>{h}</heuristic>")
    lines.append("</heuristics>")
    return "\n".join(lines)


def format_detection_questions(questions: list[str]) -> str:
    """Format detection questions as XML."""
    lines = ["<detection_questions>"]
    for q in questions:
        lines.append(f"  <question>{q}</question>")
    lines.append("</detection_questions>")
    return "\n".join(lines)


def format_examples(examples: list[tuple[str, str]]) -> str:
    """Format before/after examples as XML."""
    lines = ["<examples>"]
    for before, after in examples:
        lines.append(f'  <example before="{before}">{after}</example>')
    lines.append("</examples>")
    return "\n".join(lines)


def format_findings_template() -> str:
    """Format the expected findings output structure."""
    return """<findings_format>
For each issue found, output:

  <finding severity="high|medium|low">
    <location>file.py:line-line</location>
    <evidence>quoted code (2-5 lines)</evidence>
    <issue>What's wrong and why it matters</issue>
  </finding>

After all findings, summarize:

  <dimension_summary>
    <dimension>$DIMENSION</dimension>
    <severity>none|low|medium|high</severity>
    <count>N</count>
    <recommendation>One sentence: worth deep dive or skip</recommendation>
  </dimension_summary>
</findings_format>"""


# =============================================================================
# Step Output
# =============================================================================


def format_step_1(dimension_id: str, script_path: str) -> str:
    """Format step 1: exploration prompt."""
    dim = DIMENSIONS[dimension_id]

    actions = [
        f"DIMENSION: {dim['title']}",
        f"FOCUS: {dim['focus']}",
        "",
        "EXPLORE the codebase using these heuristics:",
        "",
        format_heuristics(dim["heuristics"]),
        "",
        "ASK these questions as you read code:",
        "",
        format_detection_questions(dim["detection_questions"]),
        "",
        "EXAMPLES of improvements:",
        "",
        format_examples(dim["examples"]),
        "",
        "SEARCH STRATEGY:",
        "  1. Use Glob to find relevant files",
        "  2. Use Grep to find patterns matching heuristics",
        "  3. Use Read to examine suspicious code",
        "  4. Document each finding with location and evidence",
        "",
        "Do NOT propose solutions yet - just document findings.",
    ]

    parts = [
        format_step_header(1, 2, "Exploration", dimension_id),
        "",
        format_xml_mandate(),
        "",
        format_current_action(actions),
        "",
        format_invoke_after(f"python3 {script_path} --step 2 --total-steps 2 --dimension {dimension_id}"),
    ]
    return "\n".join(parts)


def format_step_2(dimension_id: str) -> str:
    """Format step 2: synthesis."""
    dim = DIMENSIONS[dimension_id]

    actions = [
        f"DIMENSION: {dim['title']}",
        "",
        "SYNTHESIZE your findings from Step 1.",
        "",
        format_findings_template(),
        "",
        "SEVERITY GUIDELINES:",
        "  HIGH: Blocks maintainability, affects multiple areas, clear fix exists",
        "  MEDIUM: Causes friction, localized impact, fix is straightforward",
        "  LOW: Minor annoyance, cosmetic, fix is trivial",
        "  NONE: No issues found in this dimension",
        "",
        "OUTPUT your findings now using the format above.",
    ]

    parts = [
        format_step_header(2, 2, "Synthesis", dimension_id),
        "",
        format_current_action(actions),
        "",
        "COMPLETE - Return findings to orchestrator.",
    ]
    return "\n".join(parts)


def format_output(step: int, total_steps: int, dimension: str, script_path: str) -> str:
    """Format output for the given step."""
    if step == 1:
        return format_step_1(dimension, script_path)
    else:
        return format_step_2(dimension)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Explore - Dimension-specific exploration",
        epilog=f"Dimensions: {', '.join(DIMENSION_ORDER)}",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--dimension", type=str, required=True, choices=DIMENSION_ORDER)

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 2:
        sys.exit("ERROR: --total-steps must be >= 2")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    script_path = os.path.abspath(__file__)
    print(format_output(args.step, args.total_steps, args.dimension, script_path))


if __name__ == "__main__":
    main()
