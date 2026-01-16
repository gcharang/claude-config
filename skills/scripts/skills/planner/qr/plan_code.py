#!/usr/bin/env python3
"""
QR-Plan-Code - Step-based workflow for quality-reviewer sub-agent.

Validates proposed code changes in plan files before TW scrub:
- Diff context matches actual codebase
- KNOWLEDGE/STRUCTURE/COSMETIC category application
- Intent marker validation

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.types import QRState, LoopState, ResourceProvider
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.conventions import get_convention


STEPS = {}


def step_1_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 1."""
    banner = render(W.el("state_banner", checkpoint="QR-CODE", iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
    return {
        "title": "Code Quality Review",
        "actions": [banner, ""] + step_info["actions"],
        "next": f"python3 -m {module_path} --step 2 --total-steps {total_steps}",
    }


def step_2_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 2."""
    return {
        "title": step_info["title"],
        "actions": step_info["actions"],
        "next": f"python3 -m {module_path} --step 3 --total-steps {total_steps}",
    }


def step_3_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 3."""
    return {
        "title": step_info["title"],
        "actions": step_info["actions"],
        "next": f"python3 -m {module_path} --step 4 --total-steps {total_steps}",
    }


def step_4_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 4."""
    diff_resource = get_convention("diff-format.md")
    return {
        "title": step_info["title"],
        "actions": [
            "AUTHORITATIVE REFERENCE FOR CODE CHANGE VALIDATION:",
            "",
            "=" * 60,
            diff_resource,
            "=" * 60,
            "",
            "Use this reference when validating diff structure.",
            "Key points:",
            "  - File path: AUTHORITATIVE (must be exact)",
            "  - Line numbers: APPROXIMATE (may drift)",
            "  - Context lines: AUTHORITATIVE ANCHORS",
            "  - Comments in + lines: explain WHY, not WHAT",
        ],
        "next": f"python3 -m {module_path} --step 5 --total-steps {total_steps}",
    }


def step_5_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 5."""
    naming_resource = get_convention("code-quality/01-naming-and-types.md")
    structure_resource = get_convention("code-quality/02-structure-and-composition.md")
    patterns_resource = get_convention("code-quality/03-patterns-and-idioms.md")
    repetition_resource = get_convention("code-quality/04-repetition-and-consistency.md")
    docs_resource = get_convention("code-quality/05-documentation-and-tests.md")
    return {
        "title": step_info["title"],
        "actions": step_info["actions"] + [
            "",
            "=" * 60,
            "CODE QUALITY REFERENCES (Diff Review Applicable):",
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
        ],
        "next": f"python3 -m {module_path} --step 6 --total-steps {total_steps}",
    }


def step_6_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 6."""
    return {
        "title": step_info["title"],
        "actions": step_info["actions"],
        "next": f"python3 -m {module_path} --step 7 --total-steps {total_steps}",
    }


def step_7_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for step 7 - Self-validate suggested fixes."""
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
            "  2. Apply the SAME checks from steps 4-5 to your suggestion:",
            "     - TEMPORAL_CONTAMINATION: 'Added', 'Replaced', 'Now uses'?",
            "     - BASELINE_REFERENCE: 'instead of', 'previously', 'replaces'?",
            "     - Any taxonomy category violation?",
            "",
            "If your suggested fix VIOLATES a rule:",
            "  - REVISE the suggestion to comply, OR",
            "  - REMOVE the suggestion and report the issue only",
            "",
            "EXAMPLE OF SELF-VIOLATION:",
            "  Finding: 'existing call sites' contains temporal reference",
            "  BAD suggestion: 'Eliminates scattered checks' -- 'Eliminates' is temporal!",
            "  GOOD suggestion: '14 call sites in QR/TW/Dev modules'",
            "",
            "Record any self-violations found and corrected.",
            "</self_validation>",
        ],
        "next": f"python3 -m {module_path} --step 8 --total-steps {total_steps}",
    }


