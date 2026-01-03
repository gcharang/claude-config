#!/usr/bin/env python3
"""
Per-Milestone Executor - Execute single milestones with QR gates.

Three-step workflow per milestone:
  Step 1: Implementation (delegate to @agent-developer)
  Step 2: QR Gate (delegate to @agent-quality-reviewer with mode: milestone-review)
  Step 3: Gate Check (route based on QR result)

Orchestrates incremental validation -- each milestone is QR'ed before proceeding to next.

Three Pillars Pattern for QR Verification Loops:
  1. STATE BANNER: Visual header showing loop iteration
  2. STOP CONDITION: Explicit blocker preventing progression
  3. RE-VERIFICATION MODE: Different prompts for first-run vs retry

Usage:
    # Start milestone implementation
    python3 execute-milestone.py --milestone 1 --total-milestones 3 --step 1 \\
      --thoughts "Starting implementation..."

    # After Developer completes, invoke QR
    python3 execute-milestone.py --milestone 1 --total-milestones 3 --step 2 \\
      --thoughts "Implementation complete, running QR gate..."

    # After QR completes, check gate decision
    python3 execute-milestone.py --milestone 1 --total-milestones 3 --step 3 \\
      --qr-result PASS --thoughts "QR passed, proceeding to next milestone"

    # If QR finds issues, retry implementation (with Three Pillars flags)
    python3 execute-milestone.py --milestone 1 --total-milestones 3 --step 1 \\
      --fixing-qr-issues --qr-iteration 2 --thoughts "Fixing QR issues: missing error handling"
"""

import argparse
import sys

from utils import get_qr_state_banner, get_qr_stop_condition


def get_step_1_guidance(milestone: int, total_milestones: int, plan_file: str,
                        fixing_qr_issues: bool, qr_iteration: int = 1) -> dict:
    """Step 1: Implementation - delegate to @agent-developer.

    Three Pillars Pattern applied when fixing_qr_issues=True:
      STATE BANNER shows this is a fix iteration
      RE-VERIFICATION MODE emphasizes QR must pass after fixes
    """
    actions = [
        "MILESTONE IMPLEMENTATION",
        "",
        f"Milestone: {milestone} of {total_milestones}",
        "",
    ]

    if fixing_qr_issues or qr_iteration > 1:
        # Three Pillars: Enhanced RE-VERIFICATION MODE banner
        actions.extend([
            f"===[ QR ISSUE RESOLUTION MODE (iteration {qr_iteration}) ]===",
            "",
            "The quality reviewer found issues in this milestone that must be fixed.",
            "QR findings are in the conversation context above.",
            "",
            "CRITICAL: After fixing, you MUST re-run QR (step 2) to verify fixes.",
            "Skipping re-verification is PROHIBITED.",
            "",
            "When delegating to @agent-developer:",
            "  1. Identify the specific issues from QR output",
            "  2. Provide clear guidance on what needs to be fixed",
            "  3. Reference the original milestone acceptance criteria",
            "  4. Emphasize that ONLY the identified issues should be addressed",
            "",
            "Do NOT re-implement the entire milestone -- fix only what QR flagged.",
            "",
            "======================================",
            "",
        ])

    actions.extend([
        "Delegate implementation to @agent-developer using this structure:",
        "",
        "<delegation_format>",
        "",
        "EVERY delegation MUST use this structure:",
        "",
        "  <delegation>",
        "    <agent>@agent-developer</agent>",
        f"    <plan_source>{plan_file}</plan_source>",
        "    <milestone>[Milestone number and name]</milestone>",
        "    <files>[Exact file paths from milestone]</files>",
        "    <task>[Specific task description]</task>",
        "    <acceptance_criteria>",
        "      - [Criterion 1 from plan]",
        "      - [Criterion 2 from plan]",
        "    </acceptance_criteria>",
        "  </delegation>",
        "",
        "</delegation_format>",
        "",
        "<diff_compliance>",
        "",
        "If milestone contains code changes with diffs:",
        "  - Verify context lines are VERBATIM from actual files",
        "  - Verify WHY comments explain rationale (not WHAT code does)",
        "  - Verify no location directives in comments",
        "",
        "After @agent-developer completes:",
        "  - Verify context lines from plan were found in target file",
        "  - Verify WHY comments were transcribed verbatim",
        "  - Verify no temporal contamination leaked",
        "",
        "</diff_compliance>",
        "",
        "<acceptance_testing>",
        "",
        "After implementation, run tests:",
        "",
        "  # Python",
        "  pytest --strict-markers --strict-config",
        "  mypy --strict",
        "",
        "  # JavaScript/TypeScript",
        "  tsc --strict --noImplicitAny",
        "  eslint --max-warnings=0",
        "",
        "  # Go",
        "  go test -race -cover -vet=all",
        "",
        "Pass criteria: 100% tests pass, zero linter warnings.",
        "",
        "</acceptance_testing>",
    ])

    next_step = (
        f"After @agent-developer completes and tests pass, invoke step 2:\n\n"
        f'  python3 execute-milestone.py --plan-file "{plan_file}" \\\n'
        f'    --milestone {milestone} --total-milestones {total_milestones} --step 2 \\\n'
        f'    --thoughts "Implementation complete. Modified files: [list]. Running QR gate..."'
    )

    return {
        "actions": actions,
        "next": next_step,
    }


