"""Dispatch node type for parallel sub-agent orchestration.

TemplateDispatchNode: Parallel dispatch with parameterized template
    Same prompt structure applied to N targets (SIMD pattern).
    Template and command use $var syntax via string.Template.
    Example: refactor (N categories)

    Example:
        node = TemplateDispatchNode(
            agent_type="general-purpose",
            template="Explore $category_name in $mode mode...",
            targets=(
                {"category_name": "Naming", "mode": "design"},
                {"category_name": "Structure", "mode": "code"},
            ),
            command='uv run python -m skills.explore --category $category_name --mode $mode',
            model="haiku",
        )
        # Renderer expands to 2 agents with $var substituted per-target
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateDispatchNode:
    """Parallel dispatch: parameterized template applied to targets.

    Use when all agents run the same prompt structure with different parameters.
    Analogous to SIMD: Single Instruction (template), Multiple Data (targets).

    Template and command use $var syntax, substituted per-target
    using string.Template.substitute(). The renderer expands N prompts,
    so the LLM sees final prompts rather than substitution instructions.
    """

    agent_type: str
    template: str  # prompt with $var placeholders
    targets: tuple[dict[str, str], ...]  # variable bindings per target (tuple for frozen)
    command: str  # command with $var placeholders
    model: str | None = None
    instruction: str | None = None  # optional instruction text


__all__ = [
    "TemplateDispatchNode",
]
