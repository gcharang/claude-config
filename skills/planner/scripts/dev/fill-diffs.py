#!/usr/bin/env python3
"""
Dev-Fill-Diffs - Step-based workflow for developer sub-agent.

Converts Code Intent sections to Code Changes (unified diffs) BEFORE TW review:
- Read target files from codebase
- Convert Code Intent prose to unified diffs
- Add context lines for reliable anchoring
- Edit plan file in-place

Usage:
    python3 dev/fill-diffs.py --step 1 --total-steps 4 [--qr-iteration 1] [--qr-fail]

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
            banner = format_state_banner("DEV-FILL-DIFFS", qr_iteration, "initial_review")
        else:
            banner = format_state_banner(
                "DEV-FILL-DIFFS", qr_iteration, "re_verification",
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
                "TASK: Convert Code Intent to Code Changes (unified diffs).",
                "",
                "You are filling diffs AFTER planning, BEFORE TW review.",
                "Plan has Code Intent sections describing WHAT to implement.",
                "Your job: read codebase, create unified diffs, edit plan in-place.",
                "",
                "RULE 0 (ABSOLUTE): Edit the plan file IN-PLACE.",
                "  - Use Edit tool on the original plan file",
                "  - NEVER create new files",
                "  - NEVER 'preserve the original'",
                "",
                "SCOPE: ONLY produce diffs. Do not modify other plan sections.",
                "  - Do NOT change Decision Log",
                "  - Do NOT modify Invisible Knowledge",
                "  - Do NOT add/remove milestones",
                "",
                "Read the plan file now. For each milestone, identify:",
                "  - Code Intent section (describes WHAT to implement)",
                "  - Target files to modify/create",
            ],
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Read codebase and understand targets
    if step == 2:
        return {
            "title": "Read Target Files",
            "actions": [
                "For EACH implementation milestone:",
                "",
                "1. READ TARGET FILES from codebase:",
                "   - Files that will be modified",
                "   - Files that will be created (check if directory exists)",
                "   - Adjacent files for pattern reference",
                "",
                "2. UNDERSTAND CONTEXT:",
                "   - Existing patterns and conventions",
                "   - Where new code should be inserted",
                "   - What context lines to use for anchoring",
                "",
                "3. NOTE for each file:",
                "   - Current structure",
                "   - Insertion points for new code",
                "   - Context lines (2-3 lines before/after changes)",
                "",
                "SKIP PATTERN: If milestone only touches .md/.rst/.txt files,",
                "mark as 'Skip reason: documentation-only' instead of producing diffs.",
            ],
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Diff format reference (inject resource)
    if step == 3:
        diff_resource = get_resource("diff-format.md")
        return {
            "title": "Create Unified Diffs",
            "actions": [
                "AUTHORITATIVE REFERENCE FOR DIFF FORMAT:",
                "",
                "=" * 60,
                diff_resource,
                "=" * 60,
                "",
                "For EACH Code Intent section, create Code Changes section:",
                "",
                "STRUCTURE:",
                "  ### Code Changes",
                "  ",
                "  ```diff",
                "  --- a/path/to/file.py",
                "  +++ b/path/to/file.py",
                "  @@ -123,6 +123,15 @@ def existing_function(ctx):",
                "     context_line_before()",
                "  ",
                "  +   # WHY comment from Decision Log",
                "  +   new_code()",
                "  ",
                "     context_line_after()",
                "  ```",
                "",
                "REQUIREMENTS:",
                "  - File path: exact path to target file",
                "  - Context lines: 2-3 unchanged lines for anchoring",
                "  - Function context: include in @@ line if applicable",
                "  - Comments: explain WHY, source from Planning Context",
                "",
                "COMMENT GUIDELINES (TW will review for contamination):",
                "  - Explain WHY this code exists, not WHAT it does",
                "  - Reference Decision Log for rationale",
                "  - No location directives (diff encodes location)",
                "  - Concrete terms, no hidden baselines",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Output format (final step)
    if step >= total_steps:
        return {
            "title": "Edit Plan and Output",
            "actions": [
                "EDIT THE PLAN FILE IN-PLACE:",
                "",
                "For each milestone with Code Intent:",
                "  1. Add '### Code Changes' section after Code Intent",
                "  2. Include unified diff blocks for all file changes",
                "  3. Keep Code Intent section (for reference)",
                "",
                "VALIDATION CHECKLIST (verify before completing):",
                "",
                "  [ ] Each implementation milestone has Code Changes section",
                "  [ ] File paths are exact (not 'auth files' but 'src/auth/handler.py')",
                "  [ ] Context lines exist in target files (verify patterns match)",
                "  [ ] 2-3 context lines for reliable anchoring",
                "  [ ] Comments explain WHY, not WHAT",
                "  [ ] No location directives in comments",
                "  [ ] Documentation-only milestones have skip reason",
                "",
                "---",
                "",
                "OUTPUT FORMAT:",
                "",
                "If all diffs added successfully:",
                "  'COMPLETE: Code Changes added to all implementation milestones.'",
                "",
                "If issues found:",
                "  <escalation>",
                "    <type>BLOCKED</type>",
                "    <context>[Milestone N]</context>",
                "    <issue>[What prevented diff creation]</issue>",
                "    <needed>[What's needed to proceed]</needed>",
                "  </escalation>",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from shared import mode_main
    mode_main(__file__, get_step_guidance, "Dev-Fill-Diffs: Code Intent to Code Changes workflow")
