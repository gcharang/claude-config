"""Domain types for the planner skill.

These types replace stringly-typed dicts and primitive parameter groups
with explicit, composable abstractions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


# =============================================================================
# QR Loop State
# =============================================================================


@dataclass
class QRState:
    """Quality Review loop state.

    Encapsulates the three primitives that were previously passed separately:
    qr_iteration, qr_fail, qr_status.

    Attributes:
        iteration: Loop count (1 = initial review, 2+ = re-verification)
        failed: Whether this invocation is fixing issues from prior QR
        status: Gate input - "pass" or "fail" from previous QR step
    """

    iteration: int = 1
    failed: bool = False
    status: Literal["pass", "fail"] | None = None


# =============================================================================
# Command Routing
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
    next_command: NextCommand = None


# =============================================================================
# Gate Configuration
# =============================================================================


@dataclass
class GateConfig:
    """Configuration for a QR gate step.

    Encapsulates the gate configuration that was previously stored
    as tuples in gate_config dicts.

    Attributes:
        qr_name: QR checkpoint name (e.g., "QR-COMPLETENESS")
        work_step: Step to return to for fixes
        pass_step: Step to proceed to on pass (None for final gate)
        pass_message: Message shown when gate passes
        self_fix: If True, orchestrator fixes issues directly
        fix_target: Agent to delegate to if self_fix is False
    """

    qr_name: str
    work_step: int
    pass_step: int | None
    pass_message: str
    self_fix: bool
    fix_target: str | None = None


# =============================================================================
# QR Severity and Categories
# =============================================================================


class Severity(Enum):
    MUST = "MUST"       # Unrecoverable if missed
    SHOULD = "SHOULD"   # Maintainability debt
    COULD = "COULD"     # Auto-fixable


class IssueCategory(Enum):
    # KNOWLEDGE (MUST)
    DECISION_LOG_MISSING = "DECISION_LOG_MISSING"
    POLICY_UNJUSTIFIED = "POLICY_UNJUSTIFIED"
    IK_TRANSFER_FAILURE = "IK_TRANSFER_FAILURE"
    TEMPORAL_CONTAMINATION = "TEMPORAL_CONTAMINATION"
    BASELINE_REFERENCE = "BASELINE_REFERENCE"
    ASSUMPTION_UNVALIDATED = "ASSUMPTION_UNVALIDATED"
    LLM_COMPREHENSION_RISK = "LLM_COMPREHENSION_RISK"
    MARKER_INVALID = "MARKER_INVALID"

    # STRUCTURE (SHOULD)
    GOD_OBJECT = "GOD_OBJECT"
    GOD_FUNCTION = "GOD_FUNCTION"
    DUPLICATE_LOGIC = "DUPLICATE_LOGIC"
    INCONSISTENT_ERROR_HANDLING = "INCONSISTENT_ERROR_HANDLING"
    CONVENTION_VIOLATION = "CONVENTION_VIOLATION"
    TESTING_STRATEGY_VIOLATION = "TESTING_STRATEGY_VIOLATION"

    # COSMETIC (COULD)
    DEAD_CODE = "DEAD_CODE"
    FORMATTER_FIXABLE = "FORMATTER_FIXABLE"
    MINOR_INCONSISTENCY = "MINOR_INCONSISTENCY"


CATEGORY_SEVERITY: dict[IssueCategory, Severity] = {
    # KNOWLEDGE -> MUST
    IssueCategory.DECISION_LOG_MISSING: Severity.MUST,
    IssueCategory.POLICY_UNJUSTIFIED: Severity.MUST,
    IssueCategory.IK_TRANSFER_FAILURE: Severity.MUST,
    IssueCategory.TEMPORAL_CONTAMINATION: Severity.MUST,
    IssueCategory.BASELINE_REFERENCE: Severity.MUST,
    IssueCategory.ASSUMPTION_UNVALIDATED: Severity.MUST,
    IssueCategory.LLM_COMPREHENSION_RISK: Severity.MUST,
    IssueCategory.MARKER_INVALID: Severity.MUST,
    # STRUCTURE -> SHOULD
    IssueCategory.GOD_OBJECT: Severity.SHOULD,
    IssueCategory.GOD_FUNCTION: Severity.SHOULD,
    IssueCategory.DUPLICATE_LOGIC: Severity.SHOULD,
    IssueCategory.INCONSISTENT_ERROR_HANDLING: Severity.SHOULD,
    IssueCategory.CONVENTION_VIOLATION: Severity.SHOULD,
    IssueCategory.TESTING_STRATEGY_VIOLATION: Severity.SHOULD,
    # COSMETIC -> COULD
    IssueCategory.DEAD_CODE: Severity.COULD,
    IssueCategory.FORMATTER_FIXABLE: Severity.COULD,
    IssueCategory.MINOR_INCONSISTENCY: Severity.COULD,
}
