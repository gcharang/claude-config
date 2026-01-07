#!/usr/bin/env python3
"""
QR-Plan-Completeness - Step-based workflow for quality-reviewer sub-agent.

Validates plan document completeness before TW/Developer work:
- Decision Log completeness (all code elements documented)
- Policy default verification (user-specified backing required)
- Architectural assumption validation
- Plan structure (milestones, acceptance criteria, code presence)

Usage:
    python3 qr/plan-completeness.py --step 1 --total-steps 6 [--qr-iteration 1] [--qr-fail]

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared import (
    QRState,
    get_resource,
    format_step_output,
    format_qr_banner,
    format_resource,
    format_verification_checklist,
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
    qr = QRState(iteration=qr_iteration, failed=qr_fail)

    # Step 1: Task description
    if step == 1:
        banner = format_qr_banner("QR-COMPLETENESS", qr)
        return {
            "title": "Plan Completeness Review",
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
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Resource injection (default conventions)
    if step == 2:
        defaults_resource = get_resource("default-conventions.md")
        resource_block = format_resource(
            "default-conventions",
            "policy-default-verification",
            defaults_resource
        )
        return {
            "title": "Reference: Default Conventions",
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
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Decision Log and Policy Default verification
    if step == 3:
        return {
            "title": "Verify Decision Log and Policy Defaults",
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
                "  If not found: Record as SHOULD_FIX",
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
                "  If answer is 'none': Record as SHOULD_FIX",
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
                "  If no user-specified citation: Record as SHOULD_FIX",
                "    'Unvalidated architectural assumption: [description]'",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Plan structure verification
    if step == 4:
        structure_checklist = format_verification_checklist(
            "plan-structure",
            [
                {"element": "Milestones", "criterion": "Each has acceptance criteria", "if_missing": "M[N] lacks criteria"},
                {"element": "Invisible Knowledge", "criterion": "Populated if README.md expected", "if_missing": "Missing Invisible K"},
                {"element": "Planning Context", "criterion": "Decision Log, Constraints, Risks", "if_missing": "Incomplete Context"},
                {"element": "Documentation MS", "criterion": "Plan includes doc deliverables", "if_missing": "Add doc milestone"},
            ]
        )
        code_presence_checklist = format_verification_checklist(
            "code-presence",
            [
                {"element": "Code Intent with file paths", "criterion": "Section present with changes", "if_missing": "PASS"},
                {"element": "Documentation-only + all .md", "criterion": "Skip reason valid", "if_missing": "PASS"},
                {"element": "No Code Intent + source files", "criterion": "Must have Code Intent", "if_missing": "SHOULD_FIX: Missing intent"},
                {"element": "Skip reason + source files", "criterion": "Skip invalid for source", "if_missing": "SHOULD_FIX: Invalid skip"},
            ]
        )
        test_spec_checklist = format_verification_checklist(
            "test-specification",
            [
                {"element": "Test file paths + type + scenarios", "criterion": "Fully specified", "if_missing": "PASS"},
                {"element": "No tests with rationale", "criterion": "Explicit skip OK", "if_missing": "PASS"},
                {"element": "Documentation-only milestone", "criterion": "No tests needed", "if_missing": "PASS"},
                {"element": "Empty Tests section", "criterion": "Must specify or skip", "if_missing": "SHOULD_FIX: Empty spec"},
                {"element": "Implementation MS no Tests", "criterion": "Must have Tests section", "if_missing": "SHOULD_FIX: Missing"},
            ]
        )
        return {
            "title": "Verify Plan Structure",
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
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Exhaustiveness verification (fresh second-pass)
    if step == 5:
        return {
            "title": "Exhaustiveness Verification",
            "actions": [
                "<exhaustiveness_check>",
                "STOP. Before finalizing findings, perform fresh examination.",
                "",
                "This is a SEPARATE verification pass. Do NOT simply review your prior",
                "findings -- re-examine the plan with fresh eyes.",
                "",
                "ADVERSARIAL QUESTIONS (answer each with specific findings or 'none'):",
                "",
                "1. What CATEGORIES of issues have you not yet examined?",
                "   (e.g., error handling, edge cases, integration points)",
                "",
                "2. For each milestone, what could go WRONG that is not addressed?",
                "   List concrete failure scenarios.",
                "",
                "3. What ASSUMPTIONS is the plan making that are not documented?",
                "   (e.g., about infrastructure, dependencies, user behavior)",
                "",
                "4. What would a HOSTILE reviewer find that you missed?",
                "   Imagine someone whose job is to find problems you overlooked.",
                "",
                "5. What QUESTIONS would need to be answered before implementation",
                "   that the plan does not address?",
                "",
                "Record any NEW issues discovered. These are ADDITIONAL findings,",
                "not duplicates of prior checks.",
                "</exhaustiveness_check>",
            ],
            "next": f"python3 {script_path} --step 6 --total-steps {total_steps}",
        }

    # Step 6: Output format (final step)
    if step >= total_steps:
        expected_output = format_expected_output(
            if_pass="PASS: Plan completeness verified. Ready for Developer diffs.",
            if_issues="""\
ISSUES:
  1. [CATEGORY] Description
  2. [CATEGORY] Description
  ...""",
            categories=[
                "DECISION_LOG: Missing or insufficient Decision Log entry",
                "POLICY: Policy default lacks user-specified backing",
                "ASSUMPTION: Unvalidated architectural assumption",
                "STRUCTURE: Missing required plan element",
                "CODE_INTENT: Missing Code Intent for implementation milestone",
                "TEST_SPEC: Missing or empty test specification",
            ]
        )
        return {
            "title": "Format Output",
            "actions": [
                expected_output,
                "",
                "All issues are SHOULD_FIX severity (planning phase, not production).",
                "",
                "Return PASS or ISSUES to the orchestrator.",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from shared import mode_main
    mode_main(__file__, get_step_guidance, "QR-Plan-Completeness: Plan completeness validation workflow")
