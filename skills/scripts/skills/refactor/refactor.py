#!/usr/bin/env python3
"""
Refactor Skill - Category-based code smell detection.

Two-phase workflow:
  1. Dispatch - Launch parallel Explore agents (one per randomly selected category)
  2. Triage   - Review findings, prioritize by severity and cross-file patterns
"""

import argparse
import random
import re
import sys
from pathlib import Path

from skills.lib.workflow.formatters import (
    format_step_header,
    format_xml_mandate,
    format_current_action,
    format_invoke_after,
)
from skills.lib.workflow.types import FlatCommand


# Module paths for -m invocation
MODULE_PATH = "skills.refactor.refactor"
EXPLORE_MODULE_PATH = "skills.refactor.explore"

# Path to conventions/code-quality/ directory
CONVENTIONS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "conventions" / "code-quality"


# =============================================================================
# Category Parser
# =============================================================================


def parse_categories() -> list[dict]:
    """Parse markdown files, return categories with line ranges.

    Returns:
        List of dicts with keys: file, name, start_line, end_line
    """
    categories = []
    for md_file in ["baseline.md", "local.md", "cross-file.md", "drift.md"]:
        path = CONVENTIONS_DIR / md_file
        if not path.exists():
            continue

        lines = path.read_text().splitlines()

        current_cat = None
        for i, line in enumerate(lines, 1):
            # Match: ## N. Category Name
            if match := re.match(r"^## \d+\. (.+)$", line):
                if current_cat:
                    current_cat["end_line"] = i - 1
                    categories.append(current_cat)
                current_cat = {
                    "file": md_file,
                    "name": match.group(1),
                    "start_line": i,
                }
        if current_cat:
            current_cat["end_line"] = len(lines)
            categories.append(current_cat)

    return categories


def select_categories(n: int = 10) -> list[dict]:
    """Randomly select N categories.

    Args:
        n: Number of categories to select (default 10)

    Returns:
        List of N randomly selected category dicts
    """
    all_cats = parse_categories()
    return random.sample(all_cats, min(n, len(all_cats)))


# =============================================================================
# XML Formatters (refactor-specific)
# =============================================================================


def format_parallel_dispatch(n: int = 10) -> str:
    """Format the parallel dispatch block for step 1."""
    selected = select_categories(n)

    lines = [f'<parallel_dispatch agent="Explore" count="{len(selected)}">']
    lines.append("  <instruction>")
    lines.append(f"    Launch {len(selected)} Explore sub-agents IN PARALLEL (single message, {len(selected)} Task tool calls).")
    lines.append("    Each agent explores ONE code smell category.")
    lines.append("  </instruction>")
    lines.append("")
    lines.append("  <model_selection>")
    lines.append("    Use HAIKU (default) for all explore agents.")
    lines.append("    Each agent has a narrow, well-defined task - cheap models work well.")
    lines.append("  </model_selection>")
    lines.append("")
    lines.append("  <template>")
    lines.append("    Explore the codebase for this code smell.")
    lines.append("")
    lines.append(f'    Start: <invoke working-dir=".claude/skills/scripts" cmd="python3 -m {EXPLORE_MODULE_PATH} --step 1 --total-steps 2 --category $CATEGORY_REF" />')
    lines.append("  </template>")
    lines.append("")
    lines.append("  <categories>")
    for cat in selected:
        ref = f"{cat['file']}:{cat['start_line']}-{cat['end_line']}"
        lines.append(f'    <category ref="{ref}">{cat["name"]}</category>')
    lines.append("  </categories>")
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


# =============================================================================
# Step Definitions
# =============================================================================


STEPS = {
    1: {
        "title": "Dispatch",
        "brief": "Launch parallel Explore agents (one per randomly selected category)",
    },
    2: {
        "title": "Triage",
        "brief": "Prioritize smell findings",
        "actions": [
            "REVIEW all smell_report outputs from Step 1.",
            "",
            "PRIORITIZATION CRITERIA (in order):",
            "  1. HIGH severity findings first",
            "  2. Findings appearing in 3+ locations (abstraction candidates)",
            "  3. Findings aligned with user's stated focus (if any)",
            "",
            "OUTPUT:",
            "",
            "<prioritized_smells>",
            '  <tier name="critical">',
            '    <smell category="..." location="..." reason="high severity"/>',
            "  </tier>",
            '  <tier name="recommended">',
            '    <smell category="..." location="..." reason="medium, cross-file"/>',
            "  </tier>",
            '  <tier name="consider">',
            '    <smell category="..." location="..." reason="low severity"/>',
            "  </tier>",
            "</prioritized_smells>",
            "",
            "Present findings to user with locations and evidence.",
        ],
    },
}


# =============================================================================
# Output Formatting
# =============================================================================


def format_output(step: int, total_steps: int, n: int = 10) -> str:
    """Format output for display."""
    info = STEPS.get(step, STEPS[2])
    is_complete = step >= total_steps

    parts = []

    # Step header
    parts.append(format_step_header("refactor", step, total_steps, info["title"]))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        parts.append(format_xml_mandate())
        parts.append("")

    # Build actions
    actions = []

    if step == 1:
        # Step 1: Parallel dispatch
        actions.append("IDENTIFY the scope from user's request:")
        actions.append("  - Could be: file(s), directory, subsystem, entire codebase")
        actions.append("")
        actions.append(format_parallel_dispatch(n))
        actions.append("")
        actions.append(f"WAIT for all {n} agents to complete before proceeding.")
        actions.append("")
        actions.append(format_expected_output({
            "Per category": "smell_report with severity (none/low/medium/high) and findings",
            "Format": "<smell_report> blocks from each Explore agent",
        }))
    else:
        # Other steps use actions from STEPS dict
        if "actions" in info:
            actions.extend(info["actions"])

    parts.append(format_current_action(actions))
    parts.append("")

    # Invoke after
    if is_complete:
        parts.append("COMPLETE - Present prioritized findings to user.")
    else:
        next_step = step + 1
        parts.append(format_invoke_after(
            FlatCommand(
                f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step {next_step} --total-steps {total_steps}" />'
            )
        ))

    return "\n".join(parts)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Skill - Category-based code smell detection",
        epilog="Phases: dispatch -> triage",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--n", type=int, default=10,
                       help="Number of categories to explore (default: 10)")
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 2:
        sys.exit("ERROR: --total-steps must be >= 2 (2 phases in workflow)")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps, args.n))


if __name__ == "__main__":
    main()
