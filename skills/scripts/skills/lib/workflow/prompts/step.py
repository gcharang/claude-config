"""Step assembly for workflow prompts."""

import shlex
from pathlib import Path

# .parent x5 traverses prompts/ -> workflow/ -> lib/ -> skills/ -> scripts/
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
_SKILLS_DIR_Q = shlex.quote(str(SKILLS_DIR))
_UV_RUN = "uv run "


def pin_cwd(command: str) -> str:
    """Make a ``uv run`` command cwd-independent: ``uv run --directory <SKILLS_DIR> ...``.

    A bare ``uv run python -m skills...`` fails with "No module named 'skills'" when
    the agent's cwd has drifted (e.g. into a /tmp state dir). uv's own ``--directory``
    changes into SKILLS_DIR before it resolves the project and runs the command, so
    the agent never has to ``cd`` in a command that also does something else;
    ``--project`` alone would leave the working directory where it is.

    Raises ValueError for a command that does not start with ``uv run``: no other
    command carries its own working-directory option here.
    """
    if not command.startswith(_UV_RUN):
        raise ValueError(f"pin_cwd needs a `uv run` command, got {command!r}")
    return f"uv run --directory {_SKILLS_DIR_Q} {command[len(_UV_RUN) :]}"


def format_step(
    body: str, next_cmd: str = "", title: str = "", if_pass: str = "", if_fail: str = ""
) -> str:
    """Assemble complete workflow step: title + body + invoke directive.

    Args:
        body: Free-form prompt content (no wrapper needed)
        next_cmd: `uv run` command for next step (empty string signals completion)
        title: Optional title rendered as "TITLE\\n======\\n\\n" header
        if_pass: Branching `uv run` command when QR gate passes
        if_fail: Branching `uv run` command when QR gate fails

    Returns:
        Complete step output as plain text

    Raises:
        ValueError: if exactly one of if_pass/if_fail is set, or if branching
            (if_pass/if_fail) is mixed with next_cmd. Both combinations would
            silently mis-render -- a lone if_pass falls through to "WORKFLOW
            COMPLETE", and branch+next_cmd silently drops next_cmd. Fail loud
            instead. Also raised, by pin_cwd, for a command that is not `uv run`.
    """
    if bool(if_pass) != bool(if_fail):
        raise ValueError(
            "format_step: if_pass and if_fail must be provided together (branching requires both)"
        )
    if (if_pass or if_fail) and next_cmd:
        raise ValueError(
            "format_step: branching (if_pass/if_fail) and next_cmd are mutually exclusive"
        )

    if title:
        header = f"{title}\n{'=' * len(title)}\n\n"
        body = header + body

    if if_pass and if_fail:
        # Branching invoke for QR gate routing: the LLM chooses based on
        # aggregated QR outcome (all pass vs any fail).
        invoke = (
            f"NEXT STEP (MANDATORY -- execute exactly one):\n"
            f"    Working directory: {SKILLS_DIR}\n"
            f"    ALL agents returned PASS  ->  {pin_cwd(if_pass)}\n"
            f"    ANY agent returned FAIL   ->  {pin_cwd(if_fail)}\n\n"
            f"This is a mechanical routing decision. Do not interpret, summarize, "
            f"or assess the results.\n"
            f"Count PASS vs FAIL, then execute the matching command."
        )
        return f"{body}\n\n{invoke}"

    elif next_cmd:
        # Working directory is explicit because CLI execution context varies; the
        # command itself carries it, so it runs from wherever the agent stands.
        invoke = (
            f"NEXT STEP:\n"
            f"    Working directory: {SKILLS_DIR}\n"
            f"    Command: {pin_cwd(next_cmd)}\n\n"
            f"Execute this command now."
        )
        return f"{body}\n\n{invoke}"

    else:
        return f"{body}\n\nWORKFLOW COMPLETE - Return the output from the step above. Do not summarize."