def get_step_2_guidance(milestone: int, total_milestones: int, plan_file: str,
                        qr_iteration: int = 1) -> dict:
    """Step 2: QR Gate - delegate to @agent-quality-reviewer.

    Three Pillars Pattern applied:
      STATE BANNER shows iteration count
    """
    state_banner = get_qr_state_banner(f"MILESTONE {milestone} QR", qr_iteration, qr_iteration > 1)

    return {
        "actions": state_banner + [
            "MILESTONE QR GATE",
            "",
            f"Milestone: {milestone} of {total_milestones}",
            "",
            "Delegate to @agent-quality-reviewer for milestone validation.",
            "",
            "<qr_delegation>",
            "",
            "Task for @agent-quality-reviewer:",
            "  Mode: milestone-review",
            f"  Plan Source: {plan_file}",
            f"  Milestone: {milestone}",
            "  Files Modified: [list files modified in this milestone]",
            "",
            "QR will validate:",
            "  - Acceptance criteria met",
            "  - RULE 0: Production reliability (no crashes, data corruption, security holes)",
            "  - RULE 1: Project conformance (follows documented standards)",
            "",
            "NOTE: RULE 2 (structural quality) is SKIPPED at per-milestone level.",
            "Structural issues are caught in holistic post-implementation review.",
            "",
            "Expected output: PASS or ISSUES with specific findings.",
            "",
            "</qr_delegation>",
        ],
        "next": (
            f"After @agent-quality-reviewer completes, invoke step 3 with QR result:\n\n"
            f"If QR returns PASS:\n"
            f'  python3 execute-milestone.py --plan-file "{plan_file}" \\\n'
            f'    --milestone {milestone} --total-milestones {total_milestones} \\\n'
            f'    --step 3 --qr-result PASS --qr-iteration {qr_iteration} \\\n'
            f'    --thoughts "QR passed for milestone {milestone}"\n\n'
            f"If QR returns ISSUES:\n"
            f'  python3 execute-milestone.py --plan-file "{plan_file}" \\\n'
            f'    --milestone {milestone} --total-milestones {total_milestones} \\\n'
            f'    --step 3 --qr-result ISSUES --qr-iteration {qr_iteration} \\\n'
            f'    --thoughts "QR found issues: [summary]"'
        ),
    }


def get_step_3_guidance(milestone: int, total_milestones: int, plan_file: str,
                        qr_result: str, qr_iteration: int = 1) -> dict:
    """Step 3: Gate Check - route based on QR result.

    Three Pillars Pattern applied:
      STOP CONDITION ensures QR must pass before proceeding
    """
    stop_condition = get_qr_stop_condition(f"Milestone {milestone} QR returns PASS")

    if qr_result == "PASS":
        if milestone < total_milestones:
            # More milestones to execute
            next_milestone = milestone + 1
            next_step = (
                f"QR PASSED for milestone {milestone}.\n\n"
                f"Progress: {milestone}/{total_milestones} milestones complete.\n\n"
                f"Invoke next milestone:\n"
                f'  python3 execute-milestone.py --plan-file "{plan_file}" \\\n'
                f'    --milestone {next_milestone} --total-milestones {total_milestones} \\\n'
                f'    --step 1 --thoughts "Starting milestone {next_milestone}..."'
            )
            status = "milestone_complete"
        else:
            # All milestones complete, proceed to holistic QR
            next_step = (
                f"QR PASSED for milestone {milestone}.\n\n"
                f"ALL MILESTONES COMPLETE ({total_milestones}/{total_milestones}).\n\n"
                f"Invoke holistic quality review (executor step 4):\n"
                f'  python3 executor.py --plan-file "{plan_file}" \\\n'
                f'    --step-number 4 --total-steps 7 \\\n'
                f'    --thoughts "All milestones complete. Modified files: [list]. Running holistic QR."'
            )
            status = "all_milestones_complete"
        # No stop condition needed when PASS
        actions = [
            "GATE CHECK DECISION",
            "",
            f"Milestone: {milestone} of {total_milestones}",
            f"QR Result: {qr_result}",
            "",
        ]
    else:
        # QR found issues, retry implementation with Three Pillars flags
        next_step = (
            f"QR found ISSUES in milestone {milestone}.\n\n"
            f"Issues must be resolved before proceeding.\n\n"
            f"Retry implementation with fixes:\n"
            f'  python3 execute-milestone.py --plan-file "{plan_file}" \\\n'
            f'    --milestone {milestone} --total-milestones {total_milestones} \\\n'
            f'    --step 1 --fixing-qr-issues --qr-iteration {qr_iteration + 1} \\\n'
            f'    --thoughts "Fixing QR issues: [brief summary of issues]"\n\n'
            f"  CRITICAL: After fixing, you MUST re-run QR (step 2) to verify fixes.\n"
            f"  Skipping re-verification is PROHIBITED."
        )
        status = "in_progress"
        # Include stop condition when ISSUES - emphasizes the loop requirement
        actions = [
            "GATE CHECK DECISION",
            "",
            f"Milestone: {milestone} of {total_milestones}",
            f"QR Result: {qr_result}",
            "",
        ] + stop_condition

    return {
        "actions": actions,
        "next": next_step,
        "status": status,
    }


