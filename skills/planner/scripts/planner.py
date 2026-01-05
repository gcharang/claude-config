#!/usr/bin/env python3
"""
Interactive Sequential Planner - Two-phase planning workflow.

PLANNING PHASE: Step-based planning with context discovery (4 steps).
REVIEW PHASE: Sequential QR with gates before execution (8 steps).

Review phase flow:
  1. QR-Completeness -> 2. Gate -> 3. Developer Diffs ->
  4. QR-Code -> 5. Gate -> 6. TW Scrub ->
  7. QR-Docs -> 8. Gate -> Plan Approved

Usage:
    python3 planner.py --phase planning --step 1 --total-steps 4
    python3 planner.py --phase review --step 1 --total-steps 8
"""

import argparse
import sys
from pathlib import Path

from utils import format_qr_gate_output, get_qr_state_banner


PLANNING_VERIFICATION = """\
# Planning Verification Checklist

Complete in priority order before writing the plan.

## PHASE 1: CRITICAL (BLOCKING)

### VERIFY 1: Decision Log Completeness

TW sources ALL code comments from Decision Log. Missing entries mean
undocumented code.

- Every architectural choice has multi-step reasoning? INSUFFICIENT: 'Polling |
  Webhooks are unreliable' SUFFICIENT: 'Polling | 30% webhook failure -> need
  fallback anyway -> simpler as primary'
- Every micro-decision documented? (timeouts, thresholds, concurrency choices,
  data structure selections)
- Rejected alternatives listed with concrete reasons?
- Known risks have mitigations with file:line anchors for any behavioral claims?

### VERIFY 2: Code Intent Presence

STOP CHECK: For EACH implementation milestone:

- Does it contain a Code Intent section describing WHAT to change?
- If NO and milestone creates/modifies source files: STOP. Add Code Intent
  before proceeding.

Implementation milestones WITHOUT Code Intent cannot be approved. Only
documentation milestones (100% .md/.rst files) may skip Code Intent.

### VERIFY 3: Invisible Knowledge Capture (BLOCKING)

ALL architecture decisions, tradeoffs, invariants, and rationale that a future
reader could NOT infer from reading code alone MUST be documented in the plan's
Invisible Knowledge section.

MISSING INVISIBLE KNOWLEDGE IS A BLOCKING ISSUE.

Check for:

- Why was this approach chosen over alternatives?
- What tradeoffs were made and why?
- What invariants must be maintained?
- What assumptions underlie this design?
- What would a future maintainer need to know?

If the plan makes ANY decision that requires explanation beyond what code
comments can convey, it MUST be in Invisible Knowledge.

## PHASE 2: FORMAT

### VERIFY 4: Code Intent Clarity

For EACH implementation milestone:

- File paths exact (src/auth/handler.py not 'auth files')?
- Code Intent describes WHAT to change (functions, structs, behavior)?
- Key decisions reference Decision Log entries?
- NO diff blocks present (Developer fills those after plan is written)?

Code Intent should be clear enough for Developer to produce diffs without
ambiguity. If intent is vague, clarify it now.

### VERIFY 5: Milestone Specification

For EACH milestone:

- File paths exact?
- Requirements are specific behaviors, not 'handle X'?
- Acceptance criteria are testable pass/fail assertions?
- Tests section with type, backing, scenarios? (or explicit skip reason)
- Uncertainty flags added where applicable?

## PHASE 3: DOCUMENTATION

### VERIFY 6: Documentation Milestone

- Documentation milestone exists?
- CLAUDE.md format verification:
  - Tabular index format with WHAT/WHEN columns?
  - ~200 token budget (no prose sections)?
  - NO 'Key Invariants', 'Dependencies', 'Constraints' sections?
  - Overview is ONE sentence only?
- README.md included if Invisible Knowledge has content?
- Invisible Knowledge maps to README.md, not CLAUDE.md?
- Stub directories (only .gitkeep) excluded from CLAUDE.md requirement?

### VERIFY 7: Comment Hygiene

Comments will be transcribed VERBATIM. Write in TIMELESS PRESENT.

CONTAMINATED: '// Added mutex to fix race condition' CLEAN: '// Mutex serializes
cache access from concurrent requests'

CONTAMINATED: '// After the retry loop' CLEAN: (delete -- diff context encodes
location)

### VERIFY 8: Assumption Audit Complete

- Step 2 assumption audit completed (all categories)?
- Step 3 decision classification table written?
- Step 4 file classification table written?
- No 'assumption' rows remain unresolved?
- User responses recorded with 'user-specified' backing?

If any step was skipped: STOP. Go back and complete it.
"""


