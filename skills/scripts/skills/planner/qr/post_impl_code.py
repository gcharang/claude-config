#!/usr/bin/env python3
"""
QR-Post-Impl-Code - Step-based workflow for quality-reviewer sub-agent.

Code quality review AFTER all milestones complete:
- Factored verification: acceptance criteria vs implemented code
- Cross-cutting concerns and architectural coherence
- KNOWLEDGE/STRUCTURE/COSMETIC category application

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.types import QRState, LoopState, ResourceProvider
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.conventions import get_convention


STEPS = {
    1: {
        "title": "Code Quality Review",
    },
    2: {
        "title": "Extract Acceptance Criteria (Factored Step 1)",
    },
    3: {
        "title": "Examine Implemented Code (Factored Step 2)",
    },
    4: {
        "title": "Compare and Apply Categories (Factored Step 3)",
    },
    5: {
        "title": "Write Report and Return Result",
    },
}


def step_1_handler(step_info, total_steps, module_path, qr, **kwargs):
    banner = render(W.el("state_banner", checkpoint="CODE QR", iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
    return {
        "title": step_info["title"],
        "actions": [banner, ""]
        + [
            "TASK: Code quality review after ALL milestones complete.",
            "",
            "You are reviewing IMPLEMENTED code, not a plan.",
            "All milestones have been executed. Modified files exist.",
            "",
            "SCOPE:",
            "  - Acceptance criteria verification (factored approach)",
            "  - Cross-cutting concerns across milestones",
            "  - Intent markers, knowledge categories, structural categories",
            "",
            "NOT IN SCOPE (handled by Doc QR):",
            "  - Documentation format (CLAUDE.md)",
            "  - Invisible Knowledge proximity audit",
            "",
            "INPUTS (from your prompt):",
            "  - PLAN: Path to the executed plan file",
            "  - MODIFIED_FILES: List of files changed during implementation",
            "",
            "FIRST: Read the plan file now. Locate:",
            "  - ## Planning Context (for CONTEXT FILTER)",
            "  - ## Milestones (acceptance criteria per milestone)",
            "",
            "Write out CONTEXT FILTER before proceeding:",
            "  CONTEXT FILTER:",
            "  - Decisions accepted as given: [from Decision Log]",
            "  - Alternatives I will not suggest: [from Rejected Alternatives]",
            "  - Constraints I will respect: [from Constraints]",
            "  - Risks OUT OF SCOPE: [from Known Risks]",
        ],
        "next": f"python3 -m {module_path} --step 2 --total-steps {total_steps}",
    }


def step_2_handler(step_info, total_steps, module_path, qr, **kwargs):
    factored_rationale = """<factored_verification_rationale>
WHY FACTORED: Read criteria -> Examine code -> Compare

