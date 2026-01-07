#!/usr/bin/env python3
"""
QR-Post-Impl-Code - Step-based workflow for quality-reviewer sub-agent.

Code quality review AFTER all milestones complete:
- Factored verification: acceptance criteria vs implemented code
- Cross-cutting concerns and architectural coherence
- KNOWLEDGE/STRUCTURE/COSMETIC category application

Usage:
    python3 qr/post-impl-code.py --step 1 --total-steps 5 [--qr-iteration 1] [--qr-fail]

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
    format_qr_banner,
    format_factored_verification_rationale,
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
        banner = format_qr_banner("CODE QR", qr)
        return {
            "title": "Code Quality Review",
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
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Acceptance criteria extraction (factored - read criteria first)
    if step == 2:
        return {
            "title": "Extract Acceptance Criteria (Factored Step 1)",
            "actions": [
                "FACTORED VERIFICATION PROTOCOL - Step 1 of 3",
                "",
                format_factored_verification_rationale(),
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
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Code examination (factored - examine without re-reading criteria)
    if step == 3:
        return {
            "title": "Examine Implemented Code (Factored Step 2)",
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
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Comparison and category application
    if step == 4:
        defaults_resource = get_resource("default-conventions.md")
        return {
            "title": "Compare and Apply Categories (Factored Step 3)",
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
                "  GOD_OBJECT: >15 public methods OR >10 deps OR mixed concerns",
                "  GOD_FUNCTION: >50 lines OR >3 nesting levels",
                "  DUPLICATE_LOGIC: Copy-pasted blocks or parallel functions",
                "  INCONSISTENT_ERROR_HANDLING: Mixed exceptions/codes in same module",
                "  CONVENTION_VIOLATION: Violates documented project convention",
                "  Ask: 'What project documentation specifies this standard?'",
                "",
                "COSMETIC CATEGORIES (COULD severity):",
                "  DEAD_CODE: Unused functions, impossible branches",
                "  FORMATTER_FIXABLE: Style fixable by formatter/linter",
                "  MINOR_INCONSISTENCY: Non-conformance with no documented rule",
                "",
                "Reference for structural thresholds:",
                "",
                defaults_resource,
            ],
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Output format (final step) - XML grouped by milestone
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
                "```xml",
                '<qr_findings status="PASS | ISSUES">',
                "  <summary>",
                "    <verdict>PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES | MUST_ISSUES</verdict>",
                "    <standards_applied>[from project docs, or 'default-conventions.md']</standards_applied>",
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

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Post-Impl-Code: Code quality review workflow")
