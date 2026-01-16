"""Workflow orchestration framework for skills.

Public API for workflow types, formatters, registration, and testing.
"""

from .core import (
    Arg,
    Outcome,
    StepContext,
    StepDef,
    Workflow,
)
from .discovery import discover_workflows
from .types import (
    AgentRole,
    BranchRouting,
    Confidence,
    Dispatch,
    GateConfig,
    LinearRouting,
    Mode,
    Phase,
    PHASE_TO_MODE,
    QRState,
    Routing,
    Step,
    TerminalRouting,
    WorkflowDefinition,
)

__all__ = [
    # Core types
    "Workflow",
    "StepDef",
    "StepContext",
    "Outcome",
    "Arg",
    "discover_workflows",
    # Types for backward compatibility
    "AgentRole",
    "Confidence",
    "LinearRouting",
    "BranchRouting",
    "TerminalRouting",
    "Routing",
    "Dispatch",
    "GateConfig",
    "QRState",
    "Step",
    "WorkflowDefinition",
    # Code quality document types
    "Phase",
    "Mode",
    "PHASE_TO_MODE",
]
