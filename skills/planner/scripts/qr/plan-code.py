#!/usr/bin/env python3
"""
QR-Plan-Code - Step-based workflow for quality-reviewer sub-agent.

Validates proposed code changes in plan files before TW scrub:
- Diff context matches actual codebase
- KNOWLEDGE/STRUCTURE/COSMETIC category application
- Intent marker validation

Usage:
    python3 qr/plan-code.py --step 1 --total-steps 7 [--qr-iteration 1] [--qr-fail]

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
    format_expected_output,
)

from skills.lib.conventions import get_convention


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
        banner = format_qr_banner("QR-CODE", qr)
        return {
            "title": "Code Quality Review",
            "actions": [banner, ""]
            + [
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
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Read codebase pre-work
    if step == 2:
        return {
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
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Verify diff context
    if step == 3:
        return {
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
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Resource injection (diff format reference)
    if step == 4:
        diff_resource = get_convention("diff-format.md")
        return {
            "title": "Reference: Diff Format Specification",
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
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Category application
    if step == 5:
        return {
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
                "  GOD_OBJECT: >15 public methods OR >10 deps OR mixed concerns",
                "  GOD_FUNCTION: >50 lines OR >3 nesting levels",
                "  DUPLICATE_LOGIC: Copy-pasted blocks or parallel functions",
                "  INCONSISTENT_ERROR_HANDLING: Mixed exceptions/codes in same module",
                "  CONVENTION_VIOLATION: Violates documented project convention",
                "",
                "COSMETIC CATEGORIES (COULD severity):",
                "  DEAD_CODE: Unused functions, impossible branches",
                "  FORMATTER_FIXABLE: Style fixable by formatter/linter",
                "  MINOR_INCONSISTENCY: Non-conformance with no documented rule",
                "",
                "PLAN-CODE SPECIFIC:",
                "  - Module bloat: adds many functions to already-large module? -> GOD_OBJECT",
                "  - Responsibility overlap: similar scope to existing module? -> DUPLICATE_LOGIC",
                "",
                "Record each finding with:",
                "  [CATEGORY] [SEVERITY]: description (file:line)",
            ],
            "next": f"python3 {script_path} --step 6 --total-steps {total_steps}",
        }

    # Step 6: Exhaustiveness verification (fresh second-pass)
    if step == 6:
        return {
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
            "next": f"python3 {script_path} --step 7 --total-steps {total_steps}",
        }

    # Step 7: Output format (final step)
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
            "next": "Return minimal result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Code: Code change validation workflow")