def get_step_guidance(step: int, milestone: int, total_milestones: int,
                      plan_file: str, qr_result: str, fixing_qr_issues: bool,
                      qr_iteration: int = 1) -> dict:
    """Route to appropriate step guidance."""
    if step == 1:
        return get_step_1_guidance(milestone, total_milestones, plan_file,
                                   fixing_qr_issues, qr_iteration)
    elif step == 2:
        return get_step_2_guidance(milestone, total_milestones, plan_file, qr_iteration)
    elif step == 3:
        if not qr_result:
            print("Error: --qr-result required for step 3", file=sys.stderr)
            sys.exit(1)
        return get_step_3_guidance(milestone, total_milestones, plan_file,
                                   qr_result, qr_iteration)
    else:
        return {
            "actions": [f"Unknown step {step}. Valid steps are 1-3."],
            "next": "Re-invoke with a valid step number.",
            "status": "error",
        }


def main():
    parser = argparse.ArgumentParser(
        description="Per-Milestone Executor - Execute single milestones with QR gates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start milestone implementation
  python3 execute-milestone.py --plan-file plans/auth.md \\
    --milestone 1 --total-milestones 3 --step 1 \\
    --thoughts "Starting implementation..."

  # After Developer completes
  python3 execute-milestone.py --plan-file plans/auth.md \\
    --milestone 1 --total-milestones 3 --step 2 \\
    --thoughts "Implementation complete, running QR gate..."

  # After QR passes
  python3 execute-milestone.py --plan-file plans/auth.md \\
    --milestone 1 --total-milestones 3 --step 3 \\
    --qr-result PASS --thoughts "QR passed, proceeding to next milestone"

  # If QR finds issues
  python3 execute-milestone.py --plan-file plans/auth.md \\
    --milestone 1 --total-milestones 3 --step 1 \\
    --fixing-qr-issues --thoughts "Fixing QR issues: missing error handling"
""",
    )

    parser.add_argument(
        "--plan-file", type=str, required=True, help="Path to the plan file"
    )
    parser.add_argument(
        "--milestone", type=int, required=True, help="Milestone number to execute"
    )
    parser.add_argument(
        "--total-milestones", type=int, required=True, help="Total number of milestones in plan"
    )
    parser.add_argument(
        "--step", type=int, required=True, help="Current step (1-3)"
    )
    parser.add_argument(
        "--qr-result",
        type=str,
        choices=["PASS", "ISSUES"],
        help="QR result (required for step 3)",
    )
    parser.add_argument(
        "--fixing-qr-issues",
        action="store_true",
        help="Flag indicating this is a retry after QR found issues",
    )
    # Three Pillars Pattern flag for QR verification loops
    parser.add_argument("--qr-iteration", type=int, default=1,
                        help="QR loop iteration (1=initial, 2+=re-verification)")
    parser.add_argument(
        "--thoughts", type=str, required=True, help="Your current thinking and status"
    )

    args = parser.parse_args()

    if args.step < 1 or args.step > 3:
        print("Error: step must be between 1 and 3", file=sys.stderr)
        sys.exit(1)

    if args.step == 3 and not args.qr_result:
        print("Error: --qr-result required for step 3", file=sys.stderr)
        sys.exit(1)

    guidance = get_step_guidance(
        args.step, args.milestone, args.total_milestones,
        args.plan_file, args.qr_result, args.fixing_qr_issues, args.qr_iteration
    )

    status = guidance.get("status", "in_progress")

    step_names = {
        1: "Implementation",
        2: "QR Gate",
        3: "Gate Check",
    }

    print("=" * 70)
    if args.qr_iteration > 1 or args.fixing_qr_issues:
        print(
            f"EXECUTE MILESTONE - Milestone {args.milestone}, Step {args.step} of 3: "
            f"{step_names.get(args.step, 'Unknown')} [QR iteration {args.qr_iteration}]"
        )
    else:
        print(
            f"EXECUTE MILESTONE - Milestone {args.milestone}, Step {args.step} of 3: "
            f"{step_names.get(args.step, 'Unknown')}"
        )
    print("=" * 70)
    print()
    print(f"STATUS: {status}")
    print()
    print("YOUR THOUGHTS:")
    print(args.thoughts)
    print()

    if guidance["actions"]:
        print("GUIDANCE:")
        print()
        for action in guidance["actions"]:
            print(action)
        print()

    print("NEXT:")
    print(guidance["next"])
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