def get_plan_format() -> str:
    """Read the plan format template from resources."""
    format_path = Path(__file__).parent.parent / "resources" / "plan-format.md"
    return format_path.read_text()


PLANNING_STEPS = {
    1: {
        "title": "Context Discovery",
        "actions": [
            "READ resources: default-conventions.md, diff-format.md, temporal-contamination.md",
            "",
            "DELEGATE exploration to Explore sub-agent:",
            "  Task tool with subagent_type='Explore'",
            "  Prompt: Gather context for [TASK]. Return:",
            "    - Files to modify (exact paths)",
            "    - Codebase patterns (naming, errors, tests)",
            "    - Constraints and scope (IN/OUT)",
            "    - Success criteria",
            "",
            "CONTEXT EFFICIENCY:",
            "  Do NOT read source files directly.",
            "  Explore provides summaries. Developer reads files for diffs later.",
            "  This keeps your context focused on planning decisions.",
        ],
    },
    2: {
        "title": "Approach Generation",
        "actions": [
            "GENERATE 2-3 approach options:",
            "  - Include 'minimal change' option",
            "  - Include 'idiomatic/modern' option",
            "  - Document advantage/disadvantage for each",
            "",
            "TARGET TECH RESEARCH (if new tech/migration):",
            "  - What is canonical usage of target tech?",
            "  - Does it have different abstractions?",
            "",
            "TEST REQUIREMENTS:",
            "  - Check project docs for test requirements",
            "  - If silent, default-conventions domain='testing' applies",
        ],
    },
    3: {
        "title": "Assumption Surfacing",
        "actions": [
            "FAST PATH: Skip if task involves NONE of:",
            "  - Migration to new tech",
            "  - Policy defaults (lifecycle, capacity, failure handling)",
            "  - Architectural decisions with multiple valid approaches",
            "",
            "FULL CHECK (if any apply):",
            "  Audit each category with OPEN questions:",
            "    Pattern preservation, Migration strategy, Idiomatic usage,",
            "    Abstraction boundary, Test strategy, Policy defaults",
            "",
            "  For each assumption needing confirmation:",
            "    Use AskUserQuestion BEFORE proceeding",
            "    Record choice in Decision Log with 'user-specified' backing",
        ],
    },
    4: {
        "title": "Approach Selection & Milestones",
        "actions": [
            "EVALUATE approaches: P(success), failure mode, backtrack cost",
            "",
            "SELECT and record in Decision Log with MULTI-STEP chain:",
            "  BAD:  'Polling | Webhooks unreliable'",
            "  GOOD: 'Polling | 30% webhook failure -> need fallback anyway'",
            "",
            "MILESTONES (each deployable increment):",
            "  - Files: exact paths (each file in ONE milestone only)",
            "  - Requirements: specific behaviors",
            "  - Acceptance: testable pass/fail criteria",
            "  - Code Intent: WHAT to change (Developer converts to diffs in review phase)",
            "  - Tests: type, backing, scenarios",
            "",
            "PARALLELIZATION:",
            "  Vertical slices (parallel) > Horizontal layers (sequential)",
            "  BAD: M1=models, M2=services, M3=controllers (sequential)",
            "  GOOD: M1=auth stack, M2=users stack, M3=posts stack (parallel)",
            "  If file overlap: extract to M0 (foundation) or consolidate",
            "  Draw dependency diagram showing parallel waves",
            "",
            "RISKS: | Risk | Mitigation | Anchor (file:line if behavioral claim) |",
            "",
            "Write plan with Code Intent (no diffs yet).",
            "Developer fills diffs during review phase step 3.",
        ],
    },
    5: {
        "title": "Final Verification",
        "actions": [
            "Complete ALL verification checks (see checklist below):",
            "  Phase 1 (BLOCKING): Decision Log, Code Intent, Invisible Knowledge",
            "  Phase 2 (FORMAT): Code Intent clarity, Milestone spec",
            "  Phase 3 (DOCS): Documentation milestone, Comment hygiene",
            "",
            "STOP if any Phase 1 check fails. Fix before proceeding.",
        ],
        "include_verification": True,
    },
}


