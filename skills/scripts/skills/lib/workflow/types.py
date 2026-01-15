"""Domain types for workflow orchestration.

Explicit, composable abstractions over stringly-typed dicts and parameter groups.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal, Protocol, TypeAlias


class AgentRole(Enum):
    """Agent types for sub-agent dispatch."""

    QUALITY_REVIEWER = "quality-reviewer"
    DEVELOPER = "developer"
    TECHNICAL_WRITER = "technical-writer"
    EXPLORE = "explore"
    GENERAL_PURPOSE = "general-purpose"


class Confidence(Enum):
    """Confidence levels for iterative workflows."""

    EXPLORING = "exploring"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


class QRStatus(Enum):
    """Quality Review result status."""

    PASS = "pass"
    FAIL = "fail"

    def __bool__(self) -> bool:
        """Allow if qr_status: checks (PASS is truthy, FAIL is falsy for gating)."""
        return self == QRStatus.PASS


@dataclass
class LinearRouting:
    """Linear routing - proceed to step+1."""
    pass


@dataclass
class BranchRouting:
    """Conditional routing based on QR result."""

    if_pass: int
    if_fail: int


@dataclass
class TerminalRouting:
    """Terminal routing - no continuation."""
    pass


Routing = LinearRouting | BranchRouting | TerminalRouting


# =============================================================================
# Command Routing (for invoke_after)
# =============================================================================


@dataclass
class FlatCommand:
    """Single command routing (non-branching steps)."""

    command: str


@dataclass
class BranchCommand:
    """Conditional routing based on QR result (branching steps)."""

    if_pass: str
    if_fail: str


NextCommand = FlatCommand | BranchCommand | None
"""Union type for step routing.

- FlatCommand: Non-branching step, single next command
- BranchCommand: QR step, branches on pass/fail
- None: Terminal step, no invoke_after
"""


@dataclass
class Dispatch:
    """Sub-agent dispatch configuration."""

    agent: AgentRole
    script: str
    total_steps: int
    context_vars: dict[str, str] = field(default_factory=dict)
    free_form: bool = False


@dataclass
class QRState:
    """Quality Review loop state.

    iteration: Loop count (1=initial review, 2+=re-verification)
    failed: True when entering step to fix prior QR issues
    status: QR result from previous step
    """

    iteration: int = 1
    failed: bool = False
    status: QRStatus | None = None

    @property
    def passed(self) -> bool:
        """Check if QR passed."""
        return self.status == QRStatus.PASS


@dataclass
class GateConfig:
    """Configuration for a QR gate step.

    self_fix controls routing: True -> agent fixes issues automatically,
    False -> manual intervention required.
    """

    qr_name: str
    work_step: int
    pass_step: int | None
    pass_message: str
    self_fix: bool
    fix_target: AgentRole | None = None


# DEPRECATED: Use StepDef from core.py for new skills
@dataclass
class Step:
    """Step configuration for workflow."""

    title: str
    actions: list[str]
    routing: Routing = field(default_factory=LinearRouting)
    dispatch: Dispatch | None = None
    gate: GateConfig | None = None
    phase: str | None = None


# DEPRECATED: Use Workflow from core.py for new skills
@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""

    name: str
    script: str
    steps: dict[int, Step]
    description: str = ""


# =============================================================================
# Step Handler Pattern
# =============================================================================


@dataclass
class StepGuidance:
    """Return type for step handlers.

    Replaces dict returns with explicit structure.
    """

    title: str
    actions: list[str]
    next_hint: str = ""
    phase: str = ""
    # Additional fields can be added without breaking existing handlers


# Type alias for step handler functions
# Handlers receive step context and return guidance
StepHandler: TypeAlias = Callable[..., dict | StepGuidance]
"""Step handler function signature.

Args:
    step: Current step number
    total_steps: Total steps in workflow
    **kwargs: Additional context (qr_iteration, qr_fail, etc.)

Returns:
    Dict or StepGuidance with title, actions, next hint
"""


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
    """Discrete choice domain."""

    choices: tuple

    def __iter__(self):
        """Yield all choices in order."""
        return iter(self.choices)


@dataclass(frozen=True)
class Constant:
    """Single-value domain."""

    value: Any

    def __iter__(self):
        """Yield single value for uniform Cartesian product interface."""
        return iter([self.value])
