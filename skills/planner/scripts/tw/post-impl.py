#!/usr/bin/env python3
"""
TW-Post-Impl - Step-based workflow for technical-writer sub-agent.

Creates documentation AFTER implementation is complete:
- Extract Invisible Knowledge and modified file list from plan
- Update/create CLAUDE.md with tabular index format
- Create README.md if Invisible Knowledge has content
- Spot-check transcribed comments

Usage:
    python3 tw/post-impl.py --step 1 --total-steps 6

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys
from pathlib import Path

# Add parent of skills/ to path for skills.lib.workflow imports
claude_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(claude_dir) not in sys.path:
    sys.path.insert(0, str(claude_dir))

# Add planner/scripts to path for shared.resources access
planner_scripts_dir = Path(__file__).resolve().parent.parent
if str(planner_scripts_dir) not in sys.path:
    sys.path.insert(0, str(planner_scripts_dir))

from skills.lib.workflow.formatters import (
    format_step_output,
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
        **kwargs: Additional context (unused for post-impl)
    """
    # Step 1: Task description
    if step == 1:
        return {
            "title": "Task Description",
            "actions": [
                "TYPE: POST_IMPL",
                "",
                "TASK: Create documentation AFTER implementation is complete.",
                "",
                "You document what EXISTS. Implementation is done and stable.",
                "Code provided is correct and functional.",
                "",
                "PREREQUISITES:",
                "  - Plan file path (contains Invisible Knowledge, milestone descriptions)",
                "  - Implementation complete (all milestones executed)",
                "  - Quality review passed",
                "",
                "DELIVERABLES:",
                "  1. CLAUDE.md index entries for modified directories",
                "  2. README.md if Invisible Knowledge has content",
                "  3. Verification that TW-prepared comments were transcribed",
                "",
                "Read the plan file now to understand what was implemented.",
            ],
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: Plan extraction
    if step == 2:
        return {
            "title": "Extract Plan Information",
            "actions": [
                "EXTRACT from plan file:",
                "",
                "1. INVISIBLE KNOWLEDGE section (if present):",
                "   - Architecture decisions not visible from code",
                "   - Tradeoffs made and why",
                "   - Invariants that must be maintained",
                "   - Assumptions underlying the design",
                "",
                "2. MODIFIED FILE LIST:",
                "   - From each milestone's ## Files section",
                "   - Group by directory for CLAUDE.md updates",
                "",
                "3. MILESTONE DESCRIPTIONS:",
                "   - What each milestone accomplished",
                "   - Use for WHAT column in CLAUDE.md index",
                "",
                "Write out your extraction before proceeding:",
                "  EXTRACTION:",
                "  - Invisible Knowledge: [summary or 'none']",
                "  - Modified directories: [list]",
                "  - Key changes: [per milestone]",
            ],
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: CLAUDE.md guidance
    if step == 3:
        return {
            "title": "CLAUDE.md Index Format",
            "actions": [
                "UPDATE CLAUDE.md for each modified directory.",
                "",
                "FORMAT (tabular index):",
                "```markdown",
                "# CLAUDE.md",
                "",
                "## Overview",
                "",
                "[One sentence: what this directory contains]",
                "",
                "## Index",
                "",
                "| File         | Contents (WHAT)              | Read When (WHEN)                        |",
                "| ------------ | ---------------------------- | --------------------------------------- |",
                "| `handler.py` | Request handling, validation | Debugging request flow, adding endpoint |",
                "| `types.py`   | Data models, schemas         | Modifying data structures               |",
                "| `README.md`  | Architecture decisions       | Understanding system design             |",
                "```",
                "",
                "INDEX RULES:",
                "  - WHAT: Nouns and actions (handlers, validators, models)",
                "  - WHEN: Task-based triggers using action verbs",
                "  - Every file in directory should have an entry",
                "  - Exclude generated files (build artifacts, caches)",
                "",
                "IF CLAUDE.md exists but NOT tabular:",
                "  REWRITE completely (do not improve, replace)",
                "",
                "FORBIDDEN in CLAUDE.md:",
                "  - Explanatory prose (-> README.md)",
                "  - 'Key Invariants', 'Dependencies', 'Constraints' sections",
                "  - Overview longer than ONE sentence",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: README.md guidance
    if step == 4:
        return {
            "title": "README.md Creation Criteria",
            "actions": [
                "CREATE README.md ONLY if Invisible Knowledge has content.",
                "",
                "CREATION CRITERIA (create if ANY apply):",
                "  - Planning decisions from Decision Log",
                "  - Business context (why the product works this way)",
                "  - Architectural rationale (why this structure)",
                "  - Trade-offs made (what sacrificed for what)",
                "  - Invariants (rules not enforced by types)",
                "  - Historical context (why not alternatives)",
                "  - Performance characteristics (non-obvious)",
                "  - Non-obvious relationships between files",
                "",
                "DO NOT create README.md if:",
                "  - Directory is purely organizational",
                "  - All knowledge visible from reading source code",
                "  - You would only restate what code already shows",
                "",
                "SELF-CONTAINED PRINCIPLE:",
                "  README.md must be self-contained.",
                "  Do NOT reference external sources (wikis, doc/ directories).",
                "  Summarize external knowledge in README.md.",
                "  Duplication is acceptable for locality.",
                "",
                "CONTENT TEST for each sentence:",
                "  'Could a developer learn this by reading source files?'",
                "  If YES -> delete the sentence",
                "  If NO -> keep it",
                "",
                "README.md STRUCTURE:",
                "  # [Component Name]",
                "  ## Overview",
                "  [One paragraph: problem solved, high-level approach]",
                "  ## Architecture (if applicable)",
                "  ## Design Decisions",
                "  ## Invariants (if applicable)",
            ],
            "next": f"python3 {script_path} --step 5 --total-steps {total_steps}",
        }

    # Step 5: Comment verification
    if step == 5:
        return {
            "title": "Verify Transcribed Comments",
            "actions": [
                "SPOT-CHECK that Developer transcribed TW-prepared comments.",
                "",
                "Pick 2-3 modified files and verify:",
                "  1. Comments from plan's Code Changes appear in actual files",
                "  2. Comments are verbatim (not paraphrased)",
                "  3. Comments are in correct locations",
                "",
                "COMMON TRANSCRIPTION ISSUES:",
                "  - Comment missing entirely",
                "  - Comment paraphrased (lost precision)",
                "  - Comment in wrong location",
                "  - Temporal contamination introduced (check 5 categories)",
                "",
                "If issues found:",
                "  - Fix the comment in the actual source file",
                "  - Use Edit tool on the source file (not plan file)",
                "",
                "This is verification, not comprehensive review.",
                "QR already validated; spot-check for transcription accuracy.",
            ],
            "next": f"python3 {script_path} --step 6 --total-steps {total_steps}",
        }

    # Step 6: Output format (final step)
    if step >= total_steps:
        return {
            "title": "Output Format",
            "actions": [
                "OUTPUT FORMAT:",
                "",
                "```",
                "Documented: [directory/] or [file:symbol]",
                "Type: POST_IMPL",
                "Tokens: [count]",
                "Index: [UPDATED | CREATED | VERIFIED]",
                "README: [CREATED | SKIPPED: reason]",
                "```",
                "",
                "Examples:",
                "",
                "```",
                "Documented: src/auth/",
                "Type: POST_IMPL",
                "Tokens: 180",
                "Index: UPDATED",
                "README: CREATED",
                "```",
                "",
                "```",
                "Documented: src/utils/",
                "Type: POST_IMPL",
                "Tokens: 95",
                "Index: CREATED",
                "README: SKIPPED: no invisible knowledge",
                "```",
                "",
                "If implementation unclear, add:",
                "  Missing: [what is needed]",
                "",
                "DO NOT include text before or after the format block.",
            ],
            "next": "Return result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "TW-Post-Impl: Post-implementation documentation workflow")
