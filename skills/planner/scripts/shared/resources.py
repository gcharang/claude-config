"""Resource management for planner scripts.

Handles loading of resource files and path resolution.
"""

from pathlib import Path


# =============================================================================
# Constants
# =============================================================================

# Empirical observation: QR gains diminish after 2-3 retries.
# Beyond this limit, user confirmation is required to continue.
QR_ITERATION_LIMIT = 3


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


def get_reverification_context() -> list[str]:
    """Return standard context for QR re-verification iterations.

    Used by all mode scripts when qr_iteration > 1 to explain
    the re-verification state to the sub-agent.

    Returns:
        List of context lines explaining re-verification state
    """
    return [
        "You previously fixed issues identified by QR.",
        "This invocation verifies those fixes were applied correctly.",
        "",
        "CRITICAL: QR MUST return PASS before you can proceed.",
    ]
