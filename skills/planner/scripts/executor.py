#!/usr/bin/env python3
"""
Plan Executor - Execute approved plans through delegation.

Eight-step workflow:
  1. Execution Planning - analyze plan, detect reconciliation
  2. Reconciliation - validate existing code (conditional)
  3. Milestone Execution - delegate via execute-milestone.py
  4. Post-Implementation QR - holistic quality review
  5. QR Gate - route based on QR result
  6. Documentation - TW pass
  7. Retrospective - present summary

Usage:
    python3 executor.py --step 1 --total-steps 7
"""

import argparse
import sys

from utils import format_qr_gate_output, get_qr_state_banner


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
            "Expected output: PASS or ISSUES.",
        ],
    },
    # Step 5 is the gate - handled separately in format_output
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


def format_step_5_gate(qr_status: str, qr_iteration: int) -> str:
    """Format step 5 gate output using shared function."""
    pass_cmd = "python3 executor.py --step 6 --total-steps 7"

    def fail_cmd(iteration: int) -> str:
        return f"python3 executor.py --step 4 --total-steps 7 --qr-fail --qr-iteration {iteration}"

    return format_qr_gate_output(
        gate_name="HOLISTIC QR",
        qr_status=qr_status,
        script_name="executor.py",
        pass_command=pass_cmd,
        fail_command=fail_cmd,
        qr_iteration=qr_iteration,
        work_agent="developer",
    )


def format_output(step: int, total_steps: int,
                  qr_iteration: int, qr_fail: bool, qr_status: str,
                  reconciliation_check: bool, milestone_count: int) -> str:
    """Format output for display."""

    # Step 5 is the gate - uses shared function
    if step == 5:
        if not qr_status:
            return "Error: --qr-status required for step 5"
        return format_step_5_gate(qr_status, qr_iteration)

    info = STEPS.get(step, STEPS[7])
    is_complete = step >= total_steps

    lines = [
        f"EXECUTOR - Step {step}/{total_steps}: {info['title']}",
        "",
        "DO:",
    ]

    # Add QR banner for step 4
    if step == 4:
        banner = get_qr_state_banner("HOLISTIC QR", qr_iteration, qr_fail)
        for line in banner:
            if line:
                lines.append(f"  {line}")
        lines.append("")

    for action in info["actions"]:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

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
        lines.append("NEXT: Step 5 (QR Gate) with --qr-status pass|fail")
    else:
        lines.append(f"NEXT: Step {step + 1}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Plan Executor - Execute approved plans",
        epilog="Steps: plan -> reconcile -> execute -> QR -> gate -> docs -> retrospective",
    )

    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", action="store_true",
                        help="QR step is re-verifying after fixes")
    parser.add_argument("--qr-status", type=str, choices=["pass", "fail"],
                        help="QR result for gate step (step 5)")
    parser.add_argument("--reconciliation-check", action="store_true")
    parser.add_argument("--milestone-count", type=int, default=0)

    args = parser.parse_args()

    if args.step < 1 or args.step > 7:
        sys.exit("Error: step must be 1-7")

    if args.step == 5 and not args.qr_status:
        sys.exit("Error: --qr-status required for step 5")

    print(format_output(args.step, args.total_steps,
                        args.qr_iteration, args.qr_fail, args.qr_status,
                        args.reconciliation_check, args.milestone_count))


if __name__ == "__main__":
    main()