REVIEW_STEPS = {
    1: {
        "title": "QR-Completeness",
        "is_qr": True,
        "qr_name": "QR-COMPLETENESS",
        "actions": [
            "SPAWN quality-reviewer agent:",
            "  mode: plan-completeness",
            "  Check: Decision Log, policy defaults, plan structure",
            "",
            "Expected output: PASS or ISSUES",
        ],
    },
    # Step 2 is gate - handled by format_review_gate
    3: {
        "title": "Developer Fills Diffs",
        "is_work": True,
        "work_agent": "developer",
        "actions": [
            "SPAWN developer agent:",
            "  'Convert Code Intent to Code Changes for all implementation milestones.",
            "   Read target files, write unified diffs, edit plan in-place.",
            "   ONLY produce diffs. Do not modify other plan sections.'",
            "",
            "Developer edits plan file IN-PLACE.",
            "Wait for completion before proceeding to QR-Code.",
        ],
    },
    4: {
        "title": "QR-Code",
        "is_qr": True,
        "qr_name": "QR-CODE",
        "actions": [
            "SPAWN quality-reviewer agent:",
            "  mode: plan-code",
            "  Check: Diff context matches codebase, RULE 0/1/2",
            "",
            "Expected output: PASS or ISSUES",
        ],
    },
    # Step 5 is gate - handled by format_review_gate
    6: {
        "title": "TW Documentation Scrub",
        "is_work": True,
        "work_agent": "technical-writer",
        "actions": [
            "SPAWN technical-writer agent:",
            "  mode: plan-scrub",
            "  Task: Add WHY comments from Decision Log, enrich prose",
            "",
            "TW edits plan file IN-PLACE.",
            "Wait for completion before proceeding to QR-Docs.",
        ],
    },
    7: {
        "title": "QR-Docs",
        "is_qr": True,
        "qr_name": "QR-DOCS",
        "actions": [
            "SPAWN quality-reviewer agent:",
            "  mode: plan-docs",
            "  Check: Temporal contamination, hidden baselines, WHY not WHAT",
            "",
            "Expected output: PASS or ISSUES",
        ],
    },
    # Step 8 is gate - handled by format_review_gate
}


def get_planning_guidance(step: int, total_steps: int) -> dict:
    """Returns guidance for planning phase steps."""
    is_complete = step >= total_steps

    if is_complete:
        plan_format = get_plan_format()
        info = PLANNING_STEPS.get(5, PLANNING_STEPS[4])
        actions = list(info["actions"])
        if info.get("include_verification"):
            actions.append("")
            actions.append(PLANNING_VERIFICATION)
        return {
            "title": "Planning Complete",
            "actions": actions,
            "next": (
                f"Write plan using this format:\n\n{plan_format}\n\n"
                "Plan should have Code Intent (no diffs yet).\n"
                "Developer fills diffs during review phase step 3.\n\n"
                "Invoke review phase:\n"
                "  python3 planner.py --phase review --step 1 --total-steps 8"
            ),
        }

    info = PLANNING_STEPS.get(step, PLANNING_STEPS[4])
    actions = list(info["actions"])
    if info.get("include_verification"):
        actions.append("")
        actions.append(PLANNING_VERIFICATION)
    return {
        "title": info["title"],
        "actions": actions,
        "next": f"Step {step + 1}: {PLANNING_STEPS.get(step + 1, PLANNING_STEPS[4])['title']}",
    }


def format_review_gate(step: int, qr_status: str, qr_iteration: int) -> str:
    """Format gate step output for review phase."""
    # Gate step mapping: gate_step -> (qr_name, work_step, pass_step, work_agent)
    # Note: QR-Completeness fixes are done by main agent (plan structure is main agent's work)
    gate_config = {
        2: ("QR-COMPLETENESS", 1, 3, "yourself (fix Decision Log, plan structure issues)"),
        5: ("QR-CODE", 3, 6, "developer"),
        8: ("QR-DOCS", 6, None, "technical-writer"),  # None = plan approved
    }

    qr_name, work_step, pass_step, work_agent = gate_config[step]

    if pass_step:
        pass_cmd = f"python3 planner.py --phase review --step {pass_step} --total-steps 8"
    else:
        pass_cmd = "PLAN APPROVED. Ready for /plan-execution."

    def fail_cmd(iteration: int) -> str:
        return (
            f"python3 planner.py --phase review --step {work_step} --total-steps 8 "
            f"--qr-fail --qr-iteration {iteration}"
        )

    return format_qr_gate_output(
        gate_name=qr_name,
        qr_status=qr_status,
        script_name="planner.py",
        pass_command=pass_cmd,
        fail_command=fail_cmd,
        qr_iteration=qr_iteration,
        work_agent=work_agent,
    )


