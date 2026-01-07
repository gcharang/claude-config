"""Resource management for planner scripts.

Handles loading of resource files and path resolution.
"""

from pathlib import Path


# =============================================================================
# Constants
# =============================================================================

# Empirical observation: QR gains diminish after 4-5 retries.
# Beyond this limit, user confirmation is required to continue.
QR_ITERATION_LIMIT = 5


# =============================================================================
# Resource Loading
# =============================================================================


def get_resource(name: str) -> str:
    """Read resource file from planner resources directory.

    Resources are authoritative sources for specifications that agents need.
    Scripts inject these at runtime so agents don't need embedded copies.

    Args:
        name: Resource filename (e.g., "temporal-contamination.md")

    Returns:
        Full content of the resource file

    Raises:
        FileNotFoundError: If resource doesn't exist
    """
    resource_path = Path(__file__).parent.parent.parent / "resources" / name
    return resource_path.read_text()


def get_mode_script_path(script_name: str) -> str:
    """Get absolute path to a mode script.

    Mode scripts provide step-based workflows for sub-agents.
    Scripts are organized by agent: qr/, dev/, tw/

    Args:
        script_name: Script path relative to scripts/ (e.g., "qr/plan-docs.py")

    Returns:
        Absolute path to the mode script
    """
    scripts_dir = Path(__file__).parent.parent
    return str(scripts_dir / script_name)


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
