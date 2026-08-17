"""CLI utilities for workflow scripts.

Handles argument parsing and mode script entry points.
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .prompts.step import format_step
from .types import UserInputResponse


def _compute_module_path(script_file: str) -> str:
    """Compute module path from script file path.

    Args:
        script_file: Absolute path to script (e.g., ~/.claude/skills/scripts/skills/planner/qr/plan_completeness.py)

    Returns:
        Module path for -m invocation (e.g., skills.planner.qr.plan_completeness)
    """
    path = Path(script_file).resolve()
    parts = path.parts
    # Find 'scripts' in path and extract module path after it
    if "scripts" in parts:
        scripts_idx = parts.index("scripts")
        if scripts_idx + 1 < len(parts):
            module_parts = list(parts[scripts_idx + 1 :])
            module_parts[-1] = module_parts[-1].removesuffix(".py")
            return ".".join(module_parts)
    # Fallback: just use filename
    return path.stem


def add_standard_args(parser: argparse.ArgumentParser) -> None:
    """Add standard workflow arguments."""
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", type=str, default=None)
    parser.add_argument("--user-answer-id", type=str, help="Question ID that was answered")
    parser.add_argument(
        "--user-answer-value", type=str, help="User's selected option or custom text"
    )


def get_user_answer(args) -> UserInputResponse | None:
    """Extract user answer from parsed args."""
    if args.user_answer_id and args.user_answer_value:
        return UserInputResponse(
            question_id=args.user_answer_id,
            selected=args.user_answer_value,
        )
    return None


def render_step(guidance: dict) -> str:
    """Assemble a step's printable output: body + cd-pinned NEXT STEP footer.

    Shared by mode_main and the QR verify entry point so both render steps
    identically; the trailing invoke directive (with its absolute cd) is
    supplied by format_step.
    """
    body = "\n".join(str(action) for action in guidance["actions"])
    return format_step(body, guidance.get("next", ""), title=guidance["title"])


def mode_main(
    script_file: str,
    get_step_guidance: Callable[..., dict],
    description: str,
    extra_args: list[tuple[list, dict]] | None = None,
    pre_dispatch: Callable[[argparse.Namespace], bool] | None = None,
):
    """Standard entry point for mode scripts.

    Args:
        script_file: Pass __file__ from the calling script
        get_step_guidance: Function that returns guidance dict for each step
        description: Script description for --help
        extra_args: Additional arguments beyond standard QR args
        pre_dispatch: Optional hook called immediately after parse_args().
            When it returns True, mode_main returns early (used by verify_main
            to intercept --result flags before the --step requirement check).
    """
    module_path = _compute_module_path(script_file)

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--step", type=int, default=None)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", type=str, default=None)
    for args, kwargs in extra_args or []:
        parser.add_argument(*args, **kwargs)
    parsed = parser.parse_args()

    if pre_dispatch and pre_dispatch(parsed):
        return

    if parsed.step is None:
        parser.error("--step is required")

    guidance = get_step_guidance(
        parsed.step, module_path, **{k: v for k, v in vars(parsed).items() if k not in ("step",)}
    )

    # Handle both dict and dataclass (GuidanceResult) returns
    if isinstance(guidance, dict):
        guidance_dict = guidance
    else:
        guidance_dict = {
            "title": guidance.title,
            "actions": guidance.actions,
            "next": guidance.next_command,
        }

    # Router scripts signal invalid input by returning {"error": msg}.
    # Without this check, the downstream guidance_dict["title"]/["actions"]
    # lookups raise KeyError with a traceback instead of a clean exit.
    if "error" in guidance_dict:
        print(f"Error: {guidance_dict['error']}", file=sys.stderr)
        sys.exit(1)

    print(render_step(guidance_dict))