def get_review_guidance(step: int, total_steps: int,
                         qr_iteration: int = 1, qr_fail: bool = False,
                         qr_status: str = None) -> dict | str:
    """Returns guidance for review phase steps."""

    # Gate steps (2, 5, 8) use shared gate function
    if step in (2, 5, 8):
        if not qr_status:
            return {"error": f"--qr-status required for gate step {step}"}
        return format_review_gate(step, qr_status, qr_iteration)

    info = REVIEW_STEPS.get(step)
    if not info:
        return {"error": f"Invalid step {step}"}

    # Build actions
    actions = []

    # Add QR banner for QR steps
    if info.get("is_qr"):
        qr_name = info.get("qr_name", "QR")
        banner = get_qr_state_banner(qr_name, qr_iteration, qr_fail)
        actions.extend(banner)

    # Add fix mode banner for work steps with --qr-fail
    if info.get("is_work") and qr_fail:
        work_agent = info.get("work_agent", "agent")
        actions.extend([
            f"===[ FIX MODE (iteration {qr_iteration}) ]===",
            f"QR found issues. Spawn {work_agent} with QR findings.",
            f"The {work_agent} will address the specific issues identified.",
            "After fixes, proceed to next QR step.",
            "======================================",
            "",
        ])

    actions.extend(info["actions"])

    # Determine next step
    next_step = step + 1
    next_titles = {
        1: "QR-Completeness Gate",
        3: "QR-Code",
        4: "QR-Code Gate",
        6: "QR-Docs",
        7: "QR-Docs Gate",
    }
    next_title = next_titles.get(step, REVIEW_STEPS.get(next_step, {}).get("title", "Next"))

    return {
        "title": info["title"],
        "actions": actions,
        "next": f"Step {next_step} ({next_title}) with --qr-status pass|fail" if step in (1, 4, 7) else f"Step {next_step}: {next_title}",
    }


def format_output(phase: str, step: int, total_steps: int,
                  qr_iteration: int, qr_fail: bool, qr_status: str) -> str:
    """Format output for display."""
    if phase == "planning":
        guidance = get_planning_guidance(step, total_steps)
        phase_label = "PLANNING"
    else:
        guidance = get_review_guidance(step, total_steps, qr_iteration, qr_fail, qr_status)
        phase_label = "REVIEW"

    # Gate steps return string directly
    if isinstance(guidance, str):
        return guidance

    # Handle error case
    if "error" in guidance:
        return f"Error: {guidance['error']}"

    lines = [
        f"PLANNER - {phase_label} - Step {step}/{total_steps}: {guidance['title']}",
        "",
        "DO:",
    ]

    for action in guidance["actions"]:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    lines.append("")
    lines.append("NEXT:")
    lines.append(f"  {guidance['next']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Sequential Planner (Two-Phase)",
        epilog="planning: 4 steps | review: 8 steps with gates",
    )

    parser.add_argument("--phase", type=str, default="planning",
                        choices=["planning", "review"])
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--qr-iteration", type=int, default=1)
    parser.add_argument("--qr-fail", action="store_true",
                        help="Work step is fixing QR issues")
    parser.add_argument("--qr-status", type=str, choices=["pass", "fail"],
                        help="QR result for gate steps (2, 5, 8)")

    args = parser.parse_args()

    if args.step < 1 or args.total_steps < 1:
        print("Error: step and total-steps must be >= 1", file=sys.stderr)
        sys.exit(1)

    min_steps = 4 if args.phase == "planning" else 8
    if args.total_steps < min_steps:
        print(f"Error: {args.phase} phase requires at least {min_steps} steps", file=sys.stderr)
        sys.exit(1)

    # Gate steps require --qr-status
    if args.phase == "review" and args.step in (2, 5, 8) and not args.qr_status:
        print(f"Error: --qr-status required for gate step {args.step}", file=sys.stderr)
        sys.exit(1)

    print(format_output(args.phase, args.step, args.total_steps,
                        args.qr_iteration, args.qr_fail, args.qr_status))


if __name__ == "__main__":
    main()
