#!/usr/bin/env python3
"""
Wave Executor - Execute milestone waves with batch QR.

Three-step workflow per wave:
  1. Implementation - parallel delegation to @agent-developer (one per milestone)
  2. Batch QR - single @agent-quality-reviewer reviews all wave milestones
  3. Gate Check - route based on QR result (sequential fixes if issues)

Usage:
    python3 execute-milestones.py --milestones 1,2 --total-milestones 4 --step 1
    python3 execute-milestones.py --milestones 3 --total-milestones 4 --step 1
"""

import argparse
import sys

from utils import format_qr_gate_output, get_qr_state_banner


def parse_milestones(milestones_str: str) -> list[int]:
    """Parse comma-separated milestone list."""
    return [int(m.strip()) for m in milestones_str.split(",")]


def format_milestone_list(milestones: list[int]) -> str:
    """Format milestone list for display."""
    if len(milestones) == 1:
        return f"Milestone {milestones[0]}"
    return f"Milestones {', '.join(str(m) for m in milestones)}"


def get_step_1_guidance(milestones: list[int], total_milestones: int,
                        qr_fail: bool, qr_iteration: int) -> dict:
    """Step 1: Implementation (parallel for wave)."""
    ms_display = format_milestone_list(milestones)
    is_parallel = len(milestones) > 1

    actions = [
        f"Wave: {ms_display} (of {total_milestones} total)",
        "",
    ]

    if qr_fail or qr_iteration > 1:
        actions.extend([
            f"===[ QR FIX MODE (iteration {qr_iteration}) ]===",
            "Fix ONLY the issues QR flagged. Do NOT re-implement.",
            "Single developer fixes ALL issues sequentially.",
            "After fixing, MUST re-run Batch QR (step 2).",
            "======================================",
            "",
        ])

    actions.extend([
        "ROLE: ORCHESTRATOR. You delegate, you never implement.",
        "  Your agents are highly capable. Trust them with ANY issue.",
        "  PROHIBITED: Edit, Write tools. REQUIRED: Task(developer|debugger).",
        "",
    ])

    if is_parallel and not qr_fail:
        actions.extend([
            "PARALLEL EXECUTION:",
            f"  Spawn {len(milestones)} developer agents IN ONE MESSAGE:",
            "  (Multiple Task tool calls in single response)",
            "",
        ])
        for m in milestones:
            actions.append(f"  Task(developer): Milestone {m}")
        actions.extend([
            "",
            "  Each prompt must include:",
            "    - Plan file: $PLAN_FILE",
            "    - Milestone: [number and name]",
            "    - Files: [exact paths to create/modify]",
            "    - Acceptance criteria: [from plan]",
            "",
            "  Wait for ALL agents to complete before proceeding.",
        ])
    else:
        if qr_fail:
            actions.extend([
                "SEQUENTIAL FIX (single developer):",
                "  Use Task tool with subagent_type='developer'",
                "  Fix all QR issues in order. Developer has full context.",
                "",
            ])
        else:
            actions.extend([
                "IMPLEMENTATION:",
                "  Use Task tool with subagent_type='developer'",
                "",
                "  Prompt must include:",
                "    - Plan file: $PLAN_FILE",
                f"    - Milestone: {milestones[0]}",
                "    - Files: [exact paths to create/modify]",
                "    - Acceptance criteria: [from plan]",
                "",
            ])

    actions.extend([
        "After agent(s) complete, run tests:",
        "  pytest / tsc / go test -race",
        "  Pass criteria: 100% tests pass, zero warnings",
    ])

    return {
        "actions": actions,
        "next": "Step 2 (Batch QR)",
    }


def get_step_2_guidance(milestones: list[int], total_milestones: int,
                        qr_iteration: int) -> dict:
    """Step 2: Batch QR (reviews all wave milestones together)."""
    ms_display = format_milestone_list(milestones)
    banner = get_qr_state_banner(f"WAVE QR ({ms_display})", qr_iteration, qr_iteration > 1)

    actions = banner + [
        f"Wave: {ms_display} (of {total_milestones} total)",
        "",
        "Use Task tool with subagent_type='quality-reviewer':",
        "  Mode: batch-review",
        f"  Milestones: {milestones}",
        "  Files: [all files modified in this wave]",
        "",
        "QR validates (for ALL milestones in wave):",
        "  - Acceptance criteria met",
        "  - RULE 0: Production reliability",
        "  - RULE 1: Project conformance",
        "  - Cross-milestone consistency (if multiple)",
        "",
        "Expected: PASS or ISSUES",
    ]

    return {
        "actions": actions,
        "next": "Step 3 (Gate Check) with --qr-status pass|fail",
    }


