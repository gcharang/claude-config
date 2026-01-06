#!/usr/bin/env python3
"""
TW-Plan-Scrub - Step-based workflow for technical-writer sub-agent.

Reviews and fixes implementation plan BEFORE Developer execution:
- Extract Planning Context (Decision Log, constraints, risks)
- Temporal contamination review (all 5 detection categories)
- Code presence validation
- WHY comment injection from Decision Log
- Priority-based scrubbing (HIGH/MEDIUM/LOW)
- Documentation tier verification (Tiers 3-6)

Usage:
    python3 tw/plan-scrub.py --step 1 --total-steps 6 [--qr-iteration 1] [--qr-fail]

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared import (
    get_resource,
    format_step_output,
    format_state_banner,
    format_resource,
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

    # Step 1: Task description
    if step == 1:
        if qr_iteration == 1 and not qr_fail:
            banner = format_state_banner("TW-PLAN-SCRUB", qr_iteration, "initial_review")
        else:
            banner = format_state_banner(
                "TW-PLAN-SCRUB", qr_iteration, "re_verification",
                [
                    "You previously fixed issues identified by QR.",
                    "This invocation verifies those fixes were applied correctly.",
                    "",
                    "CRITICAL: QR MUST return PASS before you can proceed.",
                ]
            )
        return {
            "title": "Task Description",
            "actions": [banner, ""]
            + [
                "TYPE: PLAN_SCRUB",
                "",
                "TASK: Review and fix implementation plan for production readiness.",
                "",
                "You are scrubbing the plan AFTER Developer filled diffs.",
                "Plan has Code Changes sections with unified diffs.",
                "Your job: add WHY comments, fix temporal contamination, verify docs.",
                "",
                "RULE 0 (ABSOLUTE): Edit the plan file IN-PLACE.",
                "  - Use Edit tool on the original plan file",
                "  - NEVER create new files (plan-scrubbed.md, plan-tw.md)",
                "  - NEVER 'preserve the original'",
                "",
                "EFFICIENCY: Batch multiple edits in a single call.",
                "  - Read entire file first to identify ALL changes",
                "  - Group nearby changes together",
                "  - Prefer fewer, larger edits over many small edits",
                "",
                "Read the plan file now. Identify:",
                "  - ## Planning Context section",
                "  - ## Milestones with Code Changes",
                "  - ## Invisible Knowledge section (if present)",
            ],
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Planning Context extraction
    if step == 2:
        return {
            "title": "Extract Planning Context",
            "actions": [
                "EXTRACT from ## Planning Context section:",
                "",
                "1. DECISION LOG entries:",
                "   - WHY each architectural choice was made",
                "   - What alternatives were rejected and why",
                "   - Specific values and their sensitivity analysis",
                "",
                "2. CONSTRAINTS that shaped the design:",
                "   - Technical limitations",
                "   - Compatibility requirements",
                "   - Performance targets",
                "",
                "3. KNOWN RISKS and mitigations:",
                "   - What could go wrong",
                "   - How the design addresses each risk",
                "",
                "Write out your CONTEXT SUMMARY before proceeding:",
                "  CONTEXT SUMMARY:",
                "  - Key decisions: [list from Decision Log]",
                "  - Rejected alternatives: [list with reasons]",
                "  - Constraints: [list]",
                "  - Risks addressed: [list]",
                "",
                "This context is your SOURCE for WHY comments.",
                "Comments you add MUST trace back to this context.",
            ],
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Temporal contamination review (inject resource)
    if step == 3:
        temporal_resource = get_resource("temporal-contamination.md")
        return {
            "title": "Temporal Contamination Review",
            "actions": [
                "AUTHORITATIVE REFERENCE FOR TEMPORAL CONTAMINATION:",
                "",
                "=" * 60,
                temporal_resource,
                "=" * 60,
                "",
                "SCAN all existing comments in Code Changes sections.",
                "",
                "For EACH comment, evaluate against 5 detection questions:",
                "  1. Does it describe action taken? (change-relative)",
                "  2. Does it compare to something not in code? (baseline reference)",
                "  3. Does it describe where to put code? (location directive)",
                "  4. Does it describe intent not behavior? (planning artifact)",
                "  5. Does it describe author's choice? (intent leakage)",
                "",
                "ACTIONS:",
                "  - Location directives: DELETE (diff encodes location)",
                "  - Change-relative: TRANSFORM to timeless present",
                "  - Baseline reference: TRANSFORM to timeless present",
                "  - Planning artifact: DELETE or REFRAME as current constraint",
                "  - Intent leakage: EXTRACT technical justification",
                "",
                "CODE PRESENCE CHECK:",
                "  For each implementation milestone (modifies source files):",
                "  - Does it have Code Changes with unified diffs?",
                "  - If NO: Stop and report escalation (see step 6)",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Prioritization and coverage
    if step == 4:
        return {
            "title": "Prioritization and Documentation Tiers",
            "actions": [
                "PRIORITIZE by uncertainty (scrub HIGH before MEDIUM, skip LOW):",
                "",
                "| Priority | Code Pattern                 | WHY Question           |",
                "| -------- | ---------------------------- | ---------------------- |",
                "| HIGH     | Multiple valid approaches    | Why this approach?     |",
                "| HIGH     | Thresholds, timeouts, limits | Why these values?      |",
                "| HIGH     | Error handling paths         | Recovery strategy?     |",
                "| HIGH     | External system interactions | What assumptions?      |",
                "| MEDIUM   | Non-standard pattern usage   | Why deviate from norm? |",
                "| MEDIUM   | Performance-critical paths   | Why this optimization? |",
                "| LOW      | Boilerplate/established      | Skip unless unusual    |",
                "| LOW      | Simple CRUD operations       | Skip unless unusual    |",
                "",
                "CHECK MILESTONE FLAGS (if present):",
                "  - `needs-rationale`: Every non-obvious element needs WHY comment",
                "  - `complex-algorithm`: Add Tier 5 algorithm block even if simple",
                "",
                "DOCUMENTATION TIERS (verify in Code Changes):",
                "",
                "| Tier | Location           | Purpose                         |",
                "| ---- | ------------------ | ------------------------------- |",
                "| 3    | Top of new files   | Module-level: what + why exists |",
                "| 4    | Above functions    | Docstrings: ALL functions       |",
                "| 5    | Complex algorithms | Strategy, invariants, edge cases|",
                "| 6    | Within code lines  | Specific WHY (never WHAT)       |",
                "",
                "CRITICAL: Document ALL functions (public AND private).",
                "Helper docstrings: [what it does] + [when to call it]",
            ],
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Comment injection
    if step == 5:
        return {
            "title": "Comment Injection",
            "actions": [
                "INJECT WHY comments for HIGH priority code:",
                "",
                "For each non-obvious code element:",
                "  1. Find Decision Log entry that explains this choice",
                "  2. Write comment that answers WHY (not WHAT)",
                "  3. Verify ACTIONABILITY TEST:",
                "     - Does it name a specific decision or constraint?",
                "     - Does it reference concrete evidence?",
                "",
                "TRANSFORM Decision Log -> Code Comment:",
                "  Decision Log: 'Polling | 30% webhook failure -> need fallback'",
                "  Code Comment: // Polling: 30% webhook delivery failures observed",
                "",
                "PLANNING CONTEXT GAP PROTOCOL:",
                "  If code needs WHY but Decision Log lacks rationale:",
                "  1. Do NOT block the scrub -- proceed without comment",
                "  2. Record gap for final output (see step 6)",
                "  3. Continue with remaining work",
                "",
                "ENRICH PLAN PROSE (for HIGH/MEDIUM sections):",
                "  - Integrate decision context naturally into prose",
                "  - Add 'why not X' where rejected alternatives provide insight",
                "  - Surface constraints explaining non-obvious choices",
                "",
                "ADD DOCUMENTATION MILESTONES if missing:",
                "  - CLAUDE.md creation/update",
                "  - README.md if Invisible Knowledge has content",
            ],
            "next": f"python3 {script_path} --step 6 --total-steps {total_steps}",
        }

    # Step 6: Output format (final step)
    if step >= total_steps:
        return {
            "title": "Scrub Coverage and Output",
            "actions": [
                "VERIFY SCRUB COVERAGE (all must pass):",
                "",
                "Tiers 3-4 (structure):",
                "  [ ] Every new file has module-level comment",
                "  [ ] ALL functions have docstrings (public AND private)",
                "  [ ] Helper docstrings: [what it does] + [when to call it]",
                "  [ ] No docstring restates function name",
                "",
                "Tiers 5-6 (understanding):",
                "  [ ] Every algorithm block has explanatory comment",
                "  [ ] Every non-obvious line has WHY comment",
                "  [ ] No comment states WHAT the code does",
                "",
                "Temporal contamination:",
                "  [ ] No change-relative (Added, Replaced, Changed, Now uses)",
                "  [ ] No baseline references (Previously, Instead of, Replaces)",
                "  [ ] No location directives (After X, Before Y, Insert)",
                "  [ ] No planning artifacts (TODO, Will, Planned, Temporary)",
                "",
                "CLAUDE.md format:",
                "  [ ] Tabular index with WHAT/WHEN columns",
                "  [ ] NO explanatory prose",
                "  [ ] Overview is ONE sentence only",
                "",
                "---",
                "",
                "OUTPUT FORMAT:",
                "",
                "If scrub complete with no gaps:",
                "  'COMPLETE: Plan scrubbed. Ready for QR-Docs.'",
                "",
                "If scrub complete with Planning Context gaps:",
                "  'COMPLETE: Plan scrubbed with gaps.'",
                "  <planning_context_gap>",
                "    <milestone>[N]</milestone>",
                "    <code_element>[function, threshold, etc.]</code_element>",
                "    <gap_type>[missing_decision|insufficient_reasoning]</gap_type>",
                "    <needed>[what Decision Log entry would enable comment]</needed>",
                "  </planning_context_gap>",
                "",
                "If code missing (BLOCKING):",
                "  <escalation>",
                "    <type>BLOCKED</type>",
                "    <context>Milestone N is implementation but contains no code</context>",
                "    <issue>NO_CODE_TO_SCRUB</issue>",
                "    <needed>Return to planner to add code changes</needed>",
                "  </escalation>",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from shared import mode_main
    mode_main(__file__, get_step_guidance, "TW-Plan-Scrub: Plan documentation scrub workflow")