PREVENTS:
  - Confirmation bias (seeing what you expect)
  - Post-hoc rationalization (making code fit criteria)
  - Selective attention (missing what doesn't fit)

REQUIRES:
  - Write expectations BEFORE reading code
  - No modifications after code examination
  - Explicit comparison in separate step
</factored_verification_rationale>"""
    return {
        "title": step_info["title"],
        "actions": [
            "FACTORED VERIFICATION PROTOCOL - Step 1 of 3",
            "",
            factored_rationale,
            "",
            "For EACH milestone in the plan:",
            "",
            "  1. Read the milestone's acceptance criteria",
            "  2. Write down what you EXPECT to observe in code:",
            "",
            "  MILESTONE [N] EXPECTATIONS:",
            "  | Criterion                      | Expected Code Evidence       |",
            "  | ------------------------------ | ---------------------------- |",
            "  | [criterion text from plan]     | [what you expect to find]    |",
            "  | Returns 429 after 3 failures   | counter, threshold=3, 429    |",
            "  | ...                            | ...                          |",
            "",
            "CRITICAL: Write ALL expectations BEFORE reading any code.",
            "Do not modify expectations after reading code.",
            "",
            "You will examine actual code in the NEXT step.",
        ],
        "next": f"python3 -m {module_path} --step 3 --total-steps {total_steps}",
    }


def step_3_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
        "actions": [
            "FACTORED VERIFICATION PROTOCOL - Step 2 of 3",
            "",
            "EXAMINE code WITHOUT re-reading acceptance criteria.",
            "Note what the code ACTUALLY does, not what it should do.",
            "",
            "For EACH file in MODIFIED_FILES:",
            "",
            "  1. Read the file content",
            "  2. Document what you observe:",
            "",
            "  FILE: [path]",
            "  | Function/Section        | What It Actually Does               |",
            "  | ----------------------- | ----------------------------------- |",
            "  | rate_limit_check()      | counter incremented, threshold = 5  |",
            "  | ...                     | ...                                 |",
            "",
            "ALSO NOTE while reading:",
            "  - Intent markers: :PERF: and :UNSAFE: (validate format)",
            "  - Knowledge issues: temporal contamination, baseline references",
            "  - Structural issues: god objects/functions, duplicate logic",
            "  - Cross-cutting patterns: shared state, error propagation, naming",
            "",
            "FORBIDDEN: Do not look back at acceptance criteria yet.",
            "You will compare in the NEXT step.",
        ],
        "next": f"python3 -m {module_path} --step 4 --total-steps {total_steps}",
    }


def step_4_handler(step_info, total_steps, module_path, qr, **kwargs):
    defaults_resource = get_convention("structural.md")
    naming_resource = get_convention("code-quality/01-naming-and-types.md")
    structure_resource = get_convention("code-quality/02-structure-and-composition.md")
    patterns_resource = get_convention("code-quality/03-patterns-and-idioms.md")
    repetition_resource = get_convention("code-quality/04-repetition-and-consistency.md")
    docs_resource = get_convention("code-quality/05-documentation-and-tests.md")
    modules_resource = get_convention("code-quality/06-module-and-dependencies.md")
    crossfile_resource = get_convention("code-quality/07-cross-file-consistency.md")
    codebase_resource = get_convention("code-quality/08-codebase-patterns.md")
    return {
        "title": step_info["title"],
        "actions": [
            "FACTORED VERIFICATION PROTOCOL - Step 3 of 3",
            "",
            "NOW compare your expectations (Step 2) with observations (Step 3).",
            "",
            "COMPARISON TABLE:",
            "  | Milestone | Criterion        | Expected       | Observed       | Match? |",
            "  | --------- | ---------------- | -------------- | -------------- | ------ |",
            "  | M1        | 429 after 3 fail | threshold=3    | threshold=5    | NO     |",
            "  | ...       | ...              | ...            | ...            | ...    |",
            "",
            "For EACH mismatch, record as finding.",
            "",
            "---",
            "",
            "CATEGORY APPLICATION (to code observations from Step 3):",
            "",
            "INTENT MARKERS (MUST severity):",
            "  Detect :PERF: and :UNSAFE: markers",
            "  Valid format: ':MARKER: [what]; [why]' (semicolon required, non-empty why)",
            "  Invalid format -> Report MARKER_INVALID (MUST)",
            "  Valid marker -> Skip relevant checks for marked code",
            "",
            "KNOWLEDGE CATEGORIES (MUST severity):",
            "  TEMPORAL_CONTAMINATION: Change-relative language in comments",
            "  BASELINE_REFERENCE: References to removed/replaced code",
            "  LLM_COMPREHENSION_RISK: Pattern confusing to future LLM",
            "  Ask: 'Would future reader understand without knowing prior state?'",
            "",
            "STRUCTURAL CATEGORIES (SHOULD severity):",
            "  Apply all 8 code quality documents. Key checks:",
            "  - Naming precision (01): vague names, misleading names, domain mismatch",
            "  - Function composition (02): god functions, >50 lines, >3 nesting",
            "  - Pattern misuse (03): language idiom violations, anti-patterns",
            "  - Duplication (04): copy-pasted blocks, parallel functions",
            "  - Documentation (05): missing why-comments, test coverage gaps",
            "  - Module organization (06): circular deps, misplaced exports",
            "  - Cross-file consistency (07): error handling divergence, API contract violations",
            "  - Codebase patterns (08): architectural drift, layering violations",
            "  CONVENTION_VIOLATION: Violates documented project convention",
            "  Ask: 'What project documentation specifies this standard?'",
            "",
            "COSMETIC CATEGORIES (COULD severity):",
            "  FORMATTER_FIXABLE: Style fixable by formatter/linter",
            "  MINOR_INCONSISTENCY: Non-conformance with no documented rule",
            "",
            "Reference for structural thresholds:",
            "",
            defaults_resource,
            "",
            "=" * 60,
            "CODE QUALITY REFERENCES (All 8 Documents):",
            "=" * 60,
            "01. NAMING AND TYPES:",
            naming_resource,
            "",
            "02. STRUCTURE AND COMPOSITION:",
            structure_resource,
            "",
            "03. PATTERNS AND IDIOMS:",
            patterns_resource,
            "",
            "04. REPETITION AND CONSISTENCY:",
            repetition_resource,
            "",
            "05. DOCUMENTATION AND TESTS:",
            docs_resource,
            "",
            "06. MODULE AND DEPENDENCIES:",
            modules_resource,
            "",
            "07. CROSS-FILE CONSISTENCY:",
            crossfile_resource,
            "",
            "08. CODEBASE PATTERNS:",
            codebase_resource,
        ],
        "next": f"python3 -m {module_path} --step 5 --total-steps {total_steps}",
    }


def step_5_handler(step_info, total_steps, module_path, qr, **kwargs):
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
            "```xml",
            '<qr_findings status="PASS | ISSUES">',
            "  <summary>",
            "    <verdict>PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES | MUST_ISSUES</verdict>",
            "    <standards_applied>[from project docs, or 'conventions/structural.md']</standards_applied>",
            "  </summary>",
            "",
            "  <!-- Group findings by milestone for targeted fixes -->",
            '  <milestone number="1" name="Milestone Name">',
            '    <finding category="MARKER_INVALID" severity="MUST">',
            "      <location>file:line or function name</location>",
            "      <issue>What is wrong</issue>",
            "      <failure_mode>Why this matters</failure_mode>",
            "      <suggested_fix>Concrete action</suggested_fix>",
            "      <confidence>HIGH | MEDIUM | LOW</confidence>",
            "    </finding>",
            "  </milestone>",
            "",
            "  <acceptance_criteria>",
            '    <milestone number="1">',
            '      <criterion text="Returns 429 after 3 failures">MET | NOT_MET</criterion>',
            "    </milestone>",
            "  </acceptance_criteria>",
            "",
            "  <reasoning>How you arrived at verdict</reasoning>",
            "</qr_findings>",
            "```",
            "",
            "GROUPING RATIONALE:",
            "  Findings grouped by milestone so developer knows fix scope.",
            "  Cross-cutting issues: assign to most relevant milestone.",
            "",
            "VERDICT GUIDE:",
            "  PASS: All criteria met, no issues",
            "  PASS_WITH_CONCERNS: All criteria met, only COULD severity",
            "  NEEDS_CHANGES: SHOULD or MUST severity issues requiring fixes",
            "  MUST_ISSUES: MUST severity issues (unrecoverable if missed)",
        ],
        "next": "Return minimal result to orchestrator. Sub-agent task complete.",
    }


STEP_HANDLERS = {
    1: step_1_handler,
    2: step_2_handler,
    3: step_3_handler,
    4: step_4_handler,
    5: step_5_handler,
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
    mode_main(__file__, get_step_guidance, "QR-Post-Impl-Code: Code quality review workflow")
