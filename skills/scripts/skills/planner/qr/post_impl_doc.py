#!/usr/bin/env python3
"""
QR-Post-Impl-Doc - Step-based workflow for quality-reviewer sub-agent.

Documentation quality review AFTER technical writer pass:
- CLAUDE.md format verification (tabular index)
- README.md content verification (invisible knowledge)
- Comment hygiene (temporal contamination)
- Proximity audit (docs adjacent to code)

Sub-agents invoke this script immediately upon receiving their prompt.
The script provides step-by-step guidance; the agent follows exactly.
"""

import sys

from skills.lib.workflow.types import QRState, LoopState, ResourceProvider
from skills.lib.workflow.ast import W, render, XMLRenderer
from skills.lib.conventions import get_convention


STEPS = {
    1: {
        "title": "Documentation Quality Review",
    },
    2: {
        "title": "CLAUDE.md Format Verification",
    },
    3: {
        "title": "README.md and Comment Verification",
    },
    4: {
        "title": "Write Report and Return Result",
    },
}


def step_1_handler(step_info, total_steps, module_path, qr, **kwargs):
    banner = render(
        W.el("state_banner",
             checkpoint="DOC QR",
             iteration=str(qr.iteration),
             mode="fresh_review").build(),
        XMLRenderer()
    )
    return {
        "title": step_info["title"],
        "actions": [banner, ""]
        + [
            "TASK: Verify documentation quality after TW pass.",
            "",
            "You are reviewing DOCUMENTATION, not code logic.",
            "Technical writer has created/updated docs. Verify quality.",
            "",
            "SCOPE:",
            "  - CLAUDE.md format (tabular index)",
            "  - README.md content (invisible knowledge captured)",
            "  - Comment hygiene (no temporal contamination)",
            "  - Proximity audit (docs adjacent to code)",
            "",
            "INPUTS (from your prompt):",
            "  - PLAN: Path to the executed plan file",
            "  - MODIFIED_FILES: Files changed during implementation",
            "",
            "FIRST: Read the plan file now. Locate:",
            "  - ## Invisible Knowledge (for proximity audit)",
            "",
            "Note the IK items you need to verify.",
        ],
        "next": f"python3 -m {module_path} --step 2 --total-steps {total_steps}",
    }


def step_2_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
        "actions": [
            "For each CLAUDE.md in modified directories:",
            "",
            "| Check              | PASS                             | FAIL              |",
            "| ------------------ | -------------------------------- | ----------------- |",
            "| Format             | Tabular index (WHAT/WHEN cols)   | Prose, bullets    |",
            "| Size               | As small as possible             | Large             |",
            "| Overview           | One sentence max                 | Multiple          |",
            "| Forbidden sections | None present                     | Present           |",
            "| Operational        | Commands only (Build,Test,etc)   | Explanatory prose |",
            "",
            "FORBIDDEN SECTIONS:",
            "  'Key Invariants', 'Dependencies', 'Constraints'",
            "  (These belong in README.md, not CLAUDE.md)",
            "",
            "Stub directory exception: Directories with only .gitkeep",
            "do NOT require CLAUDE.md. Do not flag.",
            "",
            "Document findings:",
            "  | Directory | Format | Forbidden | Verdict |",
            "  | --------- | ------ | --------- | ------- |",
        ],
        "next": f"python3 -m {module_path} --step 3 --total-steps {total_steps}",
    }


