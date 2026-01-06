"""Shared utilities for planner scripts.

This module re-exports all utilities from submodules for backwards compatibility.
New code should import from submodules directly when possible.

QR Gate Pattern for Verification Loops:
  Every QR step is followed by a GATE step that:
  1. Takes --qr-status=pass|fail as input
  2. Outputs the EXACT next command to invoke
  3. Leaves no room for interpretation

  Work steps that follow a FAIL gate take --qr-fail flag to focus on fixing.

This pattern is applied consistently across:
  - planner.py (steps 5-12: sequential QR with gates)
  - executor.py (step 4-5: holistic QR with gate)
  - wave-executor.py (steps 2-3: batch QR with gate)
"""

# Re-export from domain
from .domain import (
    QRState,
    FlatCommand,
    BranchCommand,
    NextCommand,
    GuidanceResult,
    GateConfig,
)

# Re-export from resources
from .resources import (
    QR_ITERATION_LIMIT,
    get_resource,
    get_mode_script_path,
    get_reverification_context,
)

# Re-export from formatting
from .formatting import (
    format_step_header,
    format_current_action,
    format_invoke_after,
    format_next_block,
    format_gate_result,
    format_xml_mandate,
    format_step_output,
    format_subagent_dispatch,
    format_state_banner,
    format_qr_banner,
    format_expected_output,
    format_forbidden,
    format_routing,
    format_post_qr_routing,
    format_resource,
    format_detection_questions,
    format_verification_checklist,
    format_incorrect_behavior,
    format_orchestrator_constraint,
    format_factored_verification_rationale,
    format_open_question_guidance,
    format_gate_actions,
    format_gate_step,
)

# Re-export from cli
from .cli import (
    add_qr_args,
    mode_main,
)

__all__ = [
    # Domain types
    "QRState",
    "FlatCommand",
    "BranchCommand",
    "NextCommand",
    "GuidanceResult",
    "GateConfig",
    # Constants
    "QR_ITERATION_LIMIT",
    # Resources
    "get_resource",
    "get_mode_script_path",
    "get_reverification_context",
    # Core formatters
    "format_step_header",
    "format_current_action",
    "format_invoke_after",
    "format_next_block",
    "format_gate_result",
    "format_xml_mandate",
    "format_step_output",
    # Extended formatters
    "format_subagent_dispatch",
    "format_state_banner",
    "format_qr_banner",
    "format_expected_output",
    "format_forbidden",
    "format_routing",
    "format_post_qr_routing",
    "format_resource",
    "format_detection_questions",
    "format_verification_checklist",
    "format_incorrect_behavior",
    "format_orchestrator_constraint",
    "format_factored_verification_rationale",
    "format_open_question_guidance",
    "format_gate_actions",
    "format_gate_step",
    # CLI
    "add_qr_args",
    "mode_main",
]
