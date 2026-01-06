#!/usr/bin/env python3
"""
Wave Executor - Execute milestone waves with batch QR.

Three-step workflow per wave:
  1. Implementation - parallel delegation to @agent-developer (one per milestone)
  2. Batch QR - single @agent-quality-reviewer reviews all wave milestones
  3. Gate Check - route based on QR result (sequential fixes if issues)

Usage:
    python3 wave-executor.py --milestones 1,2 --total-milestones 4 --step 1
    python3 wave-executor.py --milestones 3 --total-milestones 4 --step 1
"""

import argparse
import sys

from shared import (
    QRState,
    get_mode_script_path,
    get_reverification_context,
    format_step_output,
    format_gate_actions,
    format_subagent_dispatch,
    format_state_banner,
    format_post_qr_routing,
    format_orchestrator_constraint,
    add_qr_args,
)


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
        banner = format_state_banner(
            "QR_FIX_MODE", qr_iteration, "fixing",
            [
                "Fix ONLY the issues QR flagged. Do NOT re-implement.",
                "Single developer fixes ALL issues sequentially.",
                "After fixing, MUST re-run Batch QR (step 2).",
            ]
        )
        actions.append(banner)
        actions.append("")

    actions.append(format_orchestrator_constraint())
    actions.append("")

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
    ms_list = ", ".join(str(m) for m in milestones)
    ms_str = ",".join(str(m) for m in milestones)
    mode_script = get_mode_script_path("qr/batch-review.py")

    # Build state banner using XML format
    qr_name = f"WAVE QR ({ms_display})"
    if qr_iteration == 1:
        banner = format_state_banner(qr_name, qr_iteration, "initial_review")
    else:
        banner = format_state_banner(
            qr_name, qr_iteration, "re_verification",
            get_reverification_context()
        )

    actions = [
        banner,
        "",
        f"Wave: {ms_display} (of {total_milestones} total)",
        "",
        format_orchestrator_constraint(),
        "",
    ]

    # Generate dispatch block using XML format
    dispatch_block = format_subagent_dispatch(
        agent="quality-reviewer",
        context_vars={
            "PLAN_FILE": "path to the executed plan",
            "MILESTONES": f"[{ms_list}]",
            "MODIFIED_FILES": "actual file paths from wave milestones",
        },
        invoke_cmd=f"python3 {mode_script} --step 1 --total-steps 5",
    )
    actions.append(dispatch_block)
    actions.extend([
        "",
        "The sub-agent will invoke the script and follow its guidance.",
        "",
        "Expected output: PASS or ISSUES",
    ])

    # Add post-QR routing block
    routing_block = format_post_qr_routing(self_fix=False, fix_target="developer")
    actions.append(routing_block)

    # Return branching commands
    base_cmd = f"python3 wave-executor.py --milestones {ms_str} --total-milestones {total_milestones} --step 3"
    return {
        "actions": actions,
        "if_pass": f"{base_cmd} --qr-status pass",
        "if_fail": f"{base_cmd} --qr-status fail",
    }


