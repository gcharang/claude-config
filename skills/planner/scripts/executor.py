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

from shared import (
    QRState,
    GateConfig,
    get_mode_script_path,
    get_reverification_context,
    format_step_output,
    format_gate_step,
    format_invoke_after,
    format_step_header,
    format_current_action,
    format_subagent_dispatch,
    format_state_banner,
    format_routing,
    format_post_qr_routing,
    format_orchestrator_constraint,
    format_qr_banner,
    add_qr_args,
)


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
            "  Delegation happens via wave-executor.py (see MANDATORY ACTION below).",
        ],
    },
    2: {
        "title": "Reconciliation",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/reconciliation.py",
        "mode_total_steps": 4,
        "context_vars": {
            "PLAN_FILE": "path to the plan being executed",
            "N": "milestone number (run once per milestone)",
        },
        "invoke_suffix": " --milestone N",
        "pre_dispatch": [
            "Validate existing code against plan requirements BEFORE executing.",
            "",
            "For EACH milestone, launch quality-reviewer agent:",
        ],
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: SATISFIED | NOT_SATISFIED | PARTIALLY_SATISFIED",
        ],
        "routing": {
            "SATISFIED": "Mark milestone complete, skip execution",
            "NOT_SATISFIED": "Execute milestone normally",
            "PARTIALLY_SATISFIED": "Execute only missing parts",
        },
        "extra_instructions": [
            "",
            "Parallel execution: May run reconciliation for multiple milestones",
            "in parallel (multiple Task calls in single response) when milestones",
            "are independent.",
        ],
    },
    3: {
        "title": "Wave Execution",
        "actions": [
            "Execute waves with batch QR after each wave.",
            "",
            "Use wave-executor.py for each WAVE:",
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
        "is_qr": True,
        "qr_name": "HOLISTIC QR",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/post-impl.py",
        "mode_total_steps": 6,
        "context_vars": {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from all milestones",
        },
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES.",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "developer"},
    },
    # Step 5 is the gate - handled separately in format_output
    6: {
        "title": "Documentation",
        "is_dispatch": True,
        "dispatch_agent": "technical-writer",
        "mode_script": "tw/post-impl.py",
        "mode_total_steps": 6,
        "context_vars": {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
        },
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: Documentation report format",
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


# Gate configuration for step 5 (Holistic QR Gate)
EXECUTOR_GATE = GateConfig(
    qr_name="Holistic QR",
    work_step=4,
    pass_step=6,
    pass_message="Proceed to documentation step.",
    self_fix=False,
    fix_target="developer",
)


def format_step_5_gate(qr: QRState) -> str:
    """Format step 5 gate output using XML format."""
    return format_gate_step(
        script="executor",
        step=5,
        total=7,
        gate=EXECUTOR_GATE,
        qr=qr,
        cmd_template="python3 executor.py",
    )


def format_output(step: int, total_steps: int,
                  qr_iteration: int, qr_fail: bool, qr_status: str,
                  reconciliation_check: bool, milestone_count: int) -> str:
    """Format output for display using XML format."""

    # Construct QRState from legacy parameters
    qr = QRState(iteration=qr_iteration, failed=qr_fail, status=qr_status)

    # Step 5 is the gate - uses dedicated gate formatter
    if step == 5:
        if not qr_status:
            return "Error: --qr-status required for step 5"
        return format_step_5_gate(qr)

    info = STEPS.get(step, STEPS[7])
    is_complete = step >= total_steps

    # Build actions
    actions = []

    # Add QR banner for QR steps using XML format
    if info.get("is_qr"):
        qr_name = info.get("qr_name", "QR")
        actions.append(format_qr_banner(qr_name, qr))
        actions.append("")

    # Handle dispatch steps with new structure
    if info.get("is_dispatch"):
        # Add pre-dispatch instructions
        pre_dispatch = info.get("pre_dispatch", [])
        actions.extend(pre_dispatch)

        # Add orchestrator constraint before dispatch
        actions.append(format_orchestrator_constraint())
        actions.append("")

        # Generate dispatch block
        mode_script = get_mode_script_path(info["mode_script"])
        mode_total_steps = info.get("mode_total_steps", 5)
        dispatch_agent = info.get("dispatch_agent", "agent")
        context_vars = info.get("context_vars", {})
        invoke_suffix = info.get("invoke_suffix", "")

        dispatch_block = format_subagent_dispatch(
            agent=dispatch_agent,
            context_vars=context_vars,
            invoke_cmd=f"python3 {mode_script} --step 1 --total-steps {mode_total_steps}{invoke_suffix}",
        )
        actions.append(dispatch_block)
        actions.append("")

        # Add post-dispatch instructions
        post_dispatch = info.get("post_dispatch", [])
        actions.extend(post_dispatch)

        # Add post-QR routing block for QR steps
        post_qr_config = info.get("post_qr_routing")
        if post_qr_config:
            routing_block = format_post_qr_routing(
                self_fix=post_qr_config.get("self_fix", False),
                fix_target=post_qr_config.get("fix_target", "developer"),
            )
            actions.append(routing_block)

        # Add routing block if present
        routing = info.get("routing")
        if routing:
            actions.append("")
            actions.append(format_routing(routing))

        # Add extra instructions if present
        extra_instructions = info.get("extra_instructions", [])
        actions.extend(extra_instructions)
    elif "actions" in info:
        # Non-dispatch step with explicit actions
        actions.extend(info["actions"])

    # Build next command(s)
    next_command = None
    if_pass = None
    if_fail = None

    if is_complete:
        # Final step - no invoke_after, just present retrospective
        actions.append("")
        actions.append("EXECUTION COMPLETE - Present retrospective to user.")
    elif step == 1:
        # Step 1 has special guidance embedded in actions
        actions.extend([
            "",
            "=" * 70,
            "MANDATORY NEXT ACTION (DO NOT SKIP)",
            "=" * 70,
        ])
        if reconciliation_check:
            next_command = f"python3 executor.py --step 2 --total-steps {total_steps} --reconciliation-check"
        else:
            actions.extend([
                "You MUST invoke wave-executor.py for wave execution.",
                "DO NOT delegate directly. The script orchestrates dev/QR loops.",
                "",
                "After EACH wave completes, invoke next wave until all done.",
                "=" * 70,
            ])
            if milestone_count > 0:
                next_command = f"python3 wave-executor.py --milestones <wave1> --total-milestones {milestone_count} --step 1"
            else:
                next_command = "python3 wave-executor.py --milestones <wave1> --total-milestones N --step 1"
    elif step == 3:
        next_command = "python3 executor.py --step 4 --total-steps 7"
    elif step == 4:
        # QR step uses branching
        if_pass = f"python3 executor.py --step 5 --total-steps {total_steps} --qr-status pass"
        if_fail = f"python3 executor.py --step 5 --total-steps {total_steps} --qr-status fail"
    else:
        next_command = f"python3 executor.py --step {step + 1} --total-steps {total_steps}"

    return format_step_output(
        script="executor",
        step=step,
        total=total_steps,
        title=info["title"],
        actions=actions,
        next_command=next_command,
        if_pass=if_pass,
        if_fail=if_fail,
        is_step_one=(step == 1),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Plan Executor - Execute approved plans",
        epilog="Steps: plan -> reconcile -> execute -> QR -> gate -> docs -> retrospective",
    )

    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    add_qr_args(parser)
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
