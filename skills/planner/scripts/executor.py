#!/usr/bin/env python3
"""
Plan Executor - Execute approved plans through delegation.

Seven-step workflow:
  1. Execution Planning - analyze plan, detect reconciliation
  2. Reconciliation - validate existing code (conditional)
  3. Milestone Execution - delegate via execute-milestone.py
  4. Post-Implementation QR - holistic quality review
  5. QR Issue Resolution - fix issues (conditional)
  6. Documentation - TW pass
  7. Retrospective - present summary

Usage:
    python3 executor.py --step 1 --total-steps 7
"""

import argparse
import sys

from utils import get_qr_state_banner, get_qr_stop_condition


STEPS = {
    1: {
        "title": "Execution Planning",
        "actions": [
            "Plan file: $PLAN_FILE (substitute from context)",
            "",
            "ANALYZE plan:",
            "  - Count milestones and parse dependency diagram",
            "  - Group milestones into WAVES for execution",
            "  - Set up TodoWrite tracking",
            "",
            "WAVE ANALYSIS:",
            "  Parse the plan's 'Milestone Dependencies' diagram.",
            "  Group into waves: milestones at same depth = one wave.",
            "",
            "  Example diagram:",
            "    M0 (foundation)",
            "     |",
            "     +---> M1 (auth)     \\",
            "     |                    } Wave 2 (parallel)",
            "     +---> M2 (users)    /",
            "     |",
            "     +---> M3 (posts) ----> M4 (feed)",
            "            Wave 3          Wave 4",
            "",
            "  Output format:",
            "    Wave 1: [0]       (foundation, sequential)",
            "    Wave 2: [1, 2]    (parallel)",
            "    Wave 3: [3]       (sequential)",
            "    Wave 4: [4]       (sequential)",
            "",
            "WORKFLOW:",
            "  This step is ANALYSIS ONLY. Do NOT delegate yet.",
            "  Delegation happens via execute-milestones.py (see MANDATORY ACTION below).",
        ],
    },
    2: {
        "title": "Reconciliation",
        "actions": [
            "Validate existing code against plan requirements BEFORE executing.",
            "",
            "Use Task tool with subagent_type='quality-reviewer' for each milestone:",
            "  Mode: reconciliation",
            "  Check: Are acceptance criteria ALREADY satisfied?",
            "  Return: SATISFIED | NOT_SATISFIED | PARTIALLY_SATISFIED",
            "",
            "Routing:",
            "  SATISFIED -> Skip execution, record as complete",
            "  NOT_SATISFIED -> Execute milestone normally",
            "  PARTIALLY_SATISFIED -> Execute only missing parts",
        ],
    },
    3: {
        "title": "Wave Execution",
        "actions": [
            "Execute waves with batch QR after each wave.",
            "",
            "Use execute-milestones.py for each WAVE:",
            "  Step 1: Implementation (parallel Task calls for wave milestones)",
            "  Step 2: Batch QR (single QR reviews all wave milestones)",
            "  Step 3: Gate Check (proceed to next wave or fix)",
            "",
            "WAVE EXECUTION PATTERN:",
            "  Wave 1: [1,2] -> parallel dev -> batch QR -> PASS",
            "  Wave 2: [3]   -> dev -> batch QR -> PASS",
            "  Wave 3: [4]   -> dev -> batch QR -> PASS -> Step 4",
            "",
            "ERROR HANDLING (you NEVER fix code yourself):",
            "  Clear problem + solution: Task(developer) immediately",
            "  Difficult/unclear problem: Task(debugger) to diagnose, then Task(developer) to fix",
            "  Uncertain how to proceed: AskUserQuestion with options",
            "  Low (warnings): Note and continue",
        ],
    },
    4: {
        "title": "Post-Implementation QR",
        "actions": [
            "Use Task tool with subagent_type='quality-reviewer' for holistic review.",
            "  Mode: post-implementation",
            "  Files: [all modified files]",
            "",
            "Priority: reconciled milestones > new milestones > cross-cutting",
            "",
            "Expected output: PASS or issues sorted by severity.",
        ],
    },
    5: {
        "title": "QR Issue Resolution",
        "actions": [
            "Present issues to user, collect decisions, delegate fixes.",
            "",
            "For EACH issue:",
            "  Present: severity, category, file, problem, evidence",
            "  AskUserQuestion: Fix | Skip | Alternative",
            "",
            "After ALL decisions collected:",
            "  Execute fixes (parallelize where possible)",
            "  Return to step 4 for re-verification",
        ],
    },
    6: {
        "title": "Documentation",
        "actions": [
            "Use Task tool with subagent_type='technical-writer':",
            "  Mode: post-implementation",
            "  Files: [all modified files]",
            "",
            "Requirements:",
            "  - Create/update CLAUDE.md index entries",
            "  - Create README.md if warranted",
            "  - Add module-level docstrings where missing",
            "",
            "Skip if ALL milestones were documentation-only.",
        ],
    },
    7: {
        "title": "Retrospective",
        "actions": [
            "PRESENT retrospective to user (do not write to file):",
            "",
            "EXECUTION RETROSPECTIVE",
            "=======================",
            "Plan: [path]",
            "Status: COMPLETED | BLOCKED | ABORTED",
            "",
            "Milestone Outcomes: | Milestone | Status | Notes |",
            "Reconciliation Summary: [if run]",
            "Plan Accuracy Issues: [if any]",
            "Deviations from Plan: [if any]",
            "Quality Review Summary: [counts by category]",
            "Feedback for Future Plans: [actionable suggestions]",
        ],
    },
}