def get_step_3_guidance(milestones: list[int], total_milestones: int,
                        qr: QRState, next_wave: str) -> dict:
    """Step 3: Gate Check - returns dict for format_step_output."""
    ms_display = format_milestone_list(milestones)
    ms_str = ",".join(str(m) for m in milestones)
    max_milestone = max(milestones)

    # Build gate result
    if qr.status and qr.status.lower() == "pass":
        gate_result = ("pass", "GATE PASSED")
    else:
        gate_result = ("fail", f"GATE FAILED (iteration {qr.iteration})")

    # Build pass message based on wave progress
    if max_milestone < total_milestones:
        pass_message = "Proceed to next wave."
    else:
        pass_message = "All waves complete. Proceed to holistic QR."

    # Build actions using format_gate_actions helper
    actions = [
        f"Wave: {ms_display} (of {total_milestones} total)",
        f"Progress: {max_milestone}/{total_milestones} milestones",
        "",
    ]
    actions.extend(format_gate_actions(
        qr=qr,
        pass_message=pass_message,
        self_fix=False,
        fix_target="developer",
    ))

    # Determine pass command
    pass_cmd = None
    if max_milestone < total_milestones:
        if next_wave:
            pass_cmd = (
                f"python3 wave-executor.py --milestones {next_wave} "
                f"--total-milestones {total_milestones} --step 1"
            )
        else:
            actions.append("")
            actions.append("Next wave milestones not specified. Determine from executor.py wave analysis.")
    else:
        pass_cmd = "python3 executor.py --step 4 --total-steps 7"

    # Determine fail command
    next_iteration = qr.iteration + 1
    fail_cmd = (
        f"python3 wave-executor.py --milestones {ms_str} "
        f"--total-milestones {total_milestones} --step 1 "
        f"--qr-fail --qr-iteration {next_iteration}"
    )

    # Return dict - pass_cmd or fail_cmd based on status
    if qr.status and qr.status.lower() == "pass" and pass_cmd:
        return {
            "title": f"Wave QR Gate ({ms_display})",
            "actions": actions,
            "gate_result": gate_result,
            "next": pass_cmd,
        }
    elif qr.status and qr.status.lower() == "fail":
        return {
            "title": f"Wave QR Gate ({ms_display})",
            "actions": actions,
            "gate_result": gate_result,
            "next": fail_cmd,
        }
    else:
        # Pass but no pass_cmd (manual wave determination needed)
        return {
            "title": f"Wave QR Gate ({ms_display})",
            "actions": actions,
            "gate_result": gate_result,
        }


def format_output(step: int, milestones: list[int], total_milestones: int,
                  qr_status: str, qr_fail: bool, qr_iteration: int,
                  next_wave: str) -> str:
    """Format output for display using XML format."""
    ms_display = format_milestone_list(milestones)
    ms_str = ",".join(str(m) for m in milestones)

    # Construct QRState from legacy parameters
    qr = QRState(iteration=qr_iteration, failed=qr_fail, status=qr_status)

    # All steps now use format_step_output consistently
    if step == 1:
        guidance = get_step_1_guidance(milestones, total_milestones, qr_fail, qr_iteration)
        next_command = f"python3 wave-executor.py --milestones {ms_str} --total-milestones {total_milestones} --step 2"
        return format_step_output(
            script="wave-executor",
            step=step,
            total=3,
            title=f"Implementation ({ms_display})",
            actions=guidance["actions"],
            next_command=next_command,
            is_step_one=True,
        )
    elif step == 2:
        guidance = get_step_2_guidance(milestones, total_milestones, qr_iteration)
        return format_step_output(
            script="wave-executor",
            step=step,
            total=3,
            title=f"Batch QR ({ms_display})",
            actions=guidance["actions"],
            if_pass=guidance.get("if_pass"),
            if_fail=guidance.get("if_fail"),
            is_step_one=False,
        )
    else:  # step == 3
        if not qr_status:
            return "Error: --qr-status required for step 3"
        guidance = get_step_3_guidance(milestones, total_milestones, qr, next_wave)
        return format_step_output(
            script="wave-executor",
            step=step,
            total=3,
            title=guidance["title"],
            actions=guidance["actions"],
            next_command=guidance.get("next"),
            gate_result=guidance.get("gate_result"),
            is_step_one=False,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Wave Executor - Execute milestone waves with batch QR",
        epilog="Steps: implement (parallel) -> batch QR -> gate check",
    )

    parser.add_argument("--milestones", type=str, required=True,
                        help="Comma-separated milestone numbers (e.g., '1,2,3')")
    parser.add_argument("--total-milestones", type=int, required=True)
    parser.add_argument("--step", type=int, required=True)
    add_qr_args(parser)
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
