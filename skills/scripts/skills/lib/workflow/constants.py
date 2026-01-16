"""Workflow constants shared across all skills.

QR-related constants are defined here in the lib layer so that
formatters can use them without creating a dependency on planner.
"""


# =============================================================================
# HITL Constants
# =============================================================================

HITL_BATCHING_GUIDANCE = """\
<hitl_efficiency>
BATCH RELATED QUESTIONS: When multiple clarifications are needed in the same
decision domain, combine into ONE AskUserQuestion call with multiple questions.

BATCH when:
  - Questions are about the same topic (testing, architecture, naming)
  - User can answer all without needing intermediate results
  - Questions don't depend on each other's answers

DO NOT BATCH when:
  - Answer to Q1 determines whether Q2 is needed
  - Questions span unrelated domains

EXAMPLE (batch these):
  - Unit test approach?
  - Integration test approach?
  - E2E test approach?
  -> ONE AskUserQuestion with questions array of 3 entries

EXAMPLE (don't batch):
  - Which database? -> User answers "PostgreSQL"
  - Which ORM? -> Depends on database choice
  -> TWO separate AskUserQuestion calls
</hitl_efficiency>
"""


# =============================================================================
# Subagent Return Constants
# =============================================================================

SUBAGENT_RETURN_BUDGET = """\
<return_budget>
TOKEN BUDGET (ENFORCED):
  - Total return: MAX 1500 tokens
  - Per section: MAX 500 tokens
  - Per finding/item: MAX 50 tokens

COMPRESSION STYLE:
  VERBOSE: 'The module implements a factory pattern that creates service
           instances, enabling dependency injection and testability...'
  DRAFT:   'Factory pattern -> DI + testability'

If findings exceed budget, OMIT low-relevance items.
Write detailed content to FILES, return only status + metadata.
</return_budget>
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
