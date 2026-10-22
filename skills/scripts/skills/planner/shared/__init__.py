"""Shared utilities for planner scripts.

Workflow types and formatters live in skills.lib.workflow.
This module contains planner-specific resource utilities.

QR Gate Pattern for Verification Loops:
  Every QR verify step is followed by a GATE step that routes from qr-{phase}.json
  and outputs the EXACT next command to invoke, leaving no room for interpretation.

  Work steps detect fix mode via qr-{phase}.json file state inspection.
"""

# Re-export from resources
# Re-export from domain (planner-specific guidance types)
from .domain import GuidanceResult
from .resources import (
    get_mode_script_path,
    get_resource,
)

# Re-export from routing
from .routing import (
    WORK_PHASES,
    detect_qr_state,
    route_work_phase,
)

__all__ = [
    # Routing
    "WORK_PHASES",
    # Domain types (planner-specific)
    "GuidanceResult",
    "detect_qr_state",
    "get_mode_script_path",
    # Resources
    "get_resource",
    "route_work_phase",
]
