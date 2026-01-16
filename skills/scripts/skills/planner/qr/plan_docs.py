#!/usr/bin/env python3
"""
QR-Plan-Docs - Step-based workflow for quality-reviewer sub-agent.

Validates documentation quality in plan files after TW scrub:
- Temporal contamination detection
- Hidden baseline references
- WHY-not-WHAT comment validation

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.types import QRState, LoopState, ResourceProvider
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.conventions import get_convention


STEPS = {
    1: {
        "title": "Documentation Quality Review",
    },
    2: {
        "title": "Reference: Temporal Contamination Heuristics",
    },
    3: {
        "title": "Execute Verification Checks",
    },
    4: {
        "title": "Exhaustiveness Verification",
    },
    5: {
        "title": "Self-Validate Suggested Fixes",
    },
    6: {
        "title": "Write Report and Return Result",
    },
}


def step_1_handler(step_info, total_steps, module_path, qr, **kwargs):
    banner = render(W.el("state_banner", checkpoint="QR-DOCS", iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
    return {
        "title": step_info["title"],
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
        "next": f"python3 -m {module_path} --step 2 --total-steps {total_steps}",
    }


def step_2_handler(step_info, total_steps, module_path, qr, **kwargs):
    temporal_resource = get_convention("temporal.md")
    resource_block = render(W.el("resource", TextNode(temporal_resource), name="temporal-contamination", purpose="documentation-review").build(), XMLRenderer())
    return {
        "title": step_info["title"],
        "actions": [
            "AUTHORITATIVE REFERENCE FOR DOCUMENTATION REVIEW:",
            "",
            resource_block,
            "",
            "Use this reference when checking comments and prose.",
            "Apply the 5 detection questions to EVERY comment.",
        ],
        "next": f"python3 -m {module_path} --step 3 --total-steps {total_steps}",
    }


def step_3_handler(step_info, total_steps, module_path, qr, **kwargs):
    detection_qs = """<detection_questions category="temporal-contamination">
  <question id="CHANGE_RELATIVE" text="Does it describe an action taken? Signal: 'Added', 'Replaced', 'Now uses'" />
  <question id="BASELINE_REFERENCE" text="Does it compare to removed code? Signal: 'Instead of', 'Previously', 'Replaces'" />
  <question id="LOCATION_DIRECTIVE" text="Does it describe WHERE to put code? Signal: 'After', 'Before', 'Insert'" />
  <question id="PLANNING_ARTIFACT" text="Does it describe future intent? Signal: 'TODO', 'Will', 'Planned'" />
  <question id="INTENT_LEAKAGE" text="Does it describe author's choice? Signal: 'intentionally', 'deliberately', 'chose'" />
</detection_questions>"""
    return {
        "title": step_info["title"],
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
        "next": f"python3 -m {module_path} --step 4 --total-steps {total_steps}",
    }


def step_4_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
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
        "next": f"python3 -m {module_path} --step 5 --total-steps {total_steps}",
    }


def step_5_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 5 - Self-validate suggested fixes."""
    return {
        "title": "Self-Validate Suggested Fixes",
        "actions": [
            "<self_validation>",
            "BEFORE finalizing your report, validate your OWN suggested fixes.",
            "",
            "This step prevents QR oscillation loops where fixes introduce new issues.",
            "",
            "For EACH suggested fix in your findings:",
            "  1. Read the suggested text VERBATIM",
            "  2. Apply the SAME temporal contamination checks to your suggestion:",
            "     - CHANGE_RELATIVE: 'Added', 'Replaced', 'Now uses'?",
            "     - BASELINE_REFERENCE: 'instead of', 'previously', 'replaces'?",
            "     - LOCATION_DIRECTIVE: 'After', 'Before', 'Insert'?",
            "     - PLANNING_ARTIFACT: 'TODO', 'Will', 'Planned'?",
            "     - INTENT_LEAKAGE: 'intentionally', 'deliberately', 'chose'?",
            "",
            "If your suggested fix VIOLATES a rule:",
            "  - REVISE the suggestion to comply, OR",
            "  - REMOVE the suggestion and report the issue only",
            "",
            "EXAMPLE OF SELF-VIOLATION:",
            "  Finding: 'Added mutex' is temporal contamination",
            "  BAD suggestion: 'Replaces scattered locks' -- 'Replaces' is also temporal!",
            "  GOOD suggestion: 'Mutex serializes cache access from concurrent requests'",
            "",
            "Record any self-violations found and corrected.",
            "</self_validation>",
        ],
        "next": f"python3 -m {module_path} --step 6 --total-steps {total_steps}",
    }


def step_6_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
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


STEP_HANDLERS = {
    1: step_1_handler,
    2: step_2_handler,
    3: step_3_handler,
    4: step_4_handler,
    5: step_5_handler,
    6: step_6_handler,
}


def get_step_guidance(
    step: int, total_steps: int, module_path: str, provider: ResourceProvider = None, **kwargs
) -> dict:
    """Return guidance for the given step.

    Args:
        step: Current step number (1-indexed)
        total_steps: Total number of steps in this workflow
        module_path: Module path for -m invocation
        **kwargs: Additional context (qr_iteration, qr_fail, etc.)
    """
    qr_iteration = kwargs.get("qr_iteration", 1)
    qr_fail = kwargs.get("qr_fail", False)
    state = LoopState.RETRY if qr_fail else LoopState.INITIAL
    qr = QRState(iteration=qr_iteration, state=state)

    step_info = STEPS.get(step, {})
    handler = STEP_HANDLERS.get(step)

    if step >= total_steps:
        handler = STEP_HANDLERS.get(5)
        step_info = STEPS.get(5, {})

    if handler:
        return handler(step_info, total_steps=total_steps, module_path=module_path, qr=qr, **kwargs)

    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Docs: Documentation quality validation workflow")
