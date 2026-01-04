#!/usr/bin/env python3
"""
Interactive Sequential Planner - Two-phase planning workflow.

PLANNING PHASE: Step-based planning with context discovery.
REVIEW PHASE: TW scrub and QR validation before execution.

Usage:
    python3 planner.py --phase planning --step 1 --total-steps 4
    python3 planner.py --phase review --step 1 --total-steps 3
"""

import argparse
import sys
from pathlib import Path

from utils import get_qr_state_banner, get_qr_stop_condition


def get_plan_format() -> str:
    """Read the plan format template from resources."""
    format_path = Path(__file__).parent.parent / "resources" / "plan-format.md"
    return format_path.read_text()


PLANNING_STEPS = {
    1: {
        "title": "Context Discovery",
        "actions": [
            "READ resources: default-conventions.md, diff-format.md, temporal-contamination.md",
            "",
            "DELEGATE exploration to Explore sub-agent:",
            "  Task tool with subagent_type='Explore'",
            "  Prompt: Gather context for [TASK]. Return:",
            "    - Files to modify (exact paths)",
            "    - Codebase patterns (naming, errors, tests)",
            "    - Constraints and scope (IN/OUT)",
            "    - Success criteria",
        ],
    },
    2: {
        "title": "Approach Generation",
        "actions": [
            "GENERATE 2-3 approach options:",
            "  - Include 'minimal change' option",
            "  - Include 'idiomatic/modern' option",
            "  - Document advantage/disadvantage for each",
            "",
            "TARGET TECH RESEARCH (if new tech/migration):",
            "  - What is canonical usage of target tech?",
            "  - Does it have different abstractions?",
            "",
            "TEST REQUIREMENTS:",
            "  - Check project docs for test requirements",
            "  - If silent, default-conventions domain='testing' applies",
        ],
    },
    3: {
        "title": "Assumption Surfacing",
        "actions": [
            "FAST PATH: Skip if task involves NONE of:",
            "  - Migration to new tech",
            "  - Policy defaults (lifecycle, capacity, failure handling)",
            "  - Architectural decisions with multiple valid approaches",
            "",
            "FULL CHECK (if any apply):",
            "  Audit each category with OPEN questions:",
            "    Pattern preservation, Migration strategy, Idiomatic usage,",
            "    Abstraction boundary, Test strategy, Policy defaults",
            "",
            "  For each assumption needing confirmation:",
            "    Use AskUserQuestion BEFORE proceeding",
            "    Record choice in Decision Log with 'user-specified' backing",
        ],
    },
    4: {
        "title": "Approach Selection & Milestones",
        "actions": [
            "EVALUATE approaches: P(success), failure mode, backtrack cost",
            "",
            "SELECT and record in Decision Log with MULTI-STEP chain:",
            "  BAD:  'Polling | Webhooks unreliable'",
            "  GOOD: 'Polling | 30% webhook failure -> need fallback anyway'",
            "",
            "MILESTONES (each deployable increment):",
            "  - Files: exact paths",
            "  - Requirements: specific behaviors",
            "  - Acceptance: testable pass/fail criteria",
            "  - Code: diff format for non-trivial logic",
            "  - Tests: type, backing, scenarios",
            "",
            "RISKS: | Risk | Mitigation | Anchor (file:line if behavioral claim) |",
        ],
    },
    5: {
        "title": "Final Verification",
        "actions": [
            "READ resources/planning-verification.md",
            "",
            "Complete ALL verification checks:",
            "  Phase 1 (BLOCKING): Decision Log, Code Changes, Invisible Knowledge",
            "  Phase 2 (FORMAT): Diff compliance, Milestone spec",
            "  Phase 3 (DOCS): Documentation milestone, Comment hygiene",
            "",
            "STOP if any Phase 1 check fails. Fix before proceeding.",
        ],
    },
}


REVIEW_STEPS = {
    1: {
        "title": "Parallel QR (Completeness + Code)",
        "actions": [
            "SPAWN BOTH in parallel (single message, two Task calls):",
            "",
            "QR-Completeness (subagent: quality-reviewer):",
            "  mode: plan-completeness",
            "  Check: Decision Log, policy defaults, plan structure",
            "",
            "QR-Code (subagent: quality-reviewer):",
            "  mode: plan-code",
            "  Check: Diff context matches codebase, RULE 0/1/2",
            "",
            "GATE: Both must PASS before TW.",
            "If ISSUES: Fix, then re-invoke with --qr-iteration incremented.",
        ],
    },
    2: {
        "title": "TW Documentation Scrub",
        "actions": [
            "SPAWN technical-writer agent:",
            "  mode: plan-scrub",
            "  Task: Add WHY comments from Decision Log, enrich prose",
            "",
            "TW edits plan file IN-PLACE.",
            "Wait for completion before proceeding to QR-Docs.",
        ],
    },
    3: {
        "title": "QR Documentation Validation",
        "actions": [
            "SPAWN quality-reviewer agent:",
            "  mode: plan-docs",
            "  Check: Temporal contamination, hidden baselines, WHY not WHAT",
            "",
            "GATE: Must PASS for plan approval.",
            "If ISSUES: Return to step 2 (TW) with scope, then re-verify.",
        ],
    },
}


