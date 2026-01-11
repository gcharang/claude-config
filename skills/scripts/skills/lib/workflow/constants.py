"""Workflow constants shared across all skills.

QR-related constants are defined here in the lib layer so that
formatters can use them without creating a dependency on planner.
"""


# =============================================================================
# QR Constants
# =============================================================================

# Empirical observation: QR gains diminish after 4-5 retries.
# Beyond this limit, user confirmation is required to continue.
QR_ITERATION_LIMIT = 5


def get_blocking_severities(iteration: int) -> set[str]:
    """Return severities that block at given iteration.

    Progressive de-escalation: early iterations enforce all severities,
    later iterations only enforce critical issues.

    Args:
        iteration: QR loop iteration count (1-indexed)

    Returns:
        Set of severity strings that should block at this iteration
    """
    if iteration <= 3:
        return {"MUST", "SHOULD", "COULD"}
    elif iteration == 4:
        return {"MUST", "SHOULD"}
    else:  # iteration >= 5
        return {"MUST"}
