#!/usr/bin/env python3
"""
Shared utilities for planner scripts.

QR Gate Pattern for Verification Loops:
  Every QR step is followed by a GATE step that:
  1. Takes --qr-status=pass|fail as input
  2. Outputs the EXACT next command to invoke
  3. Leaves no room for interpretation

  Work steps that follow a FAIL gate take --qr-fail flag to focus on fixing.

This pattern is applied consistently across:
  - planner.py (review phase: sequential QR with gates)
  - executor.py (step 4-5: holistic QR with gate)
  - execute-milestones.py (steps 2-3: batch QR with gate)
"""

from typing import Callable


def get_qr_state_banner(step_name: str, qr_iteration: int, fixing_issues: bool) -> list:
    """Generate the Three Pillars STATE BANNER for QR verification loops.

    Args:
        step_name: Name of the QR checkpoint (e.g., "PLAN QR", "HOLISTIC QR", "MILESTONE QR")
        qr_iteration: Loop iteration count (1 = initial, 2+ = re-verification)
        fixing_issues: Whether this invocation is fixing issues from previous QR

    Returns:
        List of strings to be included in script output
    """
    if qr_iteration == 1 and not fixing_issues:
        return [
            f"===[ {step_name}: INITIAL REVIEW ]===",
            "",
        ]
    else:
        return [
            f"===[ {step_name}: RE-VERIFICATION (iteration {qr_iteration}) ]===",
            "",
            "You previously fixed issues identified by QR.",
            "This invocation verifies those fixes were applied correctly.",
            "",
            "CRITICAL: QR MUST return PASS before you can proceed.",
            "",
        ]


def get_qr_stop_condition(gate_description: str, qr_iteration: int = 1) -> list:
    """Generate the Three Pillars STOP CONDITION block.

    Args:
        gate_description: What must happen before proceeding
            (e.g., "BOTH QR agents return PASS", "Milestone QR returns PASS")
        qr_iteration: Current QR loop iteration (for iteration limit check)

    Returns:
        List of strings to be included in script output
    """
    base_block = [
        "<stop_condition>",
        "STOP. You MUST NOT proceed until:",
        f"  1. {gate_description}",
        "  2. If QR returned ISSUES, you have FIXED them AND RE-RUN this step",
        "  3. Current QR result is PASS",
        "",
        "It is normal for QR to find issues on the first pass. Multiple QR",
        "iterations are expected behavior, not failure. Focus on addressing",
        "specific issues identified.",
        "",
        "Skipping re-verification after fixes is PROHIBITED.",
        "The QR agent exists to catch issues YOU cannot see in your own work.",
    ]

    # Add iteration limit guidance
    if qr_iteration >= 3:
        base_block.extend([
            "",
            "<iteration_limit_reached>",
            "ITERATION LIMIT: You have reached 3 QR iterations at this checkpoint.",
            "",
            "Use AskUserQuestion to present the situation:",
            "  question: 'QR has found issues across 3 iterations. How should we proceed?'",
            "  header: 'QR Loop'",
            "  options:",
            "    - label: 'Continue iterating'",
            "      description: 'Keep fixing issues until QR passes'",
            "    - label: 'Skip this check'",
            "      description: 'Accept current state, document remaining issues'",
            "    - label: 'Abort execution'",
            "      description: 'Stop and review the plan'",
            "",
            "If user selects 'Continue iterating': proceed with iteration 4+.",
            "If user selects 'Skip': document issues in retrospective and continue.",
            "If user selects 'Abort': stop execution and report status.",
            "</iteration_limit_reached>",
        ])
    else:
        base_block.extend([
            "",
            f"ITERATION LIMIT: Maximum 3 QR iterations before checkpoint.",
            f"Current iteration: {qr_iteration}. After 3 iterations, will ask user how to proceed.",
        ])

    base_block.append("</stop_condition>")
    return base_block


