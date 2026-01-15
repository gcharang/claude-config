"""CLI utilities for workflow scripts.

Handles argument parsing and mode script entry points.
"""

import argparse
import sys
from pathlib import Path
from typing import Callable

from .ast import W, XMLRenderer, render, TextNode


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

    # Build step output using AST builder
    parts = []
    parts.append(render(
        W.el("step_header", TextNode(guidance_dict["title"]),
             script=script_name, step=str(parsed.step), total=str(parsed.total_steps)
        ).build(), XMLRenderer()
    ))
    if parsed.step == 1:
        parts.append("")
        parts.append("<xml_format_mandate>")
        parts.append("  All workflow output MUST be well-formed XML.")
        parts.append("  Use CDATA for code: <![CDATA[...]]>")
        parts.append("</xml_format_mandate>")
        parts.append("")
        parts.append("<thinking_efficiency>")
        parts.append("Max 5 words per step. Symbolic notation preferred.")
        parts.append('Good: "Patterns needed -> grep auth -> found 3"')
        parts.append('Bad: "For the patterns we need, let me search for auth..."')
        parts.append("</thinking_efficiency>")
    parts.append("")
    parts.append(render(
        W.el("current_action", *[TextNode(a) for a in guidance_dict["actions"]]).build(),
        XMLRenderer()
    ))
    if guidance_dict["next"]:
        parts.append("")
        parts.append(render(
            W.el("invoke_after", TextNode(guidance_dict["next"])).build(),
            XMLRenderer()
        ))
    print("\n".join(parts))