def step_final_handler(step_info, total_steps, module_path, qr, **kwargs):
    """Handler for final step."""
    return {
        "title": step_info["title"],
        "actions": step_info["actions"],
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
        module_path: Module path for -m invocation
        **kwargs: Additional context (qr_iteration, qr_fail, etc.)
    """
    qr_iteration = kwargs.get("qr_iteration", 1)
    qr_fail = kwargs.get("qr_fail", False)
    state = LoopState.RETRY if qr_fail else LoopState.INITIAL
    qr = QRState(iteration=qr_iteration, state=state)

    # Initialize STEPS on first use
    if not STEPS:
        STEPS.update({
            1: {
                "title": "Code Quality Review",
                "actions": [
                    "TASK: Validate proposed code changes in plan file.",
                    "",
                    "You are reviewing the plan AFTER Developer filled diffs.",
                    "Developer has converted Code Intent to Code Changes.",
                    "Your job: verify diffs are sound before TW documents them.",
                    "",
                    "SCOPE:",
                    "  - All diff blocks in milestone Code Changes sections",
                    "  - Context lines must match actual codebase",
                    "  - Intent markers (:PERF:, :UNSAFE:) validation",
                    "  - Knowledge categories (temporal contamination, baseline references)",
                    "  - Structural categories (god objects, duplicate logic, error handling)",
                    "  - Cosmetic categories (dead code, formatting)",
                    "",
                    "Read the plan file now. Note all milestones with Code Changes.",
                ],
            },
            2: {
                "title": "Pre-Work: Read Codebase",
                "actions": [
                    "BEFORE reviewing diffs, you MUST read the actual codebase:",
                    "",
                    "1. For EACH file referenced in plan milestones:",
                    "   - Read the current file content",
                    "   - Note existing patterns, conventions, error handling",
                    "",
                    "2. For EACH new file proposed:",
                    "   - Verify target directory exists",
                    "   - Check for similar existing files that might be extended",
                    "",
                    "3. Document what you found:",
                    "   ```",
                    "   CODEBASE CHECK:",
                    "   - [file]: Read [N] lines, patterns observed: [...]",
                    "   - [directory]: [EXISTS/MISSING]",
                    "   ```",
                    "",
                    "STOP CHECK: For each milestone with source file modifications,",
                    "  does it contain diff blocks?",
                    "  - If NO diffs AND milestone modifies .go/.py/.js/etc files:",
                    "    Flag CONVENTION_VIOLATION (SHOULD): 'Milestone N lacks code changes'",
                ],
            },
            3: {
                "title": "Verify Diff Context Lines",
                "actions": [
                    "For EACH diff block in the plan, verify context lines:",
                    "",
                    "1. Extract context lines (lines starting with ' ' in diff)",
                    "",
                    "2. Search for these patterns in the actual file content",
                    "",
                    "<example type='CORRECT'>",
                    "Plan context: '    for item in items:'",
                    "Actual file:  '    for item in items:  # process each'",
                    "Match: YES (whitespace/comment differs, pattern matches)",
                    "</example>",
                    "",
                    "<example type='INCORRECT'>",
                    "Plan context: '    for item in items:'",
                    "Actual file:  '    list(map(process, items))'",
                    "Match: NO (logic restructured, context no longer exists)",
                    "</example>",
                    "",
                    "3. Document match status:",
                    "   ```",
                    "   CONTEXT VERIFICATION:",
                    "   - [file] M[N]: Context lines [MATCH/MISMATCH] at line [L]",
                    "   ```",
                    "",
                    "4. If MISMATCH:",
                    "   Flag BASELINE_REFERENCE: 'Diff context mismatch in [file]'",
                    "   Cause: Plan may be based on outdated code",
                    "",
                    "NOTE: Line numbers in @@ headers are APPROXIMATE.",
                    "Context patterns are AUTHORITATIVE anchors.",
                    "Focus on pattern matching, not line number matching.",
                ],
            },
            4: {
                "title": "Reference: Diff Format Specification",
            },
            5: {
                "title": "Apply Taxonomy to Proposed Code",
                "actions": [
                    "For EACH diff block, check categories:",
                    "",
                    "INTENT MARKERS (MUST severity):",
                    "  Detect :PERF: and :UNSAFE: markers",
                    "  Valid format: ':MARKER: [what]; [why]' (semicolon required, non-empty why)",
                    "  Invalid format -> Report MARKER_INVALID (MUST)",
                    "  Valid marker -> Skip relevant checks for marked code",
                    "",
                    "KNOWLEDGE CATEGORIES (MUST severity):",
                    "  TEMPORAL_CONTAMINATION: Change-relative language ('Added', 'Replaced', 'Now uses')",
                    "  BASELINE_REFERENCE: Compare to removed code ('Instead of', 'Previously')",
                    "  LLM_COMPREHENSION_RISK: Pattern confusing to future LLM",
                    "",
                    "STRUCTURAL CATEGORIES (SHOULD severity):",
                    "  Apply code quality documents 01-05. Key checks:",
                    "  - Naming precision (01): vague names, misleading names, domain mismatch",
                    "  - Function composition (02): god functions, >50 lines, >3 nesting",
                    "  - Pattern misuse (03): language idiom violations, anti-patterns",
                    "  - Duplication (04): copy-pasted blocks, parallel functions",
                    "  - Documentation (05): missing why-comments, test coverage gaps",
                    "  CONVENTION_VIOLATION: Violates documented project convention",
                    "",
                    "COSMETIC CATEGORIES (COULD severity):",
                    "  FORMATTER_FIXABLE: Style fixable by formatter/linter",
                    "  MINOR_INCONSISTENCY: Non-conformance with no documented rule",
                    "",
                    "PLAN-CODE SPECIFIC:",
                    "  - Module bloat: adds many functions to already-large module?",
                    "  - Responsibility overlap: similar scope to existing module?",
                    "",
                    "Record each finding with:",
                    "  [CATEGORY] [SEVERITY]: description (file:line)",
                ],
            },
            6: {
                "title": "Exhaustiveness Verification",
                "actions": [
                    "<exhaustiveness_check>",
                    "STOP. Before finalizing findings, perform fresh examination.",
                    "",
                    "This is a SEPARATE verification pass. Do NOT simply review your prior",
                    "findings -- re-examine the diffs with fresh eyes.",
                    "",
                    "ADVERSARIAL QUESTIONS (answer each with specific findings or 'none'):",
                    "",
                    "1. What FAILURE MODES have you not yet checked?",
                    "   (e.g., nil pointer, resource leak, race condition, timeout)",
                    "",
                    "2. For each diff, what could go WRONG at runtime?",
                    "   List concrete scenarios.",
                    "",
                    "3. What EDGE CASES does the code not handle?",
                    "   (e.g., empty input, max values, concurrent access)",
                    "",
                    "4. What would a HOSTILE reviewer find that you missed?",
                    "   Imagine someone whose job is to find bugs you overlooked.",
                    "",
                    "5. What CONTEXT DRIFT might exist between plan and codebase?",
                    "   Are there changes to the codebase the plan doesn't account for?",
                    "",
                    "Record any NEW issues discovered. These are ADDITIONAL findings,",
                    "not duplicates of prior checks.",
                    "</exhaustiveness_check>",
                ],
            },
        })
        STEPS[7] = {
            "title": "Self-Validate Suggested Fixes",
            "actions": [],  # Handled by step_7_handler
        }
        STEPS[8] = {
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
                "  PASS: Code changes validated. Context matches codebase.",
                "",
                "If issues found:",
                "  ISSUES:",
                "    1. [MARKER_INVALID MUST] :PERF: without explanation (M2:file.py:45)",
                "    2. [TEMPORAL_CONTAMINATION MUST] 'Added mutex' comment (M1:api.go:12)",
                "    3. [GOD_FUNCTION SHOULD] Function >80 lines (M3:handler.py:80)",
                "    4. [BASELINE_REFERENCE MUST] Diff context mismatch (M1:service.go)",
                "    5. [DEAD_CODE COULD] Unreachable branch (M4:util.py:100)",
                "    ...",
                "",
                "SEVERITY GUIDE:",
                "  - MUST: Knowledge categories, marker validation (unrecoverable)",
                "  - SHOULD: Structural categories (maintainability debt)",
                "  - COULD: Cosmetic categories (auto-fixable)",
            ],
        }

    # Get handler for this step
    handler = STEP_HANDLERS.get(step, step_final_handler if step >= total_steps else None)
    if handler:
        return handler(STEPS[step] if step in STEPS else {"title": "Write Report and Return Result", "actions": []},
                      total_steps, module_path, qr)

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Code: Code change validation workflow")
