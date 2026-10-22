"""QR domain types.

Moved from lib/workflow/types.py to planner/shared/qr/types.py.
"""

from dataclasses import dataclass, field
from enum import Enum

from skills.lib.workflow.types import AgentRole


class QAItemStatus(Enum):
    """QA checklist item status."""

    TODO = "TODO"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class QAItem:
    """Single QA checklist item.

    Tracks verification tasks across decomposition iterations with scope
    (macro vs micro), check description, status, and findings.
    """

    id: str
    scope: str
    check: str
    status: QAItemStatus
    version: int = 1
    finding: str | None = None
    parent_id: str | None = None
    group_id: str | None = None


class LoopState(Enum):
    """Whether a QR step runs first-time (INITIAL) or in fix mode (RETRY).

    resolve_qr_for_step (shared/qr/utils.py) derives it from qr-{phase}.json.
    """

    INITIAL = "initial"
    RETRY = "retry"


@dataclass
class QRState:
    """QR context for one orchestrator step (built by resolve_qr_for_step).

    Attributes:
        iteration: Current loop count (increments on each retry)
        state: First-time or fix-mode run
    """

    iteration: int = 1
    state: LoopState = LoopState.INITIAL

    @property
    def failed(self) -> bool:
        """Check if state indicates retry.

        Backward compatibility property for call sites checking retry state.
        Provides compatibility bridge during migration.
        """
        return self.state == LoopState.RETRY


@dataclass
class GateConfig:
    """Configuration for a QR gate step."""

    qr_name: str
    work_step: int
    pass_step: int | None
    pass_message: str
    fix_target: AgentRole | None = None


@dataclass
class Step:
    """Step configuration for workflow.

    DEPRECATED: Use StepDef from lib.workflow.core for new skills.
    """

    title: str
    actions: list[str]
    routing: object = field(default_factory=lambda: None)
    dispatch: object | None = None
    gate: GateConfig | None = None
    phase: str | None = None