def step_3_handler(step_info, total_steps, module_path, qr, **kwargs):
    temporal_resource = get_convention("temporal.md")
    return {
        "title": step_info["title"],
        "actions": [
            "INVISIBLE KNOWLEDGE PROXIMITY AUDIT",
            "",
            "For EACH knowledge item from plan, ask OPEN question:",
            "  'Where CLOSE TO THE CODE is [item] documented?'",
            "",
            "ACCEPTABLE (code-adjacent):",
            "  - README.md in SAME DIRECTORY as affected code",
            "  - Module-level docstrings (top of file)",
            "  - Inline code comments explaining WHY",
            "",
            "NOT ACCEPTABLE (violates proximity):",
            "  - README.md in separate doc/ directory",
            "  - External wikis or documentation systems",
            "  - References to external sources without local summary",
            "",
            "IK PROXIMITY RULE: 'as close as possible to where relevant, but not more'",
            "",
            "KNOWLEDGE TYPE MAPPING:",
            "  | Type          | Best Location                           |",
            "  | ------------- | --------------------------------------- |",
            "  | Accepted risk | :TODO: comment at flagged code location |",
            "  | Architecture  | README.md in SAME directory             |",
            "  | Data flow     | README.md or module docstring           |",
            "  | Tradeoffs     | Code comment where decision shows       |",
            "  | Invariants    | Code comment at enforcement point       |",
            "",
            "Wrong location = IK_TRANSFER_FAILURE (MUST)",
            "  Examples:",
            "  - Architecture in separate doc/ directory -> FAIL (too far)",
            "  - Tradeoff in README instead of at decision point -> FAIL (not proximate)",
            "  - Accepted risk in Decision Log without code marker -> FAIL (no proximity)",
            "",
            "---",
            "",
            "COMMENT HYGIENE (temporal contamination check):",
            "",
            temporal_resource,
            "",
            "Check modified files for contaminated comments:",
            "  TEMPORAL_CONTAMINATION: Change-relative language (MUST)",
            "  BASELINE_REFERENCE: References removed code (MUST)",
            "  LLM_COMPREHENSION_RISK: Confusing to future reader (MUST)",
            "",
            "Intent markers: Check for :PERF: and :UNSAFE: markers.",
            "  Valid format: ':MARKER: [what]; [why]' (semicolon + non-empty why)",
            "  Invalid format: Report as MARKER_INVALID (MUST)",
        ],
        "next": f"python3 -m {module_path} --step 4 --total-steps {total_steps}",
    }


def step_4_handler(step_info, total_steps, module_path, qr, **kwargs):
    return {
        "title": step_info["title"],
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
            "```",
            "## DOC QR RESULT: PASS | ISSUES",
            "",
            "### CLAUDE.md Status",
            "| Directory | Format | Forbidden | Verdict |",
            "| --------- | ------ | --------- | ------- |",
            "",
            "### Invisible Knowledge Proximity",
            "| Knowledge Item | Documented In | Proximity | Status |",
            "| -------------- | ------------- | --------- | ------ |",
            "",
            "### Comment Hygiene",
            "[List any temporal contamination findings, or 'Clean']",
            "",
            "### Findings (if ISSUES)",
            "- [CATEGORY SEVERITY] **Location**: description",
            "  Examples:",
            "  - [IK_TRANSFER_FAILURE MUST] Architecture in doc/ (should be README.md)",
            "  - [TEMPORAL_CONTAMINATION MUST] 'Added retry' comment (file:line)",
            "  - [CONVENTION_VIOLATION SHOULD] CLAUDE.md has prose sections",
            "```",
            "",
            "VERDICT GUIDE:",
            "  PASS: All docs correct format, IK at BEST location, no contamination",
            "  ISSUES: Any MUST/SHOULD/COULD severity findings",
        ],
        "next": "Return minimal result to orchestrator. Sub-agent task complete.",
    }


STEP_HANDLERS = {
    1: step_1_handler,
    2: step_2_handler,
    3: step_3_handler,
    4: step_4_handler,
}


def get_step_guidance(
    step: int, total_steps: int, module_path: str, provider: ResourceProvider = None, **kwargs
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
    state = LoopState.RETRY if qr_fail else LoopState.INITIAL
    qr = QRState(iteration=qr_iteration, state=state)

    step_info = STEPS.get(step, {})
    handler = STEP_HANDLERS.get(step)

    if step >= total_steps:
        handler = STEP_HANDLERS.get(4)
        step_info = STEPS.get(4, {})

    if handler:
        return handler(step_info, total_steps=total_steps, module_path=module_path, qr=qr, **kwargs)

    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Post-Impl-Doc: Documentation quality review workflow")
