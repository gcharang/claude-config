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
from pathlib import Path

# Add parent of skills/ to path for skills.lib.workflow imports
claude_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(claude_dir) not in sys.path:
    sys.path.insert(0, str(claude_dir))

from skills.lib.workflow.formatters import (
    format_xml_mandate,
    format_current_action,
)


def format_invoke_after(command: str) -> str:
    """Render invoke after block for explore workflow.

    Simplified version that takes a string command directly.
    """
    return f"<invoke_after>\n{command}\n</invoke_after>"

# Import shared dimension definitions
from dimensions import DIMENSIONS, DIMENSION_ORDER


# =============================================================================
# XML Formatters (explore-specific)
# =============================================================================


def format_step_header(step: int, total: int, title: str, dimension: str) -> str:
    """Render step header with dimension context."""
    return f'<step_header script="explore" step="{step}" total="{total}" dimension="{dimension}">{title}</step_header>'


def format_heuristics(heuristics: list[str]) -> str:
    """Format heuristics as XML."""
    lines = ['<heuristics exemplary="true" note="illustrative, not exhaustive">']
    for h in heuristics:
        lines.append(f"  <heuristic>{h}</heuristic>")
    lines.append("</heuristics>")
    return "\n".join(lines)


def format_detection_questions(questions: list[str]) -> str:
    """Format detection questions as XML."""
    lines = ['<detection_questions exemplary="true" note="illustrative, not exhaustive">']
    for q in questions:
        lines.append(f"  <question>{q}</question>")
    lines.append("</detection_questions>")
    return "\n".join(lines)


def format_examples(examples: list[tuple[str, str]]) -> str:
    """Format before/after examples as XML."""
    lines = ['<examples exemplary="true" note="illustrative, not exhaustive">']
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
    <similar_patterns_elsewhere>
      If similar pattern exists in other files, list locations:
      - other_file.py:line (brief note on similarity)
      Otherwise: "Unique to this location"
    </similar_patterns_elsewhere>
  </finding>

After all findings, summarize:

  <dimension_summary>
    <dimension>$DIMENSION</dimension>
    <severity>none|low|medium|high</severity>
    <count>N</count>
    <cross_file_patterns>N findings appear in multiple locations</cross_file_patterns>
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
        "NON-EXHAUSTIVE GUIDANCE:",
        "The lists below illustrate this dimension's INTENT. Use them to understand the",
        "category of issues to detect, then apply similar reasoning beyond what's listed.",
        "",
        "EXPLORE the codebase using heuristics like these:",
        "",
        format_heuristics(dim["heuristics"]),
        "",
        "ASK questions like these as you read code:",
        "",
        format_detection_questions(dim["detection_questions"]),
        "",
        "EXAMPLES of improvements (illustrative):",
        "",
        format_examples(dim["examples"]),
        "",
        "SEARCH STRATEGY:",
        "  1. Use Glob to find relevant files",
        "  2. Use Grep to find patterns matching heuristics",
        "  3. Use Read to examine suspicious code",
        "  4. Document each finding with location and evidence",
        "",
        "CROSS-FILE PATTERN SEARCH:",
        "  5. After finding an issue, Grep for similar patterns in OTHER files",
        "  6. For each finding, note similar locations or mark as 'Unique'",
        "  7. Prioritize findings that appear in 3+ locations (abstraction candidates)",
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
