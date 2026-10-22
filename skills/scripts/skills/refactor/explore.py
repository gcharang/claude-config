#!/usr/bin/env python3
"""
Refactor Explore - Category-specific exploration for code smell detection.
"""

import argparse
import re
import shlex
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

from skills.lib.workflow.ast import (
    CurrentActionNode,
    InvokeAfterNode,
    StepHeaderNode,
    render_current_action,
    render_invoke_after,
    render_step_header,
)

MODULE_PATH = "skills.refactor.explore"
TOTAL_STEPS = 2

# Path to conventions/code-quality/ directory
CONVENTIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "conventions" / "code-quality"
)

# Category heading in conventions/code-quality/*.md; group 1 is the category name.
CATEGORY_HEADING_RE = re.compile(r"^## \d+\. (.+)$")


# =============================================================================
# Category Loader
# =============================================================================


def load_category_block(category_ref: str, mode: str = "code") -> str:
    """Load category text block from file:start-end reference.

    Args:
        category_ref: File reference (file:start-end)
        mode: "design" or "code" - extracts mode-specific guidance

    Returns:
        Category content with mode-specific guidance extracted
    """
    file_part, line_range = category_ref.split(":")
    start, end = map(int, line_range.split("-"))

    from skills.lib.io import read_text_or_exit

    path = CONVENTIONS_DIR / file_part
    content = read_text_or_exit(path, "loading category file")
    lines = content.splitlines()
    category_block = "\n".join(lines[start - 1 : end])

    mode_tag = f"<{mode}-mode>"
    close_tag = f"</{mode}-mode>"

    if mode_tag in category_block:
        _, sep, after = category_block.partition(mode_tag)
        if sep:
            inner, sep, _ = after.partition(close_tag)
            if sep:
                category_block = category_block.replace(
                    f"{mode_tag}{inner}{close_tag}", inner.strip()
                )

    for tag in ["<design-mode>", "</design-mode>", "<code-mode>", "</code-mode>"]:
        category_block = category_block.replace(tag, "")

    return category_block


def load_category_name(category_ref: str) -> str:
    """Return the name in the category heading that category_ref starts at.

    Exits when the ref starts anywhere else, including past the end of the file, so
    a mis-copied ref fails instead of reporting findings under a wrong category.
    """
    first_line = load_category_block(category_ref).partition("\n")[0]
    if heading := CATEGORY_HEADING_RE.match(first_line):
        return heading.group(1)
    sys.exit(f"ERROR: --category {category_ref} does not start at a '## N. Name' category heading")


# =============================================================================
# XML Formatters
# =============================================================================


def format_next_step(
    step: int, category_ref: str, mode: str = "code", scope: str | None = None
) -> str:
    """Format the invoke-after block for next step."""
    scope_arg = f" --scope {shlex.quote(scope)}" if scope else ""
    cmd = (
        f"uv run python -m {MODULE_PATH} --step {step} --category {category_ref} --mode {mode}{scope_arg}"
    )
    return render_invoke_after(InvokeAfterNode(cmd=cmd))


# =============================================================================
# Step 1: Search
# =============================================================================


def format_step_1(category_ref: str, mode: str = "code", scope: str | None = None) -> str:
    """Step 1: Search the scope for code that violates the category."""
    category_block = load_category_block(category_ref, mode)
    mode_description = "architecture/intent" if mode == "design" else "implementation"
    scope_display = (
        f"SCOPE: {scope} (pass it as the path argument of every Glob and Grep call)"
        if scope
        else "SCOPE: Entire codebase"
    )
    actions = [
        "<smell_category>",
        category_block,
        "</smell_category>",
        "",
        f"MODE: {mode} ({mode_description})",
        scope_display,
        "",
        "Find code in scope that violates this category's <principle>. The listed violations",
        "and <grep-hints> are illustrative: translate them to this project's language,",
        "frameworks and naming, and look for unlisted violations of the same principle.",
        "Apply the category's <threshold> and <exceptions>.",
        "",
        "Read suspicious matches before reporting them. After finding an issue, Grep other",
        "files for the same pattern; a pattern in 3+ locations is one systemic finding.",
        "",
        'For each finding, run Grep with output_mode="count" on the pattern that found it,',
        "and record the count and the pattern so the count can be reproduced.",
        "",
        "Finding zero issues is a valid outcome; do not force findings.",
        "Keep a borderline case as a finding at severity low rather than dropping it;",
        "the orchestrator filters.",
    ]

    parts = [
        render_step_header(
            StepHeaderNode(
                title="Search", script="explore", step=1, category=category_ref, mode=mode
            )
        ),
        "",
        render_current_action(CurrentActionNode(actions)),
        "",
        format_next_step(2, category_ref, mode, scope),
    ]
    return "\n".join(parts)


