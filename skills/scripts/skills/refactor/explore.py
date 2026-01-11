#!/usr/bin/env python3
"""
Refactor Explore - Category-specific exploration for code smell detection.

Two-step workflow per category:
  1. Exploration - Search for issues using category heuristics from markdown
  2. Synthesis   - Format findings with severity assessment
"""

import argparse
import sys
from pathlib import Path

from skills.lib.workflow.formatters import (
    format_xml_mandate,
    format_current_action,
    format_invoke_after,
)
from skills.lib.workflow.types import FlatCommand


# Module path for -m invocation
MODULE_PATH = "skills.refactor.explore"

# Path to conventions/code-quality/ directory
# explore.py is at: .claude/skills/scripts/skills/refactor/explore.py
# conventions is at: .claude/conventions/code-quality/
CONVENTIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "conventions" / "code-quality"


# =============================================================================
# Category Loader
# =============================================================================


def load_category_block(category_ref: str) -> str:
    """Load category text block from file:start-end reference.

    Args:
        category_ref: Reference in format "baseline.md:10-19"

    Returns:
        Text content of lines start through end (1-indexed, inclusive)
    """
    file_part, line_range = category_ref.split(":")
    start, end = map(int, line_range.split("-"))

    path = CONVENTIONS_DIR / file_part
    if not path.exists():
        sys.exit(f"ERROR: Category file not found: {path}")

    lines = path.read_text().splitlines()

    # Return lines start through end (1-indexed, inclusive)
    return "\n".join(lines[start - 1 : end])


# =============================================================================
# XML Formatters (explore-specific)
# =============================================================================


def format_step_header(step: int, total: int, title: str, category_ref: str) -> str:
    """Render step header with category context."""
    return f'<step_header script="explore" step="{step}" total="{total}" category="{category_ref}">{title}</step_header>'


# =============================================================================
# Step Output
# =============================================================================


def format_step_1(category_ref: str) -> str:
    """Format step 1: exploration prompt with category block."""
    category_block = load_category_block(category_ref)

    actions = [
        "<smell_category>",
        category_block,
        "</smell_category>",
        "",
        # RE2: Re-reading instruction improves comprehension by ~3pp (Xu et al. 2023)
        "Read the category definition again. Identify:",
        "  - The core detection question (Detect: line)",
        "  - Concrete patterns to search for",
        "  - Any Stop conditions that limit scope",
        "",
        "SEARCH STRATEGY:",
        "  1. Use Glob to find relevant files in scope",
        "  2. Use Grep to find patterns matching the heuristics above",
        "  3. Use Read to examine suspicious code",
        "  4. Document each finding with location and evidence",
        "",
        "CROSS-FILE PATTERN SEARCH:",
        "  5. After finding an issue, Grep for similar patterns in OTHER files",
        "  6. For each finding, note similar locations or mark as 'Unique'",
        "  7. Prioritize findings that appear in 3+ locations (abstraction candidates)",
        "",
        # Error Normalization: Prevents forcing false positives
        "CALIBRATION:",
        "  - Finding zero issues is a valid outcome. Do not force findings.",
        "  - Flag only when evidence is clear. Ambiguous cases are not findings.",
        "  - If a Stop condition applies, do not flag even if pattern matches.",
        "",
        "Document findings. Do NOT propose solutions yet.",
    ]

    parts = [
        format_step_header(1, 2, "Exploration", category_ref),
        "",
        format_xml_mandate(),
        "",
        format_current_action(actions),
        "",
        format_invoke_after(
            FlatCommand(
                f'<invoke working-dir=".claude/skills/scripts" '
                f'cmd="python3 -m {MODULE_PATH} --step 2 --total-steps 2 '
                f'--category {category_ref}" />'
            )
        ),
    ]
    return "\n".join(parts)


def format_step_2(category_ref: str) -> str:
    """Format step 2: synthesis with strict output format."""

    actions = [
        "SYNTHESIZE your findings from Step 1.",
        "",
        "OUTPUT FORMAT (strict):",
        "",
        '<smell_report category="$CATEGORY_NAME" severity="high|medium|low|none" count="N">',
        '  <finding location="file.py:line-line" severity="high|medium|low">',
        '    <evidence>quoted code (2-5 lines max)</evidence>',
        '    <issue>what is wrong (one sentence)</issue>',
        '  </finding>',
        '  <!-- repeat for each finding -->',
        '</smell_report>',
        "",
        "SEVERITY:",
        "  HIGH: Blocks maintainability, affects multiple areas",
        "  MEDIUM: Causes friction, localized impact",
        "  LOW: Minor annoyance, cosmetic",
        "  NONE: No issues found",
        "",
        "Extract $CATEGORY_NAME from the ## heading in the category block above.",
        "",
        "OUTPUT your smell_report now.",
    ]

    parts = [
        format_step_header(2, 2, "Synthesis", category_ref),
        "",
        format_current_action(actions),
        "",
        "COMPLETE - Return smell_report to orchestrator.",
    ]
    return "\n".join(parts)


def format_output(step: int, total_steps: int, category_ref: str) -> str:
    """Format output for the given step."""
    if step == 1:
        return format_step_1(category_ref)
    else:
        return format_step_2(category_ref)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Explore - Category-specific code smell detection",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        help="Category reference as file:startline-endline (e.g., baseline.md:5-13)",
    )

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 2:
        sys.exit("ERROR: --total-steps must be >= 2")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    # Validate category format
    if ":" not in args.category or "-" not in args.category.split(":")[1]:
        sys.exit("ERROR: --category must be in format file.md:start-end")

    print(format_output(args.step, args.total_steps, args.category))


if __name__ == "__main__":
    main()
