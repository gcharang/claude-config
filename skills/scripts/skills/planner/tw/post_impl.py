#!/usr/bin/env python3
"""
TW-Post-Impl - Step-based workflow for technical-writer sub-agent.

Creates documentation AFTER implementation is complete:
- Extract Invisible Knowledge and modified file list from plan
- Update/create CLAUDE.md with tabular index format
- Create README.md if Invisible Knowledge has content
- Spot-check transcribed comments

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.workflow.types import ResourceProvider


STEPS = {
    1: {
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
    },
    2: {
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
    },
    3: {
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
    },
    4: {
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
    },
    5: {
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
    },
    6: {
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
    },
}


def step_handler(step_info: dict, step: int, total_steps: int, module_path: str, **kwargs) -> dict:
    """Generic handler for all steps."""
    result = {
        "title": step_info["title"],
        "actions": step_info["actions"],
    }
    if step >= total_steps:
        result["next"] = "Return result to orchestrator. Sub-agent task complete."
    else:
        result["next"] = f"python3 -m {module_path} --step {step + 1} --total-steps {total_steps}"
    return result


STEP_HANDLERS = {i: step_handler for i in range(1, 7)}


def get_step_guidance(
    step: int, total_steps: int, module_path: str, provider: ResourceProvider = None, **kwargs
) -> dict:
    """Return guidance for the given step.

    Args:
        step: Current step number (1-indexed)
        total_steps: Total number of steps in this workflow
        module_path: Module path for -m invocation
        **kwargs: Additional context (unused for post-impl)
    """
    step_info = STEPS.get(step if step < total_steps else 6)
    if not step_info:
        return {"title": "Unknown", "actions": ["Check step number"], "next": ""}

    handler = STEP_HANDLERS.get(step if step < total_steps else 6, step_handler)
    return handler(step_info=step_info, step=step, total_steps=total_steps, module_path=module_path, **kwargs)


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "TW-Post-Impl: Post-implementation documentation workflow")
