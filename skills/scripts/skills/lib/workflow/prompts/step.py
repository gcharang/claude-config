"""Step assembly for workflow prompts."""

import shlex
from pathlib import Path

# The uv project root (the directory holding pyproject.toml) above this package.
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

    Raises ValueError for a command that does not start with ``uv run``, since the
    working directory is pinned through uv's own ``--directory`` option.
    """
    if not command.startswith(_UV_RUN):
        raise ValueError(f"pin_cwd needs a `uv run` command, got {command!r}")
    return f"uv run --directory {_SKILLS_DIR_Q} {command[len(_UV_RUN) :]}"


def format_step(body: str, next_cmd: str = "", title: str = "") -> str:
    """Assemble complete workflow step: title + body + invoke directive.

    Args:
        body: Free-form prompt content (no wrapper needed)
        next_cmd: `uv run` command for next step (empty string signals completion)
        title: Optional title rendered as "TITLE\\n======\\n\\n" header

    Returns:
        Complete step output as plain text

    Raises:
        ValueError: from pin_cwd, for a next_cmd that is not `uv run`.
    """
    if title:
        header = f"{title}\n{'=' * len(title)}\n\n"
        body = header + body

    if next_cmd:
        # Working directory is explicit because CLI execution context varies; the
        # command itself carries it, so it runs from wherever the agent stands.
        invoke = (
            f"NEXT STEP:\n"
            f"    Working directory: {SKILLS_DIR}\n"
            f"    Command: {pin_cwd(next_cmd)}\n\n"
            f"Execute this command now."
        )
        return f"{body}\n\n{invoke}"

    return f"{body}\n\nWORKFLOW COMPLETE - Return the output from the step above. Do not summarize."
