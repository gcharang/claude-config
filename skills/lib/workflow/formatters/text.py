"""Plain text formatters for simple workflow output.

Used by skills that don't require XML structure (problem-analysis, decision-critic).
"""


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
) -> str:
    """Format complete plain text step output.

    Matches output format of problem-analysis and decision-critic skills.
    """
    lines = [format_text_step_header(step, total, title, brief), "", "DO:"]

    for action in actions:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    lines.append("")
    if step >= total:
        lines.append("COMPLETE - Present results to user.")
    elif next_title:
        lines.append(f"NEXT: Step {step + 1} - {next_title}")

    return "\n".join(lines)
