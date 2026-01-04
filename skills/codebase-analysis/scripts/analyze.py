#!/usr/bin/env python3
"""
Codebase Analysis Skill - Compact systematic analysis workflow.

Four-phase workflow:
  1. Explore    - Dispatch Explore agent(s), process results
  2. Plan       - Focus selection + investigation commitments
  3. Investigate - Deep analysis with evidence (1-N rounds)
  4. Synthesize - Verification + consolidated findings

Usage:
    python3 analyze.py --step 1 --total-steps 4
"""

import argparse
import sys


STEPS = {
    1: {
        "title": "Explore",
        "brief": "Dispatch exploration, process results",
        "actions": [
            "If NO Explore agent output in context:",
            "  Delegate to Explore sub-agent(s):",
            "    - Single codebase: one agent",
            "    - Large/broad scope: parallel agents by boundary",
            "    - Multiple repos: one agent per repo",
            "  Wait for results before re-invoking this step.",
            "",
            "If Explore output available, extract:",
            "  STRUCTURE: directories, organization, file patterns",
            "  TECH STACK: languages, frameworks, dependencies",
            "  ENTRY POINTS: main executables, APIs, data flow",
            "  OBSERVATIONS: patterns, code smells, concerns",
        ],
    },
    2: {
        "title": "Plan",
        "brief": "Focus selection + investigation commitments",
        "actions": [
            "CLASSIFY focus areas by dimension:",
            "  ARCHITECTURE: dependencies, layering, boundaries",
            "  PERFORMANCE: hot paths, queries, memory, concurrency",
            "  SECURITY: validation, auth, data handling",
            "  QUALITY: duplication, complexity, error handling, tests",
            "",
            "PRIORITIZE: P1 > P2 > P3 (security > correctness > perf)",
            "",
            "COMMIT to specific investigation targets:",
            "  For each focus area:",
            "    - Files to examine (exact paths)",
            "    - Question to answer about each file",
            "    - Hypothesis (what you expect to find)",
            "    - Evidence needed to confirm/refute",
            "",
            "This is a CONTRACT. You MUST examine every file listed.",
        ],
    },
    3: {
        "title": "Investigate",
        "brief": "Deep analysis with evidence",
        "actions": [
            "For each file in your investigation plan:",
            "  1. READ the file (use Read tool)",
            "  2. ANSWER the specific question",
            "  3. DOCUMENT with evidence:",
            "",
            "     [SEVERITY] Description (file.py:line)",
            "     > quoted code (2-5 lines)",
            "     Explanation: why this is an issue",
            "",
            "  4. UPDATE hypothesis based on findings",
            "",
            "TRACE root causes:",
            "  - Why does this issue exist?",
            "  - Related issues in connected files?",
            "  - Same pattern elsewhere? (systemic vs localized)",
            "",
            "CONTINUE investigation or proceed to synthesis.",
            "Adjust total-steps if more rounds needed.",
        ],
    },
    4: {
        "title": "Synthesize",
        "brief": "Verification + consolidated findings",
        "actions": [
            "VERIFY completeness:",
            "  - Every committed file examined?",
            "  - Every question answered with evidence?",
            "  - [CRITICAL]/[HIGH] findings have file:line + quoted code?",
            "",
            "If gaps exist: return to Investigate step.",
            "",
            "CONSOLIDATE by severity:",
            "  CRITICAL: must address immediately (file:line, quote, fix)",
            "  HIGH: should address soon (file:line, description, fix)",
            "  MEDIUM: consider addressing (description, guidance)",
            "  LOW: nice to fix (summarize, defer)",
            "",
            "IDENTIFY patterns:",
            "  - Issues across multiple files = systemic",
            "  - Root causes explaining multiple symptoms",
            "",
            "RECOMMEND actions:",
            "  IMMEDIATE: blocks other work / security",
            "  SHORT-TERM: current sprint",
            "  LONG-TERM: strategic improvements",
        ],
    },
}


def format_output(step: int, total_steps: int) -> str:
    """Format compact output for display."""
    # Extra steps in the middle go to Investigate
    if step == 1:
        info = STEPS[1]
    elif step == 2:
        info = STEPS[2]
    elif step >= total_steps:
        info = STEPS[4]  # Final synthesis
    else:
        info = STEPS[3]  # Investigation rounds

    is_complete = step >= total_steps

    lines = [
        f"CODEBASE ANALYSIS - Step {step}/{total_steps}: {info['title']}",
        f"  {info['brief']}",
        "",
        "DO:",
    ]

    for action in info["actions"]:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    lines.append("")

    if is_complete:
        lines.append("COMPLETE - Present findings to user.")
    else:
        next_step = step + 1
        if next_step == 1:
            next_info = STEPS[1]
        elif next_step == 2:
            next_info = STEPS[2]
        elif next_step >= total_steps:
            next_info = STEPS[4]
        else:
            next_info = STEPS[3]
        lines.append(f"NEXT: Step {next_step} - {next_info['title']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Codebase Analysis - Compact analysis workflow",
        epilog="Phases: explore (1) -> plan (2) -> investigate (3+) -> synthesize (N)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 4:
        sys.exit("ERROR: --total-steps must be >= 4")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps))


if __name__ == "__main__":
    main()
