"""Resource management for planner scripts.

Handles loading of resource files and path resolution.
"""

from pathlib import Path

from skills.lib.io import read_text_or_exit

__all__ = [
    "get_resource",
    "get_mode_script_path",
    "get_exhaustiveness_prompt",
    "PlannerResourceProvider",
]


# =============================================================================
# Resource Provider Implementation
# =============================================================================


class PlannerResourceProvider:
    """ResourceProvider implementation for planner workflows.

    Provides access to conventions and step guidance.
    """

    def get_resource(self, name: str) -> str:
        """Retrieve resource content from conventions directory.

        Implements ResourceProvider protocol for planner workflows.
        Maps resource name to file in CONVENTIONS_DIR.
        """
        resource_path = Path(__file__).resolve().parents[4] / "planner" / "resources" / name
        try:
            return read_text_or_exit(resource_path, "loading planner resource")
        except SystemExit:
            raise FileNotFoundError(f"Resource not found: {name}")

    def get_step_guidance(self, **kwargs) -> dict:
        """Get step-specific guidance (placeholder for forward compatibility).

        Returns empty dict until per-step guidance requirements emerge.
        Decision Log (get_step_guidance placeholder) explains deferral rationale.
        """
        return {}


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

    Exits:
        With contextual error message if resource doesn't exist
    """
    # shared -> planner -> skills -> scripts -> skills -> planner/resources
    resource_path = Path(__file__).resolve().parents[4] / "planner" / "resources" / name
    return read_text_or_exit(resource_path, "loading planner resource")


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


