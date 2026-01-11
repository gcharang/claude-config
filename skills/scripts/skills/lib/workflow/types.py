"""Domain types for workflow orchestration.

Explicit, composable abstractions over stringly-typed dicts and parameter groups.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class AgentRole(Enum):
    """Agent types for sub-agent dispatch."""

    QUALITY_REVIEWER = "quality-reviewer"
    DEVELOPER = "developer"
    TECHNICAL_WRITER = "technical-writer"
    EXPLORE = "explore"
    GENERAL_PURPOSE = "general-purpose"


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
    status: QR result from previous step ("pass"/"fail")
    """

    iteration: int = 1
    failed: bool = False
    status: Literal["pass", "fail"] | None = None


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


@dataclass
class Step:
    """Step configuration for workflow."""

    title: str
    actions: list[str]
    routing: Routing = field(default_factory=LinearRouting)
    dispatch: Dispatch | None = None
    gate: GateConfig | None = None
    phase: str | None = None


@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""

    name: str
    script: str
    steps: dict[int, Step]
    description: str = ""
