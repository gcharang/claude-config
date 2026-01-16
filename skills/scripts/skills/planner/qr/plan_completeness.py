#!/usr/bin/env python3
"""
QR-Plan-Completeness - Step-based workflow for quality-reviewer sub-agent.

Validates plan document completeness before TW/Developer work:
- Decision Log completeness (all code elements documented)
- Policy default verification (user-specified backing required)
- Architectural assumption validation
- Plan structure (milestones, acceptance criteria, code presence)

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.types import QRState, LoopState, ResourceProvider
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.conventions import get_convention


STEPS = {
    1: {
        "title": "Plan Completeness Review",
    },
    2: {
        "title": "Reference: Default Conventions",
    },
    3: {
        "title": "Verify Decision Log and Policy Defaults",
    },
    4: {
        "title": "Verify Plan Structure",
    },
    5: {
        "title": "Exhaustiveness Verification",
    },
    6: {
        "title": "Self-Validate Suggested Fixes",
    },
    7: {
        "title": "Write Report and Return Result",
    },
}


def step_1_handler(step_info, total_steps, module_path, qr, **kwargs):
    banner = render(W.el("state_banner", checkpoint="QR-COMPLETENESS", iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
    return {
        "title": step_info["title"],
        "actions": [banner, ""]
        + [
            "TASK: Validate plan document completeness before implementation.",
            "",
            "You are reviewing the plan BEFORE Developer fills diffs.",
            "Plan has Code Intent sections but no Code Changes yet.",
            "Your job: verify plan is complete enough for downstream work.",
            "",
            "SCOPE:",
            "  - Decision Log completeness (all non-obvious code elements)",
            "  - Policy defaults (must have user-specified backing)",
            "  - Architectural assumptions (if migration/new tech)",
            "  - Plan structure (milestones, acceptance criteria)",
            "",
            "Read the plan file now. Locate these sections:",
            "  - ## Planning Context (Decision Log, Constraints, Known Risks)",
            "  - ## Milestones (each with acceptance criteria, Code Intent)",
            "  - ## Invisible Knowledge (if present)",
            "",
            "Extract and write out the CONTEXT FILTER before proceeding:",
            "  CONTEXT FILTER:",
            "  - Decisions accepted as given: [list from Decision Log]",
            "  - Alternatives I will not suggest: [list from Rejected Alternatives]",
            "  - Constraints I will respect: [list from Constraints]",
            "  - Risks OUT OF SCOPE: [list from Known Risks]",
        ],
        "next": f"python3 -m {module_path} --step 2 --total-steps {total_steps}",
    }


def step_2_handler(step_info, total_steps, module_path, qr, **kwargs):
    defaults_resource = get_convention("structural.md")
    resource_block = render(W.el("resource", TextNode(defaults_resource), name="default-conventions", purpose="policy-default-verification").build(), XMLRenderer())
    return {
        "title": step_info["title"],
        "actions": [
            "AUTHORITATIVE REFERENCE FOR POLICY DEFAULT VERIFICATION:",
            "",
            resource_block,
            "",
            "KEY CONCEPT: Priority Hierarchy (Tier 1-4)",
            "  Tier 1: user-specified (explicit user instruction)",
            "  Tier 2: doc-derived (CLAUDE.md / project docs)",
            "  Tier 3: default-derived (this document)",
            "  Tier 4: assumption (NO BACKING - MUST CONFIRM WITH USER)",
            "",
            "POLICY DEFAULTS require Tier 1 (user-specified) backing.",
            "Technical defaults can use Tier 2-3 backing.",
            "",
            "Detection principle: IF THIS VALUE WERE WRONG, WHO SUFFERS?",
            "  - Technical defaults: Framework authors suffer -> safe to inherit",
            "  - Policy defaults: This user/org suffers -> must confirm",
        ],
        "next": f"python3 -m {module_path} --step 3 --total-steps {total_steps}",
    }


def step_3_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
        "actions": [
            "CHECK 1: DECISION LOG COMPLETENESS",
            "",
            "For EACH milestone's Code Intent, identify non-obvious elements:",
            "  - Thresholds and magic numbers (timeouts, buffer sizes, retry counts)",
            "  - Concurrency primitives (mutex, channel, atomic)",
            "  - Data structure choices (map vs slice, custom types)",
            "  - Conditional logic with non-obvious predicates",
            "  - Error handling granularity",
            "",
            "For EACH non-obvious element, ask OPEN question:",
            "  'Which Decision Log entry explains this choice?'",
            "",
            "  If found: Verify rationale is multi-step (not single assertion)",
            "    BAD:  'Polling | Webhooks unreliable'",
            "    GOOD: 'Polling | 30% webhook failure -> need fallback anyway'",
            "",
            "  If not found: Record as DECISION_LOG_MISSING",
            "    'M[N]: [element] uses [choice] but no Decision Log entry'",
            "",
            "---",
            "",
            "CHECK 2: POLICY DEFAULT VERIFICATION",
            "",
            "Policy defaults: choices where user/org bears operational consequence.",
            "Common patterns:",
            "  - Lifecycle policies (retention, cleanup timing)",
            "  - Capacity constraints (limits, overflow behavior)",
            "  - Failure handling (retry limits, fallback behavior)",
            "  - Output choices affecting downstream systems",
            "",
            "For EACH policy default in plan, ask OPEN question:",
            "  'What Decision Log entry shows user confirmed this value?'",
            "",
            "  If answer is 'none': Record as POLICY_UNJUSTIFIED",
            "    '[Location]: Policy default [value] chosen without user confirmation'",
            "",
            "---",
            "",
            "CHECK 3: ARCHITECTURAL ASSUMPTION (if applicable)",
            "",
            "SKIP if plan does NOT involve migration, new tech, or major refactoring.",
            "",
            "If applicable, verify with OPEN questions:",
            "  'What architectural approach did the user confirm?'",
            "  'What is the idiomatic usage pattern of target technology?'",
            "  'What abstraction from source does target eliminate/preserve?'",
            "",
            "  If no user-specified citation: Record as ASSUMPTION_UNVALIDATED",
            "    'Unvalidated architectural assumption: [description]'",
        ],
        "next": f"python3 -m {module_path} --step 4 --total-steps {total_steps}",
    }


def step_4_handler(step_info, total_steps, module_path, qr, **kwargs):
    structure_checklist = """<verification_checklist category="plan-structure">
  <item element="Milestones" criterion="Each has acceptance criteria" if_missing="CONVENTION_VIOLATION" />
  <item element="Invisible Knowledge" criterion="Populated if README.md expected" if_missing="IK_TRANSFER_FAILURE" />
  <item element="Planning Context" criterion="Decision Log, Constraints, Risks" if_missing="CONVENTION_VIOLATION" />
  <item element="Documentation MS" criterion="Plan includes doc deliverables" if_missing="CONVENTION_VIOLATION" />
