#!/usr/bin/env python3
"""
QR-Batch-Review - Step-based workflow for quality-reviewer sub-agent.

Wave milestone verification AFTER wave execution:
- Factored verification: acceptance criteria vs implemented code
- RULE 0 (production reliability) + RULE 1 (project conformance)
- Cross-milestone consistency (when multiple milestones in wave)
- Skip RULE 2 (deferred to holistic post-implementation)

Usage:
    python3 qr/batch-review.py --step 1 --total-steps 5 [--qr-iteration 1] [--qr-fail]

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared import (
    QRState,
    format_step_output,
    format_qr_banner,
    format_verification_checklist,
    format_expected_output,
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
        banner = format_qr_banner("WAVE QR (BATCH REVIEW)", qr)
        return {
            "title": "Wave Milestone Verification",
            "actions": [banner, ""]
            + [
                "TASK: Quality gate after wave of milestones executes.",
                "",
                "You are reviewing IMPLEMENTED code, not a plan.",
                "Wave milestones have been executed. Modified files exist.",
                "",
                "SCOPE:",
                "  - Acceptance criteria for ALL milestones in wave",
                "  - RULE 0 (production reliability) - CRITICAL/HIGH",
                "  - RULE 1 (project conformance) - HIGH",
                "  - Cross-milestone consistency (if wave has N > 1 milestones)",
                "",
                "OUT OF SCOPE:",
                "  - RULE 2 (structural quality) - deferred to holistic review",
                "  - Structural issues span waves; per-wave would flag incomplete patterns",
                "",
                "INPUTS (from your prompt):",
                "  - PLAN: Path to the executed plan file",
                "  - MILESTONES: List of milestone numbers in this wave",
                "  - MODIFIED_FILES: List of files changed during wave execution",
                "",
                "FIRST: Read the plan file now. Locate:",
                "  - ## Planning Context (for CONTEXT FILTER)",
                "  - ## Milestones (acceptance criteria for wave milestones)",
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
                "FACTORED VERIFICATION PROTOCOL - Step 1 of 2",
                "",
                format_factored_verification_rationale(),
                "",
                "For EACH milestone in this WAVE (not all milestones):",
                "",
                "  1. Read the milestone's acceptance criteria from the plan",
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

    # Step 3: Code examination + RULE 0/1 application
    if step == 3:
        return {
            "title": "Examine Code and Apply RULE 0/1 (Factored Step 2)",
            "actions": [
                "FACTORED VERIFICATION PROTOCOL - Step 2 of 2",
                "",
                "EXAMINE code and compare to expectations from Step 2.",
                "",
                "For EACH file in MODIFIED_FILES:",
                "",
                "  1. Read the file content",
                "  2. Document what you observe",
                "  3. Compare to expectations",
                "",
                "COMPARISON TABLE:",
                "  | Milestone | Criterion        | Expected       | Observed       | Match? |",
                "  | --------- | ---------------- | -------------- | -------------- | ------ |",
                "  | M1        | 429 after 3 fail | threshold=3    | threshold=5    | NO     |",
                "  | ...       | ...              | ...            | ...            | ...    |",
                "",
                "---",
                "",
                "RULE APPLICATION (RULE 0 + RULE 1 only, skip RULE 2):",
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
                "SKIP RULE 2:",
                "  Structural issues (god objects, duplicate logic, etc.) are deferred",
                "  to the holistic post-implementation QR. Do NOT flag RULE 2 here.",
                "",
                "Record findings as:",
                "  [RULE 0 SEVERITY]: description (file:line)",
                "  [RULE 1 HIGH]: description (file:line)",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Cross-milestone consistency (if multiple milestones)
    if step == 4:
        return {
            "title": "Cross-Milestone Consistency Check",
            "actions": [
                "CROSS-MILESTONE CONSISTENCY (if wave has multiple milestones)",
                "",
                "If wave has only ONE milestone: Skip to output format.",
                "  Write: 'Cross-milestone: N/A - single milestone wave'",
                "",
                "If wave has MULTIPLE milestones:",
                "  Parallel work may introduce inconsistencies.",
                "  Check these areas between milestones:",
                "",
                "  1. SHARED TYPE DEFINITIONS:",
                "     - Do milestones use compatible types?",
                "     - Any type name collisions with different shapes?",
                "",
                "  2. INTERFACE CONTRACTS:",
                "     - Do milestones that interact use matching signatures?",
                "     - Are return types consistent?",
                "",
                "  3. ERROR HANDLING:",
                "     - Is error propagation consistent across milestone boundaries?",
                "     - Do error types match between caller and callee?",
                "",
                "  4. NAMING CONVENTIONS:",
                "     - Are names consistent across parallel work?",
                "     - Any conflicting abbreviations or styles?",
                "",
                "FORMAT:",
                "  | Check                    | Milestones | Status     | Notes          |",
                "  | ------------------------ | ---------- | ---------- | -------------- |",
                "  | Shared type definitions  | M1, M2     | Consistent | User struct ok |",
                "  | Interface contracts      | M1, M2     | MISMATCH   | Save() sig     |",
                "  | ...                      | ...        | ...        | ...            |",
                "",
                "Flag any MISMATCH as finding (use appropriate severity).",
            ],
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Output format (final step)
    if step >= total_steps:
        return {
            "title": "Format Output",
            "actions": [
                "OUTPUT FORMAT:",
                "",
                "```",
                "## WAVE REVIEW: Milestones [list]",
                "",
                "**Gate Decision**: PASS | ISSUES",
                "",
                "### Acceptance Criteria",
                "",
                "#### Milestone N",
                "| Criterion             | Status        | Evidence    |",
                "|-----------------------|---------------|-------------|",
                "| [criterion from plan] | MET / NOT_MET | [file:line] |",
                "",
                "[Repeat for each milestone in wave]",
                "",
                "### RULE 0 Findings (Production Reliability)",
                "[List any production risks found, or 'None found']",
                "Format: [SEVERITY]: description (file:line)",
                "",
                "### RULE 1 Findings (Project Conformance)",
                "[List any conformance violations found, or 'None found']",
                "Format: [HIGH]: description (file:line)",
                "",
                "### Cross-Milestone Consistency",
                "[If single milestone: 'N/A - single milestone wave']",
                "[If multiple: list any inconsistencies, or 'Consistent']",
                "",
                "### Gate Rationale",
                "[If PASS: brief confirmation that all criteria met, no blocking issues]",
                "[If ISSUES: list issues that must be resolved before proceeding]",
                "```",
                "",
                "GATE DECISION GUIDE:",
                "  PASS: All acceptance criteria MET, no RULE 0/1 findings",
                "  ISSUES: Any NOT_MET criteria OR any RULE 0/1 findings",
                "",
                "Return 'PASS' or 'ISSUES' to the orchestrator.",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from shared import mode_main
    mode_main(__file__, get_step_guidance, "QR-Batch-Review: Wave milestone verification workflow")
