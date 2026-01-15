#!/usr/bin/env python3
"""
Dev-Fill-Diffs - Step-based workflow for developer sub-agent.

Converts Code Intent sections to Code Changes (unified diffs) BEFORE TW review:
- Read target files from codebase
- Convert Code Intent prose to unified diffs
- Add context lines for reliable anchoring
- Edit plan file in-place

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.conventions import get_convention


def get_step_guidance(
    step: int, total_steps: int, module_path: str, **kwargs
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

    # Step 1: Task description (or FIX mode)
    if step == 1:
        if qr_fail:
            # FIX MODE - address QR issues only
            banner = render(W.el("state_banner", checkpoint="DEV-FILL-DIFFS", iteration=str(qr_iteration), mode="fix").build(), XMLRenderer())
            return {
                "title": "Fix QR Issues",
                "actions": [banner, ""] + [
                    "FIX MODE: QR-CODE found issues in your diffs.",
                    "",
                    "Find QR_REPORT_PATH in the <context> section of your dispatch.",
                    "Read that file to see the issues. The orchestrator has NOT read it.",
                    "",
                    "Address ONLY the identified issues:",
                    "  - Context line mismatches",
                    "  - Missing/incorrect file paths",
                    "  - RULE 0/1/2 violations",
                    "  - Diff format errors",
                    "",
                    "Do NOT redo work that passed.",
                    "Edit the plan file to fix the specific issues.",
                    "",
                    "After fixing, return 'COMPLETE' to orchestrator.",
                ],
                "next": None,  # No continuation - single step fix
            }

        # Normal initial work
        banner = render(W.el("state_banner", checkpoint="DEV-FILL-DIFFS", iteration="1", mode="work").build(), XMLRenderer())
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
            "next": f"python3 -m {module_path} --step 2 --total-steps {total_steps}",
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
            "next": f"python3 -m {module_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: Diff format reference (inject resource)
    if step == 3:
        diff_resource = get_convention("diff-format.md")
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
            "next": f"python3 -m {module_path} --step 4 --total-steps {total_steps}",
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
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "Dev-Fill-Diffs: Code Intent to Code Changes workflow")