</verification_checklist>"""
    code_presence_checklist = """<verification_checklist category="code-presence">
  <item element="Code Intent with file paths" criterion="Section present with changes" if_missing="PASS" />
  <item element="Documentation-only + all .md" criterion="Skip reason valid" if_missing="PASS" />
  <item element="No Code Intent + source files" criterion="Must have Code Intent" if_missing="CONVENTION_VIOLATION" />
  <item element="Skip reason + source files" criterion="Skip invalid for source" if_missing="CONVENTION_VIOLATION" />
</verification_checklist>"""
    test_spec_checklist = """<verification_checklist category="test-specification">
  <item element="Test file paths + type + scenarios" criterion="Fully specified" if_missing="PASS" />
  <item element="No tests with rationale" criterion="Explicit skip OK" if_missing="PASS" />
  <item element="Documentation-only milestone" criterion="No tests needed" if_missing="PASS" />
  <item element="Empty Tests section" criterion="Must specify or skip" if_missing="TESTING_STRATEGY_VIOLATION" />
  <item element="Implementation MS no Tests" criterion="Must have Tests section" if_missing="TESTING_STRATEGY_VIOLATION" />
</verification_checklist>"""
    return {
        "title": step_info["title"],
        "actions": [
            "CHECK 4: PLAN STRUCTURE VALIDATION",
            "",
            "Verify required elements exist:",
            "",
            structure_checklist,
            "",
            "---",
            "",
            "CHECK 5: CODE PRESENCE VALIDATION",
            "",
            "For EACH milestone, ask OPEN question:",
            "  'What Code Intent does Milestone N contain?'",
            "",
            code_presence_checklist,
            "",
            "---",
            "",
            "CHECK 6: TEST SPECIFICATION VALIDATION",
            "",
            "For EACH implementation milestone, ask OPEN question:",
            "  'What test specification does Milestone N contain?'",
            "",
            test_spec_checklist,
        ],
        "next": f"python3 -m {module_path} --step 5 --total-steps {total_steps}",
    }


def step_5_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
        "actions": [
            "<exhaustiveness_check>",
            "STOP. Before finalizing findings, perform fresh examination.",
            "",
            "This is a SEPARATE verification pass. Do NOT simply review your prior",
            "findings -- re-examine the plan with fresh eyes.",
            "",
            "RE-REVIEW PREVIOUS CHECKS:",
            "",
            "For EACH check from steps 3-4 where you found no issues:",
            "  1. Re-read your assessment with skeptical eyes",
            "  2. Ask: 'Did I accept this too quickly?'",
            "  3. Ask: 'What would I have missed if I was being careless?'",
            "",
            "If still no issues after re-review: proceed",
            "If new issues found: record them using the SAME categories",
            "",
            "CONSTRAINT: Do NOT introduce new check categories.",
            "Only re-examine the checks already performed:",
            "  - Decision Log completeness",
            "  - Policy default verification",
            "  - Architectural assumptions (if applicable)",
            "  - Plan structure",
            "  - Code presence",
            "  - Test specification",
            "</exhaustiveness_check>",
        ],
        "next": f"python3 -m {module_path} --step 6 --total-steps {total_steps}",
    }


def step_6_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 6 - Self-validate suggested fixes."""
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
            "  2. Apply the SAME completeness checks to your suggestion:",
            "     - Does your suggestion contain a policy default without user backing?",
            "     - Does your suggestion make architectural assumptions?",
            "     - Does your suggestion introduce new elements needing Decision Log?",
            "",
            "If your suggested fix VIOLATES a rule:",
            "  - REVISE the suggestion to comply, OR",
            "  - REMOVE the suggestion and report the issue only",
            "",
            "EXAMPLE OF SELF-VIOLATION:",
            "  Finding: Missing Decision Log for retry count",
            "  BAD suggestion: 'Use 3 retries with exponential backoff'",
            "    -- This introduces a policy default (retry=3) without user backing!",
            "  GOOD suggestion: 'Add Decision Log entry explaining retry count choice'",
            "",
            "Record any self-violations found and corrected.",
            "</self_validation>",
        ],
        "next": f"python3 -m {module_path} --step 7 --total-steps {total_steps}",
    }