def format_restart_command(
    script: str,
    step_or_milestone: int,
    qr_iteration: int,
    thoughts_template: str,
    **extra_args: str | int | bool
) -> str:
    """Generate a restart command with Three Pillars flags.

    Plan file paths are not included in commands. The invoking agent knows
    the plan file path from context and substitutes $PLAN_FILE placeholders
    in delegation templates.

    Args:
        script: Script name (planner.py, executor.py, execute-milestone.py)
        step_or_milestone: Step or milestone number
        qr_iteration: Current iteration (will be incremented)
        thoughts_template: Template for --thoughts argument
        **extra_args: Additional CLI arguments

    Returns:
        Formatted command string
    """
    parts = [f"python3 {script}"]

    # Handle different argument names for different scripts
    if "execute-milestone" in script:
        parts.append(f"--milestone {step_or_milestone}")
        parts.append("--step 1")  # Always restart to implementation step
        parts.append("--fixing-qr-issues")
    else:
        parts.append(f"--step-number {step_or_milestone}")
        parts.append("--fixing-issues")

    parts.append(f"--qr-iteration {qr_iteration + 1}")

    for key, value in extra_args.items():
        arg_name = key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                parts.append(f"--{arg_name}")
        else:
            parts.append(f"--{arg_name} {value}")

    parts.append(f'--thoughts "{thoughts_template}"')

    return " \\\n    ".join(parts)


def format_qr_gate_output(
    gate_name: str,
    qr_status: str,
    script_name: str,
    pass_command: str | Callable[[], str],
    fail_command: str | Callable[[int], str],
    qr_iteration: int = 1,
    work_agent: str = "developer",
) -> str:
    """Generate QR gate step output with explicit routing.

    Gate steps are the ONLY place where QR results are interpreted.
    They output the EXACT command to invoke next, leaving no room
    for the main agent to interpret or take shortcuts.

    Args:
        gate_name: Name of this gate (e.g., "QR-COMPLETENESS", "QR-CODE", "WAVE QR")
        qr_status: "pass" or "fail" (from --qr-status argument)
        script_name: Script to invoke (e.g., "planner.py", "executor.py")
        pass_command: Command string or callable returning command if PASS
        fail_command: Command string or callable(qr_iteration) returning command if FAIL
        qr_iteration: Current QR iteration (1 = first attempt)
        work_agent: Agent that does the work on FAIL (for messaging)

    Returns:
        Formatted gate output string
    """
    lines = [
        f"QR GATE: {gate_name}",
        f"Result: {qr_status.upper()}",
        "",
    ]

    if qr_status.lower() == "pass":
        cmd = pass_command() if callable(pass_command) else pass_command
        lines.extend([
            "=" * 60,
            "GATE PASSED",
            "=" * 60,
            "",
            "NEXT (MANDATORY - invoke this exact command):",
            f"  {cmd}",
        ])
    else:
        # FAIL case
        next_iteration = qr_iteration + 1
        cmd = fail_command(next_iteration) if callable(fail_command) else fail_command

        lines.extend([
            "=" * 60,
            f"GATE FAILED (iteration {qr_iteration})",
            "=" * 60,
            "",
        ])

        # Add iteration limit check
        if next_iteration > 3:
            lines.extend([
                "<iteration_limit_reached>",
                f"QR has failed {qr_iteration} times at this checkpoint.",
                "",
                "Use AskUserQuestion:",
                "  question: 'QR has found issues across 3 iterations. How to proceed?'",
                "  header: 'QR Loop'",
                "  options:",
                "    - label: 'Continue iterating'",
                "      description: 'Keep fixing until QR passes'",
                "    - label: 'Skip this check'",
                "      description: 'Accept current state, note remaining issues'",
                "    - label: 'Abort'",
                "      description: 'Stop and review'",
                "</iteration_limit_reached>",
                "",
                "If user chooses 'Continue iterating':",
            ])

        lines.extend([
            "DELEGATION REQUIRED:",
            "  You are the ORCHESTRATOR. You NEVER fix code or docs yourself.",
            f"  Spawn {work_agent} agent with the QR findings.",
            f"  The {work_agent} will address the issues.",
            "",
            f"After {work_agent} completes, invoke this exact command:",
            f"  {cmd}",
            "",
            "FORBIDDEN:",
            "  - Using Edit/Write tools yourself",
            "  - Proceeding without re-running QR",
            "  - Interpreting 'minor issues' as skippable",
        ])

    return "\n".join(lines)


def get_iteration_limit_guidance(qr_iteration: int) -> list[str]:
    """Get guidance text for iteration limit scenarios.

    Args:
        qr_iteration: Current iteration number

    Returns:
        List of guidance lines (empty if under limit)
    """
    if qr_iteration < 3:
        return [
            f"Iteration: {qr_iteration}/3 (will ask user after 3 failures)",
        ]
    else:
        return [
            "<iteration_limit>",
            f"Iteration {qr_iteration}: User confirmation required.",
            "Use AskUserQuestion before proceeding.",
            "</iteration_limit>",
        ]
