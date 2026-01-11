"""CLI utilities for workflow scripts.

Handles argument parsing and mode script entry points.
"""

import argparse
import sys
from pathlib import Path
from typing import Callable

from .formatters import format_step_output


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
            module_parts = list(parts[scripts_idx + 1:])
            module_parts[-1] = module_parts[-1].removesuffix(".py")
            return ".".join(module_parts)
    # Fallback: just use filename
    return path.stem


def add_qr_args(parser: argparse.ArgumentParser) -> None:
    """Add standard QR verification arguments to argument parser.

    Used by orchestrator scripts (planner.py, executor.py, wave-executor.py)
    to ensure consistent QR-related CLI flags.
    """
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", action="store_true",
                        help="Work step is fixing QR issues")
    parser.add_argument("--qr-status", type=str, choices=["pass", "fail"],
                        help="QR result for gate steps")


def mode_main(
    script_file: str,
    get_step_guidance: Callable[..., dict],
    description: str,
    extra_args: list[tuple[list, dict]] = None,
):
    """Standard entry point for mode scripts.

    Args:
        script_file: Pass __file__ from the calling script
        get_step_guidance: Function that returns guidance dict for each step
        description: Script description for --help
        extra_args: Additional arguments beyond standard QR args
    """
    script_name = Path(script_file).stem
    module_path = _compute_module_path(script_file)

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", action="store_true")
    for args, kwargs in (extra_args or []):
        parser.add_argument(*args, **kwargs)
    parsed = parser.parse_args()

    guidance = get_step_guidance(
        parsed.step, parsed.total_steps, module_path,
        **{k: v for k, v in vars(parsed).items()
           if k not in ('step', 'total_steps')}
    )

    # Handle both dict and dataclass (GuidanceResult) returns
    # Scripts use different patterns - some return dicts, others return GuidanceResult
    if hasattr(guidance, '__dataclass_fields__'):
        # GuidanceResult dataclass - convert to dict
        guidance_dict = {
            "title": guidance.title,
            "actions": guidance.actions,
            "next": guidance.next_command,
        }
    else:
        # Already a dict
        guidance_dict = guidance

    print(format_step_output(
        script=script_name,
        step=parsed.step,
        total=parsed.total_steps,
        title=guidance_dict["title"],
        actions=guidance_dict["actions"],
        next_command=guidance_dict["next"],
        is_step_one=(parsed.step == 1),
    ))
