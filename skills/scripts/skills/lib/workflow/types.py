"""Domain types for workflow orchestration.

Explicit, composable abstractions over stringly-typed dicts and parameter groups.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ResourceProvider(Protocol):
    """Protocol for accessing workflow resources without circular imports.

    QR/TW/Dev modules receive ResourceProvider instead of importing
    skills.planner.shared.resources directly. This breaks 3-layer coupling
    (modules import from both lib/workflow and planner/shared).

    Protocol in types.py enables mock implementations for isolated unit testing
    without circular dependency chains.
    """

    def get_resource(self, name: str) -> str:
        """Retrieve resource content by name.

        Args:
            name: Resource filename (e.g., "plan-format.md")

        Returns:
            Resource file content as string

        Raises:
            FileNotFoundError: Resource not found in conventions directory
        """
        ...

    def get_step_guidance(self, **kwargs) -> dict:
        """Get step-specific guidance for workflow execution.

        Placeholder for future per-step metadata (guidance varies by step).
        Current QR/TW modules read full conventions files, not step-specific
        guidance. Returns empty dict until use case emerges.

        Avoids speculative design while maintaining protocol compatibility.
        """
        ...


class AgentRole(Enum):
    """Agent types for sub-agent dispatch."""

    QUALITY_REVIEWER = "quality-reviewer"
    DEVELOPER = "developer"
    TECHNICAL_WRITER = "technical-writer"
    EXPLORE = "explore"
    GENERAL_PURPOSE = "general-purpose"
    ARCHITECT = "architect"


class Confidence(Enum):
    """Confidence levels for iterative workflows."""

    EXPLORING = "exploring"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


@dataclass
class Dispatch:
    """Sub-agent dispatch configuration."""

    agent: AgentRole
    script: str
    context_vars: dict[str, str] = field(default_factory=dict)
    free_form: bool = False


# =============================================================================
# Domain Types for Test Generation
# =============================================================================


# Domain types implement __iter__ for use with itertools.product to generate
# Cartesian products. frozen=True enables hashability for pytest param caching.
@dataclass(frozen=True)
class BoundedInt:
    """Integer domain with inclusive bounds [lo, hi]."""

    lo: int
    hi: int

    def __post_init__(self):
        # Enforce lo <= hi: prevents empty ranges that would silently skip test cases
        if self.lo > self.hi:
            raise ValueError(f"BoundedInt: lo ({self.lo}) must be <= hi ({self.hi})")

    def __iter__(self):
        """Yield all integers in [lo, hi] inclusive."""
        return iter(range(self.lo, self.hi + 1))


@dataclass(frozen=True)
class ChoiceSet:
    """Finite choice domain stored as a tuple (hashable for test caching)."""

    choices: tuple

    def __iter__(self):
        return iter(self.choices)


@dataclass(frozen=True)
class Constant:
    """Single-value domain; yields exactly one element."""

    value: object

    def __iter__(self):
        return iter((self.value,))


# =============================================================================
# Question Relay Types
# =============================================================================


@dataclass(frozen=True)
class QuestionOption:
    """Single option for a user input question."""

    label: str
    description: str