def get_step_3_guidance(milestones: list[int], total_milestones: int,
                        qr_status: str, qr_iteration: int,
                        next_wave: str) -> str:
    """Step 3: Gate Check - uses shared gate function."""
    ms_display = format_milestone_list(milestones)
    ms_str = ",".join(str(m) for m in milestones)
    max_milestone = max(milestones)

    # Determine pass command
    if max_milestone < total_milestones:
        if next_wave:
            pass_cmd = (
                f"python3 execute-milestones.py --milestones {next_wave} "
                f"--total-milestones {total_milestones} --step 1"
            )
        else:
            pass_cmd = "Invoke next wave (from executor.py wave analysis)"
    else:
        pass_cmd = "python3 executor.py --step 5 --total-steps 8"

    # Determine fail command (takes iteration as parameter)
    def fail_cmd(iteration: int) -> str:
        return (
            f"python3 execute-milestones.py --milestones {ms_str} "
            f"--total-milestones {total_milestones} --step 1 "
            f"--qr-fail --qr-iteration {iteration}"
        )

    # Use shared gate function
    gate_output = format_qr_gate_output(
        gate_name=f"WAVE QR ({ms_display})",
        qr_status=qr_status,
        script_name="execute-milestones.py",
        pass_command=pass_cmd,
        fail_command=fail_cmd,
        qr_iteration=qr_iteration,
        work_agent="developer",
    )

    # Add wave progress header
    header = [
        f"Wave: {ms_display} (of {total_milestones} total)",
        f"Progress: {max_milestone}/{total_milestones} milestones",
        "",
    ]

    return "\n".join(header) + "\n" + gate_output


def format_output(step: int, milestones: list[int], total_milestones: int,
                  qr_status: str, qr_fail: bool, qr_iteration: int,
                  next_wave: str) -> str:
    """Format output for display."""
    step_names = {1: "Implementation", 2: "Batch QR", 3: "Gate Check"}
    ms_display = format_milestone_list(milestones)

    # Step 3 uses the gate function directly
    if step == 3:
        if not qr_status:
            return "Error: --qr-status required for step 3"
        return get_step_3_guidance(milestones, total_milestones, qr_status, qr_iteration, next_wave)

    # Steps 1 and 2 use the dict-based format
    if step == 1:
        guidance = get_step_1_guidance(milestones, total_milestones, qr_fail, qr_iteration)
    else:
        guidance = get_step_2_guidance(milestones, total_milestones, qr_iteration)

    lines = [
        f"WAVE ({ms_display}) - Step {step}/3: {step_names[step]}",
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
        description="Wave Executor - Execute milestone waves with batch QR",
        epilog="Steps: implement (parallel) -> batch QR -> gate check",
    )

    parser.add_argument("--milestones", type=str, required=True,
                        help="Comma-separated milestone numbers (e.g., '1,2,3')")
    parser.add_argument("--total-milestones", type=int, required=True)
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--qr-status", type=str, choices=["pass", "fail"],
                        help="QR result for gate step (step 3)")
    parser.add_argument("--qr-fail", action="store_true",
                        help="Work step is fixing QR issues")
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--next-wave", type=str, default="",
                        help="Next wave milestones (e.g., '3,4') for navigation")

    args = parser.parse_args()

    if args.step < 1 or args.step > 3:
        sys.exit("Error: step must be 1-3")

    if args.step == 3 and not args.qr_status:
        sys.exit("Error: --qr-status required for step 3")

    try:
        milestones = parse_milestones(args.milestones)
    except ValueError:
        sys.exit("Error: --milestones must be comma-separated integers (e.g., '1,2,3')")

    print(format_output(args.step, milestones, args.total_milestones,
                        args.qr_status, args.qr_fail, args.qr_iteration,
                        args.next_wave))


if __name__ == "__main__":
    main()
