"""Resource management for planner scripts.

Handles loading of resource files and path resolution.
"""

from pathlib import Path

# Re-export QR constants from lib layer for backwards compatibility
from skills.lib.workflow.constants import QR_ITERATION_LIMIT, get_blocking_severities

__all__ = [
    "QR_ITERATION_LIMIT",
    "get_blocking_severities",
    "create_qr_report_dir",
    "get_resource",
    "get_mode_script_path",
    "get_exhaustiveness_prompt",
]


# =============================================================================
# QR Report Token Optimization
# =============================================================================


def create_qr_report_dir() -> Path:
    """Create temp directory for QR report.

    WHY: Token optimization. QR reports can be 1000+ tokens. Main agent only
    needs PASS/FAIL to route. Full report goes to file, executor reads directly.
    This reduces main agent context by ~95% for QR results.
    """
    import tempfile
    return Path(tempfile.mkdtemp(prefix="qr-report-"))


# =============================================================================
# Resource Loading
# =============================================================================


def get_resource(name: str) -> str:
    """Read resource file from planner resources directory.

    Resources are authoritative sources for specifications that agents need.
    Scripts inject these at runtime so agents don't need embedded copies.

    Args:
        name: Resource filename (e.g., "plan-format.md")

    Returns:
        Full content of the resource file

    Raises:
        FileNotFoundError: If resource doesn't exist
    """
    # shared -> planner -> skills -> scripts -> skills -> planner/resources
    resource_path = Path(__file__).resolve().parents[4] / "planner" / "resources" / name
    return resource_path.read_text()


def get_mode_script_path(script_name: str) -> str:
    """Get module path for -m invocation.

    Mode scripts provide step-based workflows for sub-agents.
    Scripts are organized by agent: qr/, dev/, tw/

    Args:
        script_name: Script path relative to planner/ (e.g., "qr/plan-docs.py")

    Returns:
        Module path for python3 -m (e.g., "skills.planner.qr.plan_docs")
    """
    # Convert path to module: "qr/plan-docs.py" -> "qr.plan_docs"
    module = script_name.replace("/", ".").replace("-", "_").removesuffix(".py")
    return f"skills.planner.{module}"


def get_exhaustiveness_prompt() -> list[str]:
    """Return exhaustiveness verification prompt for QR steps.

    Research shows models satisfice (stop after finding "enough" issues)
    unless explicitly prompted to find more. This prompt counters that
    tendency by forcing adversarial self-examination.

    Returns:
        List of prompt lines for exhaustiveness verification
    """
    return [
        "<exhaustiveness_check>",
        "STOP. Before reporting your findings, perform adversarial self-examination:",
        "",
        "1. What categories of issues have you NOT yet checked?",
        "2. What assumptions are you making that could hide problems?",
        "3. Re-read each milestone -- what could go wrong that you missed?",
        "4. What would a hostile reviewer find that you overlooked?",
        "",
        "List any additional issues discovered. Only report PASS if this",
        "second examination finds nothing new.",
        "</exhaustiveness_check>",
    ]