def step_7_handler(step_info, total_steps, module_path, qr, **kwargs):
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
            "  PASS: Plan completeness verified. Ready for Developer diffs.",
            "",
            "If issues found:",
            "  ISSUES:",
            "    1. [CATEGORY] Description",
            "    2. [CATEGORY] Description",
            "    ...",
            "",
            "CATEGORIES (use exact category names):",
            "  - DECISION_LOG_MISSING: Missing or insufficient Decision Log entry (MUST)",
            "  - POLICY_UNJUSTIFIED: Policy default lacks user-specified backing (MUST)",
            "  - ASSUMPTION_UNVALIDATED: Unvalidated architectural assumption (MUST)",
            "  - IK_TRANSFER_FAILURE: Invisible Knowledge not at BEST location (MUST)",
            "  - CONVENTION_VIOLATION: Missing required plan element (SHOULD)",
            "  - TESTING_STRATEGY_VIOLATION: Missing or empty test specification (SHOULD)",
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
    7: step_7_handler,
}


def get_step_guidance(
    step: int, total_steps: int, module_path: str, provider: ResourceProvider = None, **kwargs
) -> dict:
    """Return guidance for the given step.

    Args:
        step: Current step number (1-indexed)
        total_steps: Total number of steps in this workflow
        module_path: Module path for -m invocation (e.g., skills.planner.qr.plan_completeness)
        **kwargs: Additional context (qr_iteration, qr_fail, etc.)
    """
    qr_iteration = kwargs.get("qr_iteration", 1)
    qr_fail = kwargs.get("qr_fail", False)
    state = LoopState.RETRY if qr_fail else LoopState.INITIAL
    qr = QRState(iteration=qr_iteration, state=state)

    step_info = STEPS.get(step, {})
    handler = STEP_HANDLERS.get(step)

    if step >= total_steps:
        handler = STEP_HANDLERS.get(7)
        step_info = STEPS.get(7, {})

    if handler:
        return handler(step_info, total_steps=total_steps, module_path=module_path, qr=qr, **kwargs)

    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Completeness: Plan completeness validation workflow")
