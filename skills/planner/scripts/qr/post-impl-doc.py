#!/usr/bin/env python3
"""
QR-Post-Impl-Doc - Step-based workflow for quality-reviewer sub-agent.

Documentation quality review AFTER technical writer pass:
- CLAUDE.md format verification (tabular index)
- README.md content verification (invisible knowledge)
- Comment hygiene (temporal contamination)
- Proximity audit (docs adjacent to code)

Usage:
    python3 qr/post-impl-doc.py --step 1 --total-steps 4 [--qr-iteration 1] [--qr-fail]

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
from skills.lib.workflow.formatters import format_qr_banner

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
        banner = format_qr_banner("DOC QR", qr)
        return {
            "title": "Documentation Quality Review",
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
            "next": f"python3 {script_path} --step 2 --total-steps {total_steps}",
        }

    # Step 2: CLAUDE.md verification
    if step == 2:
        return {
            "title": "CLAUDE.md Format Verification",
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
            "next": f"python3 {script_path} --step 3 --total-steps {total_steps}",
        }

    # Step 3: README.md and comment verification
    if step == 3:
        temporal_resource = get_resource("temporal-contamination.md")
        return {
            "title": "README.md and Comment Verification",
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
                "KNOWLEDGE TYPE MAPPING:",
                "  | Type                  | Required Location                   |",
                "  | --------------------- | ----------------------------------- |",
                "  | Architecture diagrams | README.md in SAME directory         |",
                "  | Data flow             | README.md or module docstring       |",
                "  | Tradeoffs             | Code comment where decision shows   |",
                "  | Invariants            | Code comment at enforcement point   |",
                "  | Why This Structure    | README.md in SAME directory         |",
                "",
                "---",
                "",
                "COMMENT HYGIENE (temporal contamination check):",
                "",
                temporal_resource,
                "",
                "Check modified files for contaminated comments.",
            ],
            "next": f"python3 {script_path} --step 4 --total-steps {total_steps}",
        }

    # Step 4: Output format (final step)
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
                "- **Location**: [file or directory]",
                "- **Issue**: [What is wrong]",
                "- **Suggested Fix**: [Concrete action]",
                "```",
                "",
                "VERDICT GUIDE:",
                "  PASS: All docs correct format, IK captured, no contamination",
                "  ISSUES: Any doc format violations or missing IK",
            ],
            "next": "Return minimal result to orchestrator. Sub-agent task complete.",
        }

    # Fallback
    return {"title": "Unknown", "actions": ["Check step number"], "next": ""}


if __name__ == "__main__":
    from skills.lib.workflow.cli import mode_main
    mode_main(__file__, get_step_guidance, "QR-Post-Impl-Doc: Documentation quality review workflow")
