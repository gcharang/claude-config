#!/usr/bin/env python3
"""
Shared utilities for planner scripts.

Three Pillars Pattern for QR Verification Loops:
  1. STATE BANNER: Visual header showing loop iteration
  2. STOP CONDITION: Explicit blocker preventing progression
  3. RE-VERIFICATION MODE: Different prompts for first-run vs retry

This pattern is applied consistently across:
  - planner.py (review phase steps 1 and 3)
  - executor.py (step 4: holistic QR)
  - execute-milestone.py (steps 2-3: per-milestone QR)
"""


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
