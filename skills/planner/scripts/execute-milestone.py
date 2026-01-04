#!/usr/bin/env python3
"""
Per-Milestone Executor - Execute single milestones with QR gates.

Three-step workflow per milestone:
  1. Implementation - delegate to @agent-developer
  2. QR Gate - delegate to @agent-quality-reviewer
  3. Gate Check - route based on QR result

Usage:
    python3 execute-milestone.py --milestone 1 --total-milestones 3 --step 1
"""

import argparse
import sys

from utils import get_qr_state_banner, get_qr_stop_condition


def get_step_1_guidance(milestone: int, total_milestones: int,
                        fixing_qr_issues: bool, qr_iteration: int) -> dict:
    """Step 1: Implementation."""
    actions = [
        f"Milestone: {milestone} of {total_milestones}",
        "",
    ]

    if fixing_qr_issues or qr_iteration > 1:
        actions.extend([
            f"===[ QR FIX MODE (iteration {qr_iteration}) ]===",
            "Fix ONLY the issues QR flagged. Do NOT re-implement entire milestone.",
            "After fixing, MUST re-run QR (step 2).",
            "======================================",
            "",
        ])

    actions.extend([
        "Delegate to @agent-developer:",
        "  <delegation>",
        "    <agent>@agent-developer</agent>",
        "    <plan_source>$PLAN_FILE</plan_source>",
        "    <milestone>[number and name]</milestone>",
        "    <files>[exact paths]</files>",
        "    <acceptance_criteria>[from plan]</acceptance_criteria>",
        "  </delegation>",
        "",
        "After implementation, run tests:",
        "  pytest / tsc / go test -race",
        "  Pass criteria: 100% tests pass, zero warnings",
    ])

    return {
        "actions": actions,
        "next": f"Step 2 (QR Gate)",
    }


def get_step_2_guidance(milestone: int, total_milestones: int,
                        qr_iteration: int) -> dict:
    """Step 2: QR Gate."""
    banner = get_qr_state_banner(f"MILESTONE {milestone} QR", qr_iteration, qr_iteration > 1)

    return {
        "actions": banner + [
            f"Milestone: {milestone} of {total_milestones}",
            "",
            "Delegate to @agent-quality-reviewer:",
            "  Mode: milestone-review",
            "  Files: [modified in this milestone]",
            "",
            "QR validates:",
            "  - Acceptance criteria met",
            "  - RULE 0: Production reliability",
            "  - RULE 1: Project conformance",
            "  (RULE 2 skipped - caught in holistic review)",
            "",
            "Expected: PASS or ISSUES",
        ],
        "next": "Step 3 (Gate Check) with --qr-result PASS|ISSUES",
    }


def get_step_3_guidance(milestone: int, total_milestones: int,
                        qr_result: str, qr_iteration: int) -> dict:
    """Step 3: Gate Check."""
    actions = [
        f"Milestone: {milestone} of {total_milestones}",
        f"QR Result: {qr_result}",
        "",
    ]

    if qr_result == "PASS":
        if milestone < total_milestones:
            next_step = (
                f"Milestone {milestone} PASSED. Progress: {milestone}/{total_milestones}\n"
                f"  python3 execute-milestone.py --milestone {milestone + 1} "
                f"--total-milestones {total_milestones} --step 1"
            )
        else:
            next_step = (
                f"ALL MILESTONES COMPLETE ({total_milestones}/{total_milestones})\n"
                f"  python3 executor.py --step 4 --total-steps 7"
            )
    else:
        stop = get_qr_stop_condition(f"Milestone {milestone} QR returns PASS", qr_iteration)
        actions.extend(stop)
        next_step = (
            f"FIX ISSUES then retry:\n"
            f"  python3 execute-milestone.py --milestone {milestone} "
            f"--total-milestones {total_milestones} --step 1 "
            f"--fixing-qr-issues --qr-iteration {qr_iteration + 1}"
        )

    return {
        "actions": actions,
        "next": next_step,
    }


def format_output(step: int, milestone: int, total_milestones: int,
                  qr_result: str, fixing_qr_issues: bool, qr_iteration: int) -> str:
    """Format output for display."""
    step_names = {1: "Implementation", 2: "QR Gate", 3: "Gate Check"}

    if step == 1:
        guidance = get_step_1_guidance(milestone, total_milestones, fixing_qr_issues, qr_iteration)
    elif step == 2:
        guidance = get_step_2_guidance(milestone, total_milestones, qr_iteration)
    else:
        if not qr_result:
            return "Error: --qr-result required for step 3"
        guidance = get_step_3_guidance(milestone, total_milestones, qr_result, qr_iteration)

    lines = [
        f"MILESTONE {milestone} - Step {step}/3: {step_names[step]}",
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
        description="Per-Milestone Executor",
        epilog="Steps: implement -> QR gate -> proceed or fix",
    )

    parser.add_argument("--milestone", type=int, required=True)
    parser.add_argument("--total-milestones", type=int, required=True)
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--qr-result", type=str, choices=["PASS", "ISSUES"])
    parser.add_argument("--fixing-qr-issues", action="store_true")
    parser.add_argument("--qr-iteration", type=int, default=1)

    args = parser.parse_args()

    if args.step < 1 or args.step > 3:
        sys.exit("Error: step must be 1-3")

    if args.step == 3 and not args.qr_result:
        sys.exit("Error: --qr-result required for step 3")

    print(format_output(args.step, args.milestone, args.total_milestones,
                        args.qr_result, args.fixing_qr_issues, args.qr_iteration))


if __name__ == "__main__":
    main()
