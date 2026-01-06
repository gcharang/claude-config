#!/usr/bin/env python3
"""
QR-Plan-Docs - Step-based workflow for quality-reviewer sub-agent.

Validates documentation quality in plan files after TW scrub:
- Temporal contamination detection
- Hidden baseline references
- WHY-not-WHAT comment validation

Usage:
    python3 qr/plan-docs.py --step 1 --total-steps 4 [--qr-iteration 1] [--qr-fail]

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared import (
    QRState,
    get_resource,
    format_step_output,
    format_qr_banner,
    format_resource,
    format_detection_questions,
    format_expected_output,
)


def get_step_guidance(
    step: int, total_steps: int, script_path: str, **kwargs
) -> dict:
    """Return guidance for the given step.

    Args:
        step: Current step number (1-indexed)
        total_steps: Total number of steps in this workflow
        script_path: Absolute path to this script (for sub-agent invocation)
        **kwargs: Additional context (qr_iteration, qr_fail, etc.)
    """
    qr_iteration = kwargs.get("qr_iteration", 1)
    qr_fail = kwargs.get("qr_fail", False)
    qr = QRState(iteration=qr_iteration, failed=qr_fail)

    # Step 1: Task description
    if step == 1:
        banner = format_qr_banner("QR-DOCS", qr)
        return {
            "title": "Documentation Quality Review",
            "actions": [banner, ""]
            + [
                "TASK: Validate documentation quality in plan file.",
                "",
                "You are reviewing the plan AFTER technical-writer scrub.",
                "TW has added comments and enriched prose.",
                "Your job: verify TW's work follows documentation standards.",
                "",
                "SCOPE:",
                "  - All comments in Code Changes sections (```diff blocks)",
                "  - All prose in milestone descriptions",
                "  - Decision Log entries",
                "",
                "Read the plan file now. Note all comments and prose sections.",
            ],
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Resource injection (temporal contamination reference)
    if step == 2:
        temporal_resource = get_resource("temporal-contamination.md")
        resource_block = format_resource(
            "temporal-contamination",
            "documentation-review",
            temporal_resource
        )
        return {
            "title": "Reference: Temporal Contamination Heuristics",
            "actions": [
                "AUTHORITATIVE REFERENCE FOR DOCUMENTATION REVIEW:",
                "",
                resource_block,
                "",
                "Use this reference when checking comments and prose.",
                "Apply the 5 detection questions to EVERY comment.",
            ],
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Verification checks (factored)
    if step == 3:
        detection_qs = format_detection_questions(
            "temporal-contamination",
            [
                {"id": "CHANGE_RELATIVE", "text": "Does it describe an action taken? Signal: 'Added', 'Replaced', 'Now uses'"},
                {"id": "BASELINE_REFERENCE", "text": "Does it compare to removed code? Signal: 'Instead of', 'Previously', 'Replaces'"},
                {"id": "LOCATION_DIRECTIVE", "text": "Does it describe WHERE to put code? Signal: 'After', 'Before', 'Insert'"},
                {"id": "PLANNING_ARTIFACT", "text": "Does it describe future intent? Signal: 'TODO', 'Will', 'Planned'"},
                {"id": "INTENT_LEAKAGE", "text": "Does it describe author's choice? Signal: 'intentionally', 'deliberately', 'chose'"},
            ]
        )
        return {
            "title": "Execute Verification Checks",
            "actions": [
                "CHECK EACH COMMENT against these detection questions:",
                "",
                detection_qs,
                "",
                "FAIL CRITERIA:",
                "  CHANGE_RELATIVE: FAIL if comment describes what was DONE rather than what IS",
                "  BASELINE_REFERENCE: FAIL if comment references something not in the code",
                "  LOCATION_DIRECTIVE: FAIL - location is encoded in diff structure, not comments",
                "  PLANNING_ARTIFACT: FAIL - implement now or delete; no future promises",
                "  INTENT_LEAKAGE: FAIL if it foregrounds decision; PASS if technical reason given",
                "",
                "ALSO CHECK PROSE:",
                "  - Does prose explain WHY decisions were made?",
                "  - Are Decision Log entries substantive (multi-step reasoning)?",
                "  - Is Invisible Knowledge documented where needed?",
                "",
                "Record each issue with: [CATEGORY] description (file:line if applicable)",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Output format (final step)
    if step >= total_steps:
        expected_output = format_expected_output(
            if_pass="PASS: Documentation follows timeless present convention.",
            if_issues="""\
ISSUES:
  1. [CATEGORY] description (file:line)
  2. [CATEGORY] description (file:line)
  ...""",
            categories=[
                "TEMPORAL: Change-relative language (most common)",
                "BASELINE: Hidden baseline reference",
                "LOCATION: Location directive in comment",
                "PLANNING: Future intent / TODO",
                "INTENT: Author decision without technical reason",
                "WHY-MISSING: Comment explains WHAT but not WHY",
            ]
        )
        return {
            "title": "Format Output",
            "actions": [
                expected_output,
                "",
                "Return PASS or ISSUES to the orchestrator.",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from shared import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Docs: Documentation quality validation workflow")
