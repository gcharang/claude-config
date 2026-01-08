"""Plain text formatters for simple workflow output.

Used by skills that don't require XML structure (problem-analysis, decision-critic).
"""


def build_invoke_command(
    script: str,
    step: int,
    total_steps: int,
    **kwargs,
) -> str:
    """Build invoke command from structured parameters.

    Args:
        script: Script path (e.g., "scripts/analyze.py")
        step: Step number
        total_steps: Total steps
        **kwargs: Additional CLI args (underscores converted to hyphens)

    Examples:
        build_invoke_command("scripts/analyze.py", 3, 5)
        # -> "python3 scripts/analyze.py --step 3 --total-steps 5"

        build_invoke_command("scripts/analyze.py", 3, 5,
                            confidence="<your_confidence>", iteration=3)
        # -> "python3 scripts/analyze.py --step 3 --total-steps 5 ..."
    """
    parts = ["python3", script, f"--step {step}", f"--total-steps {total_steps}"]
    for key, value in kwargs.items():
        arg_name = key.replace("_", "-")
        parts.append(f"--{arg_name} {value}")
    return " ".join(parts)


def format_text_step_header(step: int, total: int, title: str, brief: str = None) -> str:
    """Format a plain text step header.

    Args:
        step: Current step number
        total: Total steps
        title: Step title
        brief: Optional brief description

    Returns:
        Plain text header string
    """
    lines = [f"STEP {step}/{total}: {title}"]
    if brief:
        lines.append(f"  {brief}")
    return "\n".join(lines)


def format_text_output(
    step: int,
    total: int,
    title: str,
    actions: list[str],
    brief: str = None,
    next_title: str = None,
    invoke_after: str = None,
) -> str:
    """Format complete plain text step output.

    Matches output format of problem-analysis and decision-critic skills.

    Args:
        step: Current step number
        total: Total steps
        title: Step title
        actions: List of action strings
        brief: Optional brief description
        next_title: Title for next step (used if invoke_after not provided)
        invoke_after: Explicit command to invoke after (takes precedence)
    """
    lines = [format_text_step_header(step, total, title, brief), "", "DO:"]

    for action in actions:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    lines.append("")
    if invoke_after:
        lines.append(f"INVOKE AFTER: {invoke_after}")
    elif step >= total:
        lines.append("COMPLETE - Present results to user.")
    elif next_title:
        lines.append(f"NEXT: Step {step + 1} - {next_title}")

    return "\n".join(lines)