# =============================================================================
# Step 2: Report
# =============================================================================


def format_step_2(category_ref: str, mode: str = "code", scope: str | None = None) -> str:
    """Step 2: Write the findings as one smell report."""
    category_name = load_category_name(category_ref)
    actions = [
        "REPORT the findings from your search as one smell_report.",
        "",
        "OUTPUT FORMAT (strict):",
        "",
        "REPORT SIZE:",
        "  Report every finding that meets the evidence requirements below, most severe",
        "  first. Quote 2-5 lines of code per finding and keep each finding to the fields",
        "  shown; the orchestrator merges the reports from every category.",
        "",
        # WHY impact tag requires "Blocks/Degrades/Risks" structure:
        #
        # Without structure, agents produce:
        #   - Restatements: "This is inconsistent" (not an impact)
        #   - Vague claims: "Could cause issues" (what issues?)
        #   - Implementation details: "Should use HashMap" (not WHY)
        #
        # The 3-verb taxonomy forces causal reasoning:
        #   - "Blocks X" -> identifies a concrete capability gap
        #   - "Degrades X" -> quantifies a performance/quality cost
        #   - "Risks X" -> names a failure mode
        #
        # This makes impact falsifiable: reviewers can verify whether X is actually affected.
        f'<smell_report category={quoteattr(category_name)} mode={quoteattr(mode)} severity="high|medium|low|none" count="N">',
        '  <finding location="file:line-range" severity="high|medium|low">',
        '    <evidence lines="N">',
        "      quoted code (2-5 lines, preserve exact indentation)",
        "    </evidence>",
        "    <issue>what is wrong (one sentence, be specific)</issue>",
        "    <impact>",
        "      WHY fix this? One of:",
        '      - "Blocks X" (prevents something)',
        '      - "Degrades X" (makes something worse)',
        '      - "Risks X" (could cause harm)',
        "    </impact>",
        '    <occurrences count="N" verification="grep -r PATTERN path/">',
        "      Codebase-wide count. Verification command must reproduce the count.",
        "    </occurrences>",
        "  </finding>",
        "  <!-- repeat for each finding -->",
        "</smell_report>",
        "",
        "EVIDENCE REQUIREMENTS (findings without these are INVALID):",
        "  1. <evidence> must quote actual code, not describe it",
        "  2. <impact> must state consequence, not just restate the issue",
        "  3. <occurrences> count must come from actual Grep, not estimation",
        "  4. verification attribute must be executable command",
        "",
        "SEVERITY LEVELS:",
        "  HIGH: Blocks maintainability, affects multiple areas",
        "  MEDIUM: Causes friction, localized impact",
        "  LOW: Minor annoyance, cosmetic",
        "  NONE: No issues found (empty findings)",
        "",
        "OUTPUT your smell_report now.",
    ]

    parts = [
        render_step_header(
            StepHeaderNode(
                title="Report", script="explore", step=2, category=category_ref, mode=mode
            )
        ),
        "",
        render_current_action(CurrentActionNode(actions)),
        "",
        "COMPLETE - Return smell_report to orchestrator.",
    ]
    return "\n".join(parts)


# =============================================================================
# Output Router
# =============================================================================


def format_output(
    step: int, category_ref: str, mode: str = "code", scope: str | None = None
) -> str:
    """Route to appropriate step formatter."""
    formatters = {
        1: format_step_1,
        2: format_step_2,
    }
    formatter = formatters.get(step)
    if not formatter:
        sys.exit(f"ERROR: Unknown step {step}")
    return formatter(category_ref, mode, scope)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Refactor Explore - Category-specific code smell detection",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        help="Category reference as file:startline-endline (e.g., 01-naming-and-types.md:5-13)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["design", "code"],
        default="code",
        help="Evaluation mode: design (architecture/intent) or code (implementation)",
    )
    parser.add_argument(
        "--scope",
        type=str,
        default=None,
        help="Filesystem scope constraint for Glob/Grep operations (e.g., 'src/planner/')",
    )

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.step > TOTAL_STEPS:
        sys.exit(f"ERROR: --step cannot exceed {TOTAL_STEPS}")

    if ":" not in args.category or "-" not in args.category.split(":")[1]:
        sys.exit("ERROR: --category must be in format file.md:start-end")
    # Checked at every step so a bad ref fails at step 1, not after the agent's search.
    load_category_name(args.category)

    print(format_output(args.step, args.category, args.mode, args.scope))


if __name__ == "__main__":
    main()
