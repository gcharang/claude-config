#!/usr/bin/env python3
"""QR decomposition for plan-docs phase.

Scope: Documentation quality only.
  - COVERAGE: decisions/IK documented somewhere
  - QUALITY: temporal-free, WHY-not-WHAT
NOT code correctness (plan-code's job).

Severity categories (per conventions/severity.md):
  MUST: KNOWLEDGE categories only (TW can fix documentation issues)
    - DECISION_LOG_MISSING, IK_TRANSFER_FAILURE
    - TEMPORAL_CONTAMINATION, BASELINE_REFERENCE
  SHOULD: Documentation structure gaps
  COULD: Minor formatting inconsistencies

WHY KNOWLEDGE-only: TW agent cannot fix code correctness issues.
Applying STRUCTURE categories generates unfixable items, causing QR loops.
"""

from skills.planner.quality_reviewer.prompts.decompose import dispatch_step


PHASE = "plan-docs"


# =============================================================================
# PHASE-SPECIFIC PROMPTS (visible at module level for debugging)
# =============================================================================

STEP_1_ABSORB = """\
Read plan.json from STATE_DIR:
  cat $STATE_DIR/plan.json | jq '.'

SCOPE: Documentation quality only. You are verifying that planning knowledge
is captured in documentation fields -- NOT verifying code correctness.

SOURCES (planning knowledge that must be documented):
  - planning_context.decisions[] -- architectural choices with reasoning
  - planning_context.rejected_alternatives[] -- what was considered and why not
  - invisible_knowledge{} -- system context, invariants, tradeoffs

DESTINATIONS (where knowledge appears in the plan):
  - milestones[].documentation.module_comment -- Tier 4: why module exists
  - milestones[].documentation.docstrings[] -- Tier 3: function summaries
  - milestones[].documentation.function_blocks[] -- Tier 2: algorithm explanation
  - milestones[].documentation.inline_comments[] -- Tier 1: WHY for specific lines
  - readme_entries[] -- Tier 5: cross-cutting invisible knowledge

OUT OF SCOPE (already verified in plan-code phase):
  - Code correctness in diffs (compilation, exports, types, logic)
  - Diff format validity (context lines, unified diff syntax)
  - Intent-to-change linkage
  - Whether planned files exist on disk (this is a PLAN, not implementation)"""


STEP_2_CONCERNS = """\
Brainstorm concerns specific to DOCUMENTATION QUALITY:
  - Temporal contamination (change-relative language in comments)
  - Missing WHY-not-WHAT (comments describe code, not explain reasoning)
  - Incomplete coverage (decisions not documented anywhere)
  - Invalid decision_refs (refs point to nonexistent decisions)
  - Structural gaps (empty documentation{} fields)

DO NOT brainstorm code correctness concerns (out of scope for this phase)."""


STEP_3_ENUMERATION = """\
For plan-docs, enumerate DOCUMENTATION ARTIFACTS only:

SOURCES (planning knowledge to verify coverage):
  - Each planning_context.decisions[] entry (ID, has reasoning?)
  - Each planning_context.rejected_alternatives[] entry
  - invisible_knowledge content (system, invariants[], tradeoffs[])

DESTINATIONS (documentation fields to verify population):
  - Each milestone's documentation{} section:
    * module_comment present?
    * docstrings[] count
    * function_blocks[] count
    * inline_comments[] count
  - readme_entries[] (path, has content?)

QUALITY DIMENSIONS:
  - Temporal contamination in documentation strings
  - WHY-not-WHAT in inline_comments and function_blocks
  - decision_ref validity (refs point to existing decisions)

DO NOT enumerate:
  - code_changes for code correctness (plan-code's job)
  - diff syntax or context lines (plan-code's job)
  - whether files exist on disk (this is a plan, not implementation)"""


STEP_5_GENERATE = """\
SEVERITY ASSIGNMENT (per conventions/severity.md, plan-docs scope):

  MUST (blocks all iterations) - KNOWLEDGE categories only:
    - DECISION_LOG_MISSING: decision without documentation anywhere
    - IK_TRANSFER_FAILURE: invisible knowledge not at best location
    - TEMPORAL_CONTAMINATION: change-relative language in comments
    - BASELINE_REFERENCE: comment references removed code

  SHOULD (iterations 1-4):
    - Structural completeness gaps in documentation{}
    - WHY-not-WHAT violations in function_blocks

  COULD (iterations 1-3):
    - Minor formatting inconsistencies

DO NOT use STRUCTURE categories (god objects, convention violations) --
those are plan-code's responsibility. TW cannot fix code issues."""


COMPONENT_EXAMPLES = """\
  - A milestone's documentation{} block
  - A readme_entry
  - A decision log entry"""


CONCERN_EXAMPLES = """\
  - Temporal contamination
  - WHY-not-WHAT clarity
  - Coverage completeness"""


# =============================================================================
# CONFIGURATION FOR DISPATCH
# =============================================================================

PHASE_PROMPTS = {
    1: STEP_1_ABSORB,
    2: STEP_2_CONCERNS,
    3: STEP_3_ENUMERATION,
    5: STEP_5_GENERATE,
}

GROUPING_CONFIG = {
    "component_examples": COMPONENT_EXAMPLES,
    "concern_examples": CONCERN_EXAMPLES,
}


# =============================================================================
# ENTRY POINT
# =============================================================================

def get_step_guidance(step: int, module_path: str = None, **kwargs) -> dict:
    """Entry point for workflow execution.

    Called by mode_main() in cli.py. Delegates to shared dispatch_step()
    with phase-specific prompts and grouping config.
    """
    module_path = module_path or "skills.planner.quality_reviewer.plan_docs_qr_decompose"
    state_dir = kwargs.get("state_dir", "")
    return dispatch_step(step, PHASE, module_path, PHASE_PROMPTS, GROUPING_CONFIG, state_dir)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main

    mode_main(
        __file__,
        get_step_guidance,
        "QR-Plan-Docs-Decompose: Generate verification items for documentation completeness",
        extra_args=[
            (["--state-dir"], {"type": str, "required": True, "help": "State directory path"}),
        ],
    )
