#!/usr/bin/env python3
"""
QR-Plan-Docs - Step-based workflow for quality-reviewer sub-agent.

Validates documentation quality in plan files after TW scrub:
- Temporal contamination detection
- Hidden baseline references
- WHY-not-WHAT comment validation

Usage:
    python3 qr/plan-docs.py --step 1 --total-steps 5 [--qr-iteration 1] [--qr-fail]

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path

# Add .claude/ to path for skills.* imports
_claude_dir = Path(__file__).resolve().parents[4]
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

# Add planner/scripts to path for shared.resources access
planner_scripts_dir = Path(__file__).resolve().parent.parent
if str(planner_scripts_dir) not in sys.path:
    sys.path.insert(0, str(planner_scripts_dir))

from skills.lib.workflow.types import QRState
from skills.lib.workflow.formatters import (
    format_step_output,
    format_qr_banner,
    format_resource,
    format_detection_questions,
    format_expected_output,
)

from shared.resources import get_resource


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
                "  CHANGE_RELATIVE: Report as TEMPORAL_CONTAMINATION (MUST)",
                "  BASELINE_REFERENCE: Report as BASELINE_REFERENCE (MUST)",
                "  LOCATION_DIRECTIVE: Report as TEMPORAL_CONTAMINATION (MUST)",
                "  PLANNING_ARTIFACT: Report as TEMPORAL_CONTAMINATION (MUST)",
                "  INTENT_LEAKAGE: Report as LLM_COMPREHENSION_RISK (MUST)",
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

    # Step 4: Exhaustiveness verification (fresh second-pass)
    if step == 4:
        return {
            "title": "Exhaustiveness Verification",
            "actions": [
                "<exhaustiveness_check>",
                "STOP. Before finalizing findings, perform fresh examination.",
                "",
                "This is a SEPARATE verification pass. Do NOT simply review your prior",
                "findings -- re-examine the documentation with fresh eyes.",
                "",
                "ADVERSARIAL QUESTIONS (answer each with specific findings or 'none'):",
                "",
                "1. What CATEGORIES of temporal contamination have you not yet checked?",
                "   (e.g., implicit comparisons, verb tense shifts, meta-commentary)",
                "",
                "2. For each comment, does it make sense to a reader who ONLY sees",
                "   the final code? Would they understand it without diff context?",
                "",
                "3. What ASSUMPTIONS about the reader's context does the documentation make?",
                "   (e.g., knowing what was removed, knowing the author's intent)",
                "",
                "4. What would a HOSTILE reviewer find that you missed?",
                "   Imagine someone whose job is to find documentation issues you overlooked.",
                "",
                "5. Are there any comments that explain WHAT but not WHY?",
                "   Re-read each comment asking 'does this explain the reasoning?'",
                "",
                "Record any NEW issues discovered. These are ADDITIONAL findings,",
                "not duplicates of prior checks.",
                "</exhaustiveness_check>",
            ],
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Output format (final step)
    # WHY file-based: Token optimization. Main agent only needs PASS/FAIL to route.
    # Full report goes to file. Executor reads file directly.
    # Reduces main agent context by ~95% for QR results.
    if step >= total_steps:
        return {
            "title": "Write Report and Return Result",
            "actions": [
                "TOKEN OPTIMIZATION: Write full report to file, return minimal output.",
                "",
                "WHY: Main agent only needs PASS/FAIL to route. Full report goes to",
                "file. Executor reads file directly. Saves ~95% tokens in main agent.",
                "",
                "STEPS:",
                "1. Create temp dir: Use Python's tempfile.mkdtemp(prefix='qr-report-')",
                "2. Write full findings (format below) to: {tmpdir}/qr.md",
                "3. Return to orchestrator:",
                "   - If PASS: Return exactly 'RESULT: PASS'",
                "   - If ISSUES: Return exactly:",
                "       RESULT: FAIL",
                "       PATH: {tmpdir}/qr.md",
                "",
                "FULL REPORT FORMAT (write to file, NOT to output):",
                "",
                "If NO issues found:",
                "  PASS: Documentation follows timeless present convention.",
                "",
                "If issues found:",
                "  ISSUES:",
                "    1. [CATEGORY] description (file:line)",
                "    2. [CATEGORY] description (file:line)",
                "    ...",
                "",
                "CATEGORIES (use exact category names):",
                "  - TEMPORAL_CONTAMINATION: Change-relative language (MUST)",
                "  - BASELINE_REFERENCE: Hidden baseline reference (MUST)",
                "  - LLM_COMPREHENSION_RISK: Confusing to future LLM (MUST)",
                "  - MINOR_INCONSISTENCY: Comment explains WHAT but not WHY (COULD)",
                "",
                "Intent markers: Check for :PERF: and :UNSAFE: markers.",
                "  Valid format: ':MARKER: [what]; [why]' (semicolon + non-empty why)",
                "  Invalid format: Report as MARKER_INVALID (MUST)",
            ],
            "next": "Return minimal result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Docs: Documentation quality validation workflow")