def get_planning_guidance(step: int, total_steps: int) -> dict:
    """Returns guidance for planning phase steps."""
    is_complete = step >= total_steps

    if is_complete:
        plan_format = get_plan_format()
        return {
            "title": "Planning Complete",
            "actions": PLANNING_STEPS.get(5, PLANNING_STEPS[4])["actions"],
            "next": (
                f"Write plan using this format:\n\n{plan_format}\n\n"
                "Then invoke review phase:\n"
                "  python3 planner.py --phase review --step 1 --total-steps 3"
            ),
        }

    info = PLANNING_STEPS.get(step, PLANNING_STEPS[4])
    return {
        "title": info["title"],
        "actions": info["actions"],
        "next": f"Step {step + 1}: {PLANNING_STEPS.get(step + 1, PLANNING_STEPS[4])['title']}",
    }


def get_review_guidance(step: int, total_steps: int,
                         qr_iteration: int = 1, fixing_issues: bool = False) -> dict:
    """Returns guidance for review phase steps."""
    is_complete = step >= total_steps

    # Re-verification mode: condensed guidance
    if qr_iteration > 1 and step in (1, 3):
        banner = get_qr_state_banner(
            "PLAN QR" if step == 1 else "DOC QR",
            qr_iteration, fixing_issues
        )
        stop = get_qr_stop_condition(
            "BOTH QR agents PASS" if step == 1 else "QR-Docs PASS",
            qr_iteration
        )
        return {
            "title": f"Re-Verify (iteration {qr_iteration})",
            "actions": banner + ["", "Re-spawn same agent(s). Expect PASS after fixes."] + stop,
            "next": "Proceed to next step on PASS, or fix and re-verify on ISSUES.",
        }

    info = REVIEW_STEPS.get(step, REVIEW_STEPS[3])

    if step == 1:
        banner = get_qr_state_banner("PLAN QR", qr_iteration, fixing_issues)
        stop = get_qr_stop_condition("BOTH QR agents PASS", qr_iteration)
        actions = banner + info["actions"] + stop
    elif step == 3:
        banner = get_qr_state_banner("DOC QR", qr_iteration, fixing_issues)
        stop = get_qr_stop_condition("QR-Docs PASS", qr_iteration)
        actions = banner + info["actions"] + stop
    else:
        actions = info["actions"]

    if is_complete:
        return {
            "title": "Review Complete",
            "actions": actions,
            "next": "PLAN APPROVED. Ready for /plan-execution.",
        }

    return {
        "title": info["title"],
        "actions": actions,
        "next": f"Step {step + 1}: {REVIEW_STEPS.get(step + 1, REVIEW_STEPS[3])['title']}",
    }


def format_output(phase: str, step: int, total_steps: int,
                  qr_iteration: int, fixing_issues: bool) -> str:
    """Format output for display."""
    if phase == "planning":
        guidance = get_planning_guidance(step, total_steps)
        phase_label = "PLANNING"
    else:
        guidance = get_review_guidance(step, total_steps, qr_iteration, fixing_issues)
        phase_label = "REVIEW"

    lines = [
        f"PLANNER - {phase_label} - Step {step}/{total_steps}: {guidance['title']}",
        "",
        "DO:",
    ]

    for action in guidance["actions"]:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    lines.append("")
    lines.append("NEXT:")
    lines.append(f"  {guidance['next']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Sequential Planner (Two-Phase)",
        epilog="planning: context -> approach -> assumptions -> milestones | review: QR -> TW -> QR",
    )

    parser.add_argument("--phase", type=str, default="planning",
                        choices=["planning", "review"])
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--fixing-issues", action="store_true")

    args = parser.parse_args()

    if args.step < 1 or args.total_steps < 1:
        print("Error: step and total-steps must be >= 1", file=sys.stderr)
        sys.exit(1)

    min_steps = 4 if args.phase == "planning" else 3
    if args.total_steps < min_steps:
        print(f"Error: {args.phase} phase requires at least {min_steps} steps", file=sys.stderr)
        sys.exit(1)

    print(format_output(args.phase, args.step, args.total_steps,
                        args.qr_iteration, args.fixing_issues))


if __name__ == "__main__":
    main()
