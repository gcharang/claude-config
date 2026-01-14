"""Workflow orchestration framework for skills.

Public API for workflow types, formatters, registration, and testing.
"""

from .core import (
    Arg,
    Outcome,
    StepContext,
    StepDef,
    Workflow,
    get_workflow_registry,
    register_workflow,
)
from .types import (
    AgentRole,
    BranchRouting,
    Confidence,
    Dispatch,
    GateConfig,
    LinearRouting,
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
    "register_workflow",
    "get_workflow_registry",
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
]