def format_output(step: int, total_steps: int,
                  qr_iteration: int, fixing_issues: bool,
                  reconciliation_check: bool, milestone_count: int) -> str:
    """Format output for display."""
    info = STEPS.get(step, STEPS[7])
    is_complete = step >= total_steps

    lines = [
        f"EXECUTOR - Step {step}/{total_steps}: {info['title']}",
        "",
        "DO:",
    ]

    # Add QR banner for step 4
    if step == 4:
        banner = get_qr_state_banner("HOLISTIC QR", qr_iteration, fixing_issues)
        stop = get_qr_stop_condition("Holistic QR returns PASS", qr_iteration)
        for line in banner:
            if line:
                lines.append(f"  {line}")
        lines.append("")

    for action in info["actions"]:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    if step == 4:
        lines.append("")
        for line in stop:
            if line:
                lines.append(f"  {line}")

    lines.append("")

    # Next step guidance
    if is_complete:
        lines.append("EXECUTION COMPLETE - Present retrospective to user.")
    elif step == 1:
        lines.append("")
        lines.append("=" * 70)
        lines.append("MANDATORY NEXT ACTION (DO NOT SKIP)")
        lines.append("=" * 70)
        if reconciliation_check:
            lines.append("RUN THIS COMMAND NOW:")
            lines.append(f"  python3 executor.py --step 2 --total-steps {total_steps} --reconciliation-check")
        else:
            lines.append("You MUST invoke execute-milestones.py for wave execution.")
            lines.append("DO NOT delegate directly. The script orchestrates dev/QR loops.")
            lines.append("")
            lines.append("RUN FIRST WAVE NOW:")
            if milestone_count > 0:
                lines.append(f"  python3 execute-milestones.py --milestones <wave1> --total-milestones {milestone_count} --step 1")
            else:
                lines.append("  python3 execute-milestones.py --milestones <wave1> --total-milestones N --step 1")
            lines.append("  (Replace <wave1> with first wave milestones, e.g., '1' or '1,2')")
        lines.append("")
        lines.append("After EACH wave completes, invoke next wave until all done.")
        lines.append("=" * 70)
    elif step == 3:
        lines.append("NEXT: Step 4 (Post-Implementation QR) after all waves complete")
    elif step == 4:
        lines.append("NEXT: Step 5 if ISSUES, Step 6 if PASS")
    elif step == 5:
        lines.append(f"NEXT: Return to Step 4 for re-verification (--qr-iteration {qr_iteration + 1})")
    else:
        lines.append(f"NEXT: Step {step + 1}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Plan Executor - Execute approved plans",
        epilog="Steps: plan -> reconcile -> execute -> QR -> fix -> docs -> retrospective",
    )

    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--fixing-issues", action="store_true")
    parser.add_argument("--reconciliation-check", action="store_true")
    parser.add_argument("--milestone-count", type=int, default=0)

    args = parser.parse_args()

    if args.step < 1 or args.step > 7:
        sys.exit("Error: step must be 1-7")

    print(format_output(args.step, args.total_steps,
                        args.qr_iteration, args.fixing_issues,
                        args.reconciliation_check, args.milestone_count))


if __name__ == "__main__":
    main()
