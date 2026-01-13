#!/usr/bin/env python3
"""arxiv-to-md orchestrator: Parse input, dispatch sub-agents, rename outputs.

3-step workflow:
  1. Discover/Parse - Find arXiv IDs from input or folder metadata, dispatch sub-agents
  2. Wait          - Wait for all sub-agents to complete
  3. Finalize      - Rename successful outputs to target location
"""

import argparse
import sys

from skills.lib.workflow.formatters.text import build_invoke_command, format_text_output
from skills.lib.workflow.formatters import format_parallel_dispatch


MODULE_PATH = "skills.arxiv_to_md.main"
SUBAGENT_MODULE = "skills.arxiv_to_md.sub_agent"


def _build_parallel_dispatch():
    """Build the parallel dispatch block for sub-agent invocation."""
    return format_parallel_dispatch(
        agent="general-purpose",
        instruction="Launch one sub-agent per arXiv ID.\nUse a SINGLE message with multiple Task tool calls.",
        model="OPUS",
        model_rationale="These markdown files become the scientific basis for downstream work.\nCost of error amplifies: subpar markdown -> subpar knowledge.",
        template=f"""Convert this arXiv paper to markdown.

arXiv ID: $ARXIV_ID

Start: <invoke working-dir=".claude/skills/scripts" cmd="python3 -m {SUBAGENT_MODULE} --step 1 --arxiv-id $ARXIV_ID" />

<expected_output>
Sub-agent responds with ONLY:
FILE: <path-to-markdown>
OR
FAIL: <reason>
</expected_output>""",
        wait_message=None,
    )


PHASES = {
    1: {
        "title": "Discover and Dispatch",
        "brief": "Find arXiv IDs and launch sub-agents",
        "actions": [
            "DISCOVERY HINT:",
            "Before asking the user for arXiv IDs, check current working directory for:",
            "  - README.md or similar docs with arXiv links/IDs",
            "  - .bib files with arXiv entries",
            "  - Filenames containing arXiv IDs (e.g., 2503.05179.pdf)",
            "If IDs found, confirm with user: 'Found arXiv ID(s) X, Y. Convert these?'",
            "",
            "PARSE USER INPUT:",
            "If user provides input directly, parse for arXiv IDs:",
            "  - Format: YYMM.NNNNN (e.g., 2503.05179)",
            "  - Or full URL: https://arxiv.org/abs/YYMM.NNNNN",
            "  - May be multiple IDs (comma-separated, space-separated, or multiple URLs)",
            "",
            "DISPATCH:",
            "For EVERY arXiv ID found (even if just one), dispatch a sub-agent.",
            "",
            _build_parallel_dispatch(),
        ],
    },
    2: {
        "title": "Wait for Completion",
        "brief": "Collect sub-agent results",
        "actions": [
            "WAIT for all sub-agents to complete.",
            "",
            "Collect results from each sub-agent:",
            "  - FILE: <path> -> successful conversion",
            "  - FAIL: <reason> -> conversion failed",
            "",
            "Build results summary:",
            "```",
            "results:",
            "  - arxiv_id: 2503.05179",
            "    status: success",
            "    temp_path: /tmp/arxiv_2503.05179/cleaned.md",
            "  - arxiv_id: 2401.12345",
            "    status: failed",
            "    reason: PDF-only submission",
            "```",
        ],
    },
    3: {
        "title": "Finalize",
        "brief": "Rename successful outputs to target location",
        "actions": [
            "For each SUCCESSFUL conversion:",
            "",
            "1. Determine target filename:",
            "   - Default: <arxiv_id>.md in current working directory",
            "   - Example: 2503.05179.md",
            "",
            "2. Copy the cleaned.md to target:",
            "   ```bash",
            "   cp /tmp/arxiv_<id>/cleaned.md ./<arxiv_id>.md",
            "   ```",
            "",
            "3. Verify the copy succeeded:",
            "   - Use Read tool to confirm file exists and has content",
            "",
            "PRESENT FINAL SUMMARY to user:",
            "```",
            "Converted N of M papers:",
            "  [OK] 2503.05179 -> ./2503.05179.md",
            "  [FAIL] 2401.12345: PDF-only submission",
            "```",
        ],
    },
}


def main():
    parser = argparse.ArgumentParser(
        description="arxiv-to-md orchestrator",
        epilog="Steps: discover (1) -> wait (2) -> finalize (3)",
    )
    parser.add_argument("--step", type=int, required=True, help="Current step (1-3)")
    args = parser.parse_args()

    if args.step < 1 or args.step > 3:
        sys.exit(f"ERROR: --step must be 1-3, got {args.step}")

    phase = PHASES[args.step]

    next_step = args.step + 1
    if next_step <= 3:
        next_cmd = build_invoke_command(MODULE_PATH, step=next_step, total_steps=3)
    else:
        next_cmd = None

    print(
        format_text_output(
            step=args.step,
            total=3,
            title=f"ARXIV-TO-MD - {phase['title']}",
            actions=phase["actions"],
            brief=phase["brief"],
            invoke_after=next_cmd,
        )
    )


if __name__ == "__main__":
    main()
