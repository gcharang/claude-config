"""Plain text formatters for simple workflow output.

Used by skills that don't require XML structure (problem-analysis, decision-critic).
"""


def format_invoke_xml(cmd: str, working_dir: str = ".claude/skills/scripts") -> str:
    """Format command as XML invoke tag for cross-platform execution.

    Args:
        cmd: Command string to execute
        working_dir: Working directory relative to user home (default: .claude/skills/scripts)

    Returns:
        XML invoke tag string
    """
    return f'<invoke working-dir="{working_dir}" cmd="{cmd}" />'


def build_invoke_command(
    script: str,
    step: int,
    total_steps: int,
    as_xml: bool = True,
    **kwargs,
) -> str:
    """Build invoke command from structured parameters.

    Args:
        script: Module path (e.g., "skills.problem_analysis.analyze") or script path
        step: Step number
        total_steps: Total steps
        as_xml: Whether to wrap command in XML invoke tag (default: True)
        **kwargs: Additional CLI args (underscores converted to hyphens)

    Returns:
        Command string, optionally wrapped in XML invoke tag
    """
    # Use -m for module paths (contain dots but no slashes)
    if "." in script and "/" not in script and not script.endswith(".py"):
        parts = ["python3", "-m", script, f"--step {step}", f"--total-steps {total_steps}"]
    else:
        parts = ["python3", script, f"--step {step}", f"--total-steps {total_steps}"]
    for key, value in kwargs.items():
        arg_name = key.replace("_", "-")
        parts.append(f"--{arg_name} {value}")
    cmd = " ".join(parts)
    if as_xml:
        return format_invoke_xml(cmd)
    return cmd


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
    elif step >= total - 1:
        # step is 0-indexed, total is count; step 12 with total 13 is the last step
        lines.append("WORKFLOW COMPLETE - Present results to user.")
    elif next_title:
        lines.append(f"NEXT: Step {step + 1} - {next_title}")

    return "\n".join(lines)
