"""Domain types for the planner skill.

Planner-specific value types.
"""

from dataclasses import dataclass

__all__ = [
    "GuidanceResult",
]

# =============================================================================
# Step Guidance
# =============================================================================


@dataclass
class GuidanceResult:
    """Step guidance returned by get_*_guidance functions.

    Replaces stringly-typed dicts with explicit structure.

    Attributes:
        title: Step title for display
        actions: List of action strings (may include XML blocks)
        next_command: Routing command for invoke_after
    """

    title: str
    actions: list[str]
    next_command: str | None = None
