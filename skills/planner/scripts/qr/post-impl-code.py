#!/usr/bin/env python3
"""
QR-Post-Impl-Code - Step-based workflow for quality-reviewer sub-agent.

Code quality review AFTER all milestones complete:
- Factored verification: acceptance criteria vs implemented code
- Cross-cutting concerns and architectural coherence
- RULE 0/1/2 on implemented code

Usage:
    python3 qr/post-impl-code.py --step 1 --total-steps 5 [--qr-iteration 1] [--qr-fail]

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared import (
    QRState,
    get_resource,
    format_qr_banner,
    format_factored_verification_rationale,
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
                "  - RULE 0/1/2 on implemented code",
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
                "  - RULE 0 signals: unhandled errors, silent failures, data loss paths",
                "  - Cross-cutting patterns: shared state, error propagation, naming",
                "",
                "FORBIDDEN: Do not look back at acceptance criteria yet.",
                "You will compare in the NEXT step.",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Comparison and RULE 0/1/2 application
    if step == 4:
        defaults_resource = get_resource("default-conventions.md")
        return {
            "title": "Compare and Apply Rules (Factored Step 3)",
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
                "RULE APPLICATION (to code observations from Step 3):",
                "",
                "RULE 0 (Production Reliability) - CRITICAL/HIGH:",
                "  Ask OPEN questions (not yes/no):",
                "    'What happens when [error condition] occurs?'",
                "    'What data could be lost if [operation] is interrupted?'",
                "",
                "  For CRITICAL findings, verify via dual-path reasoning:",
                "    Forward:  'If X happens, then Y, therefore Z (failure)'",
                "    Backward: 'For Z to occur, Y must happen, which requires X'",
                "    Both paths must converge for CRITICAL. Otherwise HIGH.",
                "",
                "RULE 1 (Project Conformance) - HIGH:",
                "  Only flag if project documentation specifies a standard.",
                "  'Does [code] violate [specific documented standard]?'",
                "",
                "RULE 2 (Structural Quality) - SHOULD_FIX/SUGGESTION:",
                "  Apply ONLY these categories (reference below).",
                "  Do not invent additional categories.",
                "",
                defaults_resource,
            ],
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Output format (final step) - XML grouped by milestone
    if step >= total_steps:
        return {
            "title": "Format Output (XML by Milestone)",
            "actions": [
                "OUTPUT FORMAT (XML grouped by milestone for targeted fixes):",
                "",
                "```xml",
                '<qr_findings status="PASS | ISSUES">',
                "  <summary>",
                "    <verdict>PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES | CRITICAL</verdict>",
                "    <standards_applied>[from project docs, or 'RULE 0 + RULE 2 only']</standards_applied>",
                "  </summary>",
                "",
                "  <!-- Group findings by milestone for targeted fixes -->",
                '  <milestone number="1" name="Milestone Name">',
                '    <finding rule="RULE0" severity="CRITICAL">',
                "      <location>file:line or function name</location>",
                "      <issue>What is wrong</issue>",
                "      <failure_mode>Why this matters</failure_mode>",
                "      <suggested_fix>Concrete action</suggested_fix>",
                "      <confidence>HIGH | MEDIUM | LOW</confidence>",
                "    </finding>",
                "    <!-- more findings for this milestone -->",
                "  </milestone>",
                "",
                '  <milestone number="2" name="Another Milestone">',
                "    <!-- findings for milestone 2 -->",
                "  </milestone>",
                "",
                "  <!-- Cross-cutting issues: assign to most relevant milestone -->",
                "",
                "  <acceptance_criteria>",
                '    <milestone number="1">',
                '      <criterion text="Returns 429 after 3 failures">MET | NOT_MET</criterion>',
                "    </milestone>",
                '    <milestone number="2">',
                '      <criterion text="...">MET | NOT_MET</criterion>',
                "    </milestone>",
                "  </acceptance_criteria>",
                "",
                "  <reasoning>How you arrived at verdict</reasoning>",
                "  <considered_not_flagged>Patterns examined but not issues</considered_not_flagged>",
                "</qr_findings>",
                "```",
                "",
                "GROUPING RATIONALE:",
                "  Findings grouped by milestone so developer knows fix scope.",
                "  Cross-cutting issues: assign to most relevant milestone.",
                "",
                "VERDICT GUIDE:",
                "  PASS: All criteria met, no issues",
                "  PASS_WITH_CONCERNS: All criteria met, minor suggestions",
                "  NEEDS_CHANGES: Issues requiring fixes",
                "  CRITICAL: Production reliability risks",
                "",
                "Return PASS or ISSUES to orchestrator.",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from shared import mode_main
    mode_main(__file__, get_step_guidance, "QR-Post-Impl-Code: Code quality review workflow")
