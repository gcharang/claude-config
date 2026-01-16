#!/usr/bin/env python3
"""
Interactive Sequential Planner - Unified 13-step planning workflow.

Steps 1-5:  Planning (context, testing strategy, approaches, assumptions, milestones)
Steps 6-13: Review (QR gates, developer diffs, TW scrub)

Flow:
  1. Context Discovery
  2. Testing Strategy Discovery
  3. Approach Generation
  4. Assumption Surfacing
  5. Approach Selection & Milestones
  6. QR-Completeness -> 7. Gate
  8. Developer Fills Diffs
  9. QR-Code -> 10. Gate
  11. TW Documentation Scrub
  12. QR-Docs -> 13. Gate -> Plan Approved
"""

import argparse
import sys

from skills.lib.workflow.types import QRState, QRStatus, GateConfig, AgentRole, Dispatch, LoopState
from skills.lib.workflow.core import (
    Workflow,
    StepDef,
    StepContext,
    Outcome,
)
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.workflow.cli import add_qr_args
from skills.planner.shared.resources import get_mode_script_path, PlannerResourceProvider


# Module path for -m invocation
MODULE_PATH = "skills.planner.planner"

# Resource provider instance
_provider = PlannerResourceProvider()


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
    return _provider.get_resource("plan-format.md")


# Unified step definitions (1-13)
# Step flags:
#   is_qr: True = step runs QR verification (followed by gate step)
#   is_dispatch: True = step dispatches to sub-agent via mode script
#   is_work: True = step performs modifications (vs review-only)
STEPS = {
    # Planning steps (1-5)
    1: {
        "title": "Context Discovery",
        "is_dispatch": True,
        "dispatch_agent": "Explore",
        "mode_script": "explore.py",
        "mode_total_steps": 5,
        "context_vars": {
            "TASK": "the user's task/request being planned",
            "DECISION_CRITERIA": "what planning decisions will consume this output",
        },
        "actions": [
            "READ .claude/conventions: structural.md, diff-format.md, temporal.md",
            "",
            "DELEGATE exploration to Explore sub-agent with decision context.",
            "",
            "The sub-agent will follow a 5-step workflow:",
            "  1. Exploration Planning - parse task into investigation targets",
            "  2. Execute Exploration - gather findings with decision-relevant depth",
            "  3. Gap Analysis - check coverage against decision criteria",
            "  4. Fill Gaps - additional exploration for uncovered criteria",
            "  5. Format Output - compress into structured XML",
        ],
        "post_dispatch": [
            "The sub-agent MUST invoke explore.py and follow its guidance.",
            "",
            "Expected output: Structured XML with sections:",
            "  <approach_inputs> - for Step 3 (Approach Generation)",
            "  <assumption_inputs> - for Step 4 (Assumption Surfacing)",
            "  <milestone_inputs> - for Step 5 (Milestone Planning)",
        ],
    },
    2: {
        "title": "Testing Strategy Discovery",
        "actions": [
            "DISCOVER existing testing strategy from:",
            "  - User conversation hints",
            "  - Project CLAUDE.md / README.md",
            "  - conventions/structural.md domain='testing-strategy'",
            "",
            "PROPOSE test approach for EACH type:",
            "",
            "For UNIT tests:",
            "  Use AskUserQuestion:",
            "    'For unit tests, use property-based (quickcheck) approach?'",
            "    Options: [Yes - few tests cover many variables] [No - example-based] [Skip - no unit tests]",
            "",
            "For INTEGRATION tests:",
            "  Use AskUserQuestion:",
            "    'For integration tests, use real dependencies?'",
            "    Options: [Yes - testcontainers/real deps] [No - mocks] [Skip - no integration tests]",
            "",
            "For E2E tests:",
            "  Use AskUserQuestion:",
            "    'For e2e tests, use generated datasets?'",
            "    Options: [Yes - deterministic generated data] [No - fixtures] [Skip - no e2e tests]",
            "",
            "Record confirmed strategy in Decision Log with 'user-specified' backing.",
        ],
    },
    3: {
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
    4: {
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
            "    Abstraction boundary, Policy defaults",
            "",
            "  For each assumption needing confirmation:",
            "    Use AskUserQuestion BEFORE proceeding",
            "    Record choice in Decision Log with 'user-specified' backing",
        ],
    },
    5: {
        "title": "Approach Selection & Milestones",
        "include_verification": True,
        "include_plan_format": True,
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
            "  - Code Intent: WHAT to change (Developer converts to diffs in step 7)",
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
            "Developer fills diffs in step 8.",
        ],
    },
    # Review steps (6-13)
    6: {
        "title": "QR-Completeness",
        "is_qr": True,
        "qr_name": "QR-COMPLETENESS",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/plan-completeness.py",
        "mode_total_steps": 7,  # Added step 6: Self-Validate Suggested Fixes
        "context_vars": {"PLAN_FILE": "path to the plan being reviewed"},
        "post_dispatch": [
            "The sub-agent MUST invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES",
        ],
        "post_qr_routing": {"self_fix": True},
    },
    # Step 7 is gate - handled by GATES dict
    8: {
        "title": "Developer Fills Diffs",
        "is_work": True,
        "work_agent": "developer",
        "is_dispatch": True,
        "dispatch_agent": "developer",
        "mode_script": "dev/fill-diffs.py",
        "mode_total_steps": 4,
        "context_vars": {"PLAN_FILE": "path to the plan being reviewed"},
        "post_dispatch": [
            "The sub-agent MUST invoke the script and follow its guidance.",
            "Developer edits plan file IN-PLACE.",
        ],
    },
    9: {
        "title": "QR-Code",
        "is_qr": True,
        "qr_name": "QR-CODE",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/plan-code.py",
        "mode_total_steps": 8,  # Added step 7: Self-Validate Suggested Fixes
        "context_vars": {"PLAN_FILE": "path to the plan being reviewed"},
        "post_dispatch": [
            "The sub-agent MUST invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "developer"},
    },
    # Step 10 is gate - handled by GATES dict
    11: {
        "title": "TW Documentation Scrub",
        "is_work": True,
        "work_agent": "technical-writer",
        "is_dispatch": True,
        "dispatch_agent": "technical-writer",
        "mode_script": "tw/plan-scrub.py",
        "mode_total_steps": 6,
        "context_vars": {"PLAN_FILE": "path to the plan being reviewed"},
        "post_dispatch": [
            "The sub-agent MUST invoke the script and follow its guidance.",
            "TW edits plan file IN-PLACE.",
            "",
            "Expected output: COMPLETE or BLOCKED",
        ],
    },
    12: {
        "title": "QR-Docs",
        "is_qr": True,
        "qr_name": "QR-DOCS",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/plan-docs.py",
        "mode_total_steps": 6,  # Added step 5: Self-Validate Suggested Fixes
        "context_vars": {"PLAN_FILE": "path to the plan being reviewed"},
        "post_dispatch": [
            "The sub-agent MUST invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "technical-writer"},
    },
    # Step 13 is gate - handled by GATES dict
}


# Gate configurations (steps 7, 10, 13)
GATES = {
    7: GateConfig(
        qr_name="QR-COMPLETENESS",
        work_step=5,
        pass_step=8,
        pass_message="Proceed to step 8 (Developer Fills Diffs).",
        self_fix=True,
    ),
    10: GateConfig(
        qr_name="QR-CODE",
        work_step=8,
        pass_step=11,
        pass_message="Proceed to step 11 (TW Documentation Scrub).",
        self_fix=False,
        fix_target=AgentRole.DEVELOPER,
    ),
    13: GateConfig(
        qr_name="QR-DOCS",
        work_step=11,
        pass_step=None,
        pass_message="PLAN APPROVED. Ready for plan execution.",
        self_fix=False,
        fix_target=AgentRole.TECHNICAL_WRITER,
    ),
}


def step_gate_handler(step_info: dict, step: int, qr: QRState, **kwargs) -> str:
    """Handle gate steps (7, 10, 13)."""
    return format_gate(step, qr)


def step_5_handler(step_info: dict, step: int, qr: QRState, total_steps: int, **kwargs) -> dict:
    """Handle step 5 (planning) in normal or fix mode."""
    if qr.state == LoopState.RETRY:
        banner = render(W.el("state_banner", checkpoint="PLAN-FIX", iteration=str(qr.iteration), mode="fix").build(), XMLRenderer())
        fix_actions = [banner, ""] + [
            "FIX MODE: QR-COMPLETENESS found plan structure issues.",
            "",
            "Review the QR findings in your context.",
            "Fix the identified issues in the plan file directly.",
            "",
            "Common issues:",
            "  - Missing Decision Log entries",
            "  - Incomplete Code Intent sections",
            "  - Missing Invisible Knowledge",
            "  - Incomplete milestone specifications",
            "",
            "Use Edit tool to fix the plan file.",
            "After fixing, proceed to QR-Completeness for fresh verification.",
        ]
        return {
            "title": f"{step_info['title']} - Fix Mode",
            "actions": fix_actions,
            "next": f"python3 -m {MODULE_PATH} --step 6 --total-steps {total_steps}",
        }
    return None


def step_dispatch_handler(step_info: dict, step: int, qr: QRState, **kwargs) -> list:
    """Add QR banner for QR dispatch steps."""
    if step_info.get("is_qr"):
        qr_name = step_info.get("qr_name", "QR")
        banner = render(W.el("state_banner", checkpoint=qr_name, iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
        return [banner, ""]
    return []


def step_verification_handler(step_info: dict, **kwargs) -> list:
    """Add verification checklist for step 5."""
    if step_info.get("include_verification"):
        return ["", PLANNING_VERIFICATION]
    return []


def step_format_handler(step_info: dict, **kwargs) -> list:
    """Add plan format for step 5."""
    if step_info.get("include_plan_format"):
        plan_format = get_plan_format()
        return ["", "Write plan using this format:", "", plan_format]
    return []


STEP_HANDLERS = {
    5: step_5_handler,
    7: step_gate_handler,
    10: step_gate_handler,
    13: step_gate_handler,
}


def step_handler_noop(ctx: StepContext) -> tuple[Outcome, dict]:
    """Generic handler for output-only steps."""
    return Outcome.OK, {}


def step_gate_passthrough(ctx: StepContext) -> tuple[Outcome, dict]:
    """Pass-through handler for gate routing steps."""
    return Outcome.OK, {}


WORKFLOW = Workflow(
    "planner",
    StepDef(
        id="context_discovery",
        title="Context Discovery",
        actions=STEPS[1]["actions"],
        handler=Dispatch(
            agent=AgentRole.EXPLORE,
            script="skills.planner.explore",
            total_steps=5,
            context_vars={
                "TASK": "the user's task/request being planned",
                "DECISION_CRITERIA": "what planning decisions will consume this output",
            },
        ),
        next={Outcome.OK: "testing_strategy"},
    ),
    StepDef(
        id="testing_strategy",
        title="Testing Strategy Discovery",
        actions=STEPS[2]["actions"],
        handler=step_handler_noop,
        next={Outcome.OK: "approach_generation"},
    ),
    StepDef(
        id="approach_generation",
        title="Approach Generation",
        actions=STEPS[3]["actions"],
        handler=step_handler_noop,
        next={Outcome.OK: "assumption_surfacing"},
    ),
    StepDef(
        id="assumption_surfacing",
        title="Assumption Surfacing",
        actions=STEPS[4]["actions"],
        handler=step_handler_noop,
        next={Outcome.OK: "approach_selection"},
    ),
    StepDef(
        id="approach_selection",
        title="Approach Selection & Milestones",
        actions=STEPS[5]["actions"],
        handler=step_handler_noop,
        next={Outcome.OK: "qr_completeness"},
    ),
    StepDef(
        id="qr_completeness",
        title="QR-Completeness",
        actions=[],
        handler=Dispatch(
            agent=AgentRole.QUALITY_REVIEWER,
            script="skills.planner.qr.plan_completeness",
            total_steps=7,  # Added step 6: Self-Validate Suggested Fixes
            context_vars={"PLAN_FILE": "path to the plan being reviewed"},
        ),
        next={Outcome.OK: "qr_completeness_gate", Outcome.FAIL: "qr_completeness_gate"},
    ),
    StepDef(
        id="qr_completeness_gate",
        title="QR-Completeness Gate",
        actions=[],
        handler=step_gate_passthrough,
        next={Outcome.OK: "developer_fills_diffs", Outcome.FAIL: "approach_selection"},
    ),
    StepDef(
        id="developer_fills_diffs",
        title="Developer Fills Diffs",
        actions=[],
        handler=Dispatch(
            agent=AgentRole.DEVELOPER,
            script="skills.planner.dev.fill_diffs",
            total_steps=4,
            context_vars={"PLAN_FILE": "path to the plan being reviewed"},
        ),
        next={Outcome.OK: "qr_code"},
    ),
    StepDef(
        id="qr_code",
        title="QR-Code",
        actions=[],
        handler=Dispatch(
            agent=AgentRole.QUALITY_REVIEWER,
            script="skills.planner.qr.plan_code",
            total_steps=7,
            context_vars={"PLAN_FILE": "path to the plan being reviewed"},
        ),
        next={Outcome.OK: "qr_code_gate", Outcome.FAIL: "qr_code_gate"},
    ),
    StepDef(
        id="qr_code_gate",
        title="QR-Code Gate",
        actions=[],
        handler=step_gate_passthrough,
        next={Outcome.OK: "tw_documentation_scrub", Outcome.FAIL: "developer_fills_diffs"},
    ),
    StepDef(
        id="tw_documentation_scrub",
        title="TW Documentation Scrub",
        actions=[],
        handler=Dispatch(
            agent=AgentRole.TECHNICAL_WRITER,
            script="skills.planner.tw.plan_scrub",
            total_steps=6,
            context_vars={"PLAN_FILE": "path to the plan being reviewed"},
        ),
        next={Outcome.OK: "qr_docs"},
    ),
    StepDef(
        id="qr_docs",
        title="QR-Docs",
        actions=[],
        handler=Dispatch(
            agent=AgentRole.QUALITY_REVIEWER,
            script="skills.planner.qr.plan_docs",
            total_steps=6,  # Added step 5: Self-Validate Suggested Fixes
            context_vars={"PLAN_FILE": "path to the plan being reviewed"},
        ),
        next={Outcome.OK: "qr_docs_gate", Outcome.FAIL: "qr_docs_gate"},
    ),
    StepDef(
        id="qr_docs_gate",
        title="QR-Docs Gate",
        actions=[],
        handler=step_gate_passthrough,
        next={Outcome.OK: None, Outcome.FAIL: "tw_documentation_scrub"},
    ),
    description="Interactive sequential planner with QR gates",
)


def format_gate(step: int, qr: QRState) -> str:
    """Format gate step output using XML format."""
    from skills.lib.workflow.ast.nodes import ElementNode
    from skills.lib.workflow.constants import QR_ITERATION_LIMIT, get_blocking_severities

    gate = GATES[step]
    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(f"{gate.qr_name} Gate"),
            script="planner", step=str(step), total="13"
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # Gate result
    if qr.passed:
        parts.append(f'<gate_result status="pass">GATE PASSED</gate_result>')
    else:
        parts.append(f'<gate_result status="fail">GATE FAILED (iteration {qr.iteration} of {QR_ITERATION_LIMIT})</gate_result>')
    parts.append("")

    # Actions
    actions = []
    if qr.passed:
        actions.append(gate.pass_message)
        actions.append("")
        actions.append("<forbidden>")
        actions.append("Asking the user whether to proceed - the workflow is deterministic")
        actions.append("Offering alternatives to the next step - all steps are mandatory")
        actions.append("Interpreting 'proceed' as optional - EXECUTE immediately")
        actions.append("</forbidden>")
    else:
        # Pedantic mode reminder
        actions.append("<pedantic_enforcement>")
        actions.append("QR exists to catch problems BEFORE they reach production.")
        actions.append("See <severity_filter> below for which severities block at this iteration.")
        actions.append("</pedantic_enforcement>")
        actions.append("")

        # Severity filter
        blocking = get_blocking_severities(qr.iteration)
        if blocking == {"MUST", "SHOULD", "COULD"}:
            actions.append("<severity_filter>")
            actions.append(f"ITERATION {qr.iteration} of {QR_ITERATION_LIMIT}: All severities block (MUST, SHOULD, COULD)")
            actions.append("Fix ALL issues reported by QR before proceeding.")
            actions.append("</severity_filter>")
            actions.append("")
        elif blocking == {"MUST", "SHOULD"}:
            actions.append("<severity_filter>")
            actions.append(f"ITERATION {qr.iteration} of {QR_ITERATION_LIMIT}: Only MUST and SHOULD severities block")
            actions.append("COULD severity issues (DEAD_CODE, FORMATTER_FIXABLE, MINOR_INCONSISTENCY) may be deferred.")
            actions.append("Focus on MUST and SHOULD issues. COULD issues are noted but do not block.")
            actions.append("</severity_filter>")
            actions.append("")
        else:
            actions.append("<severity_filter>")
            actions.append(f"ITERATION {qr.iteration} of {QR_ITERATION_LIMIT}: Only MUST severity blocks")
            actions.append("SHOULD and COULD severity issues may be deferred.")
            actions.append("Focus ONLY on MUST issues (knowledge loss, unrecoverable if missed).")
            actions.append("SHOULD issues (structural debt) are noted but do not block.")
            actions.append("COULD issues (cosmetic) are noted but do not block.")
            actions.append("")
            actions.append("If NO MUST issues remain, this gate PASSES despite SHOULD/COULD issues.")
            actions.append("</severity_filter>")
            actions.append("")

        next_iteration = qr.iteration + 1
        if next_iteration > QR_ITERATION_LIMIT:
            actions.append("<iteration_limit_reached>")
            actions.append(f"QR has failed {qr.iteration} times at this checkpoint.")
            actions.append("")
            actions.append("NOTE: At iteration 5+, only MUST severity issues should block.")
            actions.append("If QR is reporting SHOULD/COULD issues only, consider proceeding.")
            actions.append("")
            actions.append("MANDATORY: Use AskUserQuestion NOW:")
            actions.append(f"  question: 'QR has found issues across {QR_ITERATION_LIMIT} iterations. How to proceed?'")
            actions.append("  header: 'QR Loop'")
            actions.append("  options:")
            actions.append("    - label: 'Continue iterating'")
            actions.append("      description: 'Keep fixing until QR passes'")
            actions.append("    - label: 'Fix MUST issues only'")
            actions.append("      description: 'Accept SHOULD/COULD issues, fix MUST issues'")
            actions.append("    - label: 'Skip this check'")
            actions.append("      description: 'Accept current state, note remaining issues'")
            actions.append("    - label: 'Abort'")
            actions.append("      description: 'Stop and review'")
            actions.append("")
            actions.append("<human_override_recording>")
            actions.append("If user selects 'Skip this check' or 'Fix MUST issues only':")
            actions.append("")
            actions.append("1. Record accepted risks to plan's Decision Log:")
            actions.append("   Add to ## Decision Log section (create if missing):")
            actions.append("   | Issue | Rationale | Iteration |")
            actions.append("   | ----- | --------- | --------- |")
            actions.append(f"   | [Each MUST issue text] | [User's selected option] | {qr.iteration} |")
            actions.append("")
            actions.append("2. Instruct TW to add :TODO: comments at code locations:")
            actions.append("   For each accepted MUST issue with a file/line reference:")
            actions.append("   Delegate to @agent-technical-writer in free-form mode:")
            actions.append("   'Add :TODO: comments at [file:line] marking accepted risk: [issue text]'")
            actions.append("</human_override_recording>")
            actions.append("</iteration_limit_reached>")
            actions.append("")
            actions.append("<when_user_says_continue>")
            actions.append("When user selects 'Continue iterating':")
            actions.append("  1. IMMEDIATELY invoke the exact command from <invoke_after> below")
            actions.append("  2. The Python script provides the fix guidance - invoke it first")
            actions.append("  3. Iteration counter is already incremented in the command")
            actions.append("</when_user_says_continue>")
            actions.append("")

        # Gate routing
        if gate.self_fix:
            actions.append("NEXT ACTION:")
            actions.append("  Invoke the command in <invoke_after> below.")
            actions.append("  The next step will provide fix guidance for plan structure issues.")
            actions.append("")
        else:
            fix_target = gate.fix_target.value if gate.fix_target else "developer"
            actions.append("NEXT ACTION:")
            actions.append("  Invoke the command in <invoke_after> below.")
            actions.append(f"  The next step will dispatch {fix_target} with fix guidance.")
            actions.append("")
            actions.append("<qr_report_path_passthrough>")
            actions.append("QR_REPORT_PATH from QR output MUST be passed to the work step.")
            actions.append("You do NOT read this file. The sub-agent reads it.")
            actions.append("</qr_report_path_passthrough>")
            actions.append("")

        actions.append("<forbidden>")
        actions.append("Fixing issues directly from this gate step")
        actions.append("Spawning agents directly from this gate step")
        actions.append("Using Edit/Write tools yourself")
        actions.append("Proceeding without invoking the next step")
        actions.append("Interpreting 'minor issues' as skippable")
        actions.append("</forbidden>")

    parts.append("<workflow>")
    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    # Determine next command
    if qr.passed and gate.pass_step is not None:
        next_cmd = f"python3 -m {MODULE_PATH} --step {gate.pass_step} --total-steps 13"
    else:
        next_iteration = qr.iteration + 1
        next_cmd = f"python3 -m {MODULE_PATH} --step {gate.work_step} --total-steps 13 --qr-fail --qr-iteration {next_iteration}"

    parts.append(render(W.el("invoke_after", TextNode(next_cmd)).build(), XMLRenderer()))
    parts.append("")
    parts.append(render(
        W.el("next",
            TextNode("After current_action completes, execute invoke_after."),
            TextNode(f"Re-read now: {next_cmd}"),
            required="true"
        ).build(),
        XMLRenderer()
    ))
    parts.append("</workflow>")

    return "\n".join(parts)


def generic_step_handler(step_info, step, total_steps, **kwargs):
    """Generic handler for standard steps without special logic."""
    actions = list(step_info.get("actions", []))
    actions.extend(step_verification_handler(step_info))
    actions.extend(step_format_handler(step_info))

    qr = kwargs.get("qr", QRState())
    qr_banner = step_dispatch_handler(step_info, step=step, qr=qr)
    if qr_banner:
        actions[0:0] = qr_banner

    # Generate dispatch block for dispatch steps
    if step_info.get("is_dispatch"):
        mode_script = get_mode_script_path(step_info["mode_script"])
        mode_total_steps = step_info.get("mode_total_steps", 5)
        dispatch_agent = step_info.get("dispatch_agent", "agent")
        context_vars = step_info.get("context_vars", {})
        qr_fail = kwargs.get("qr_fail", False)
        qr_iteration = kwargs.get("qr_iteration", 1)

        # Add orchestrator constraint before dispatch
        constraint = render(
            W.el(
                "orchestrator_constraint",
                TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
                TextNode("Your agents are highly capable. Trust them with ANY issue."),
                TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
                TextNode(""),
                TextNode("THINKING EFFICIENCY: Before dispatch, max 5 words internal reasoning."),
                TextNode('Example thinking: "Step 1 -> need context -> dispatch Explore"'),
                TextNode(""),
                TextNode("The Task tool prompt you send to sub-agents should be complete."),
            ).build(),
            XMLRenderer(),
        )
        actions.append(constraint)
        actions.append("")

        # Build invoke command with QR flags when in fix mode
        invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps {mode_total_steps}"
        if qr.state == LoopState.RETRY:
            invoke_cmd += f" --qr-fail --qr-iteration {qr.iteration}"

        # Build dispatch block inline
        if qr.state == LoopState.RETRY:
            context_vars_copy = dict(context_vars)
            context_vars_copy["QR_REPORT_PATH"] = "exact path from QR output"
        else:
            context_vars_copy = context_vars

        dispatch_lines = [f'<subagent_dispatch agent="{dispatch_agent}" mode="script">']
        if context_vars_copy:
            dispatch_lines.append("  <context>")
            for name, description in context_vars_copy.items():
                dispatch_lines.append(f'    <var name="{name}">{description}</var>')
            dispatch_lines.append("  </context>")
        dispatch_lines.append(f"  <invoke>{invoke_cmd}</invoke>")
        dispatch_lines.append("  <handoff_instruction>")
        dispatch_lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
        dispatch_lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
        dispatch_lines.append("  </handoff_instruction>")
        if qr.state == LoopState.RETRY:
            dispatch_lines.append("  <qr_report_passthrough>")
            dispatch_lines.append("    CRITICAL: Include QR_REPORT_PATH verbatim in your Task prompt.")
            dispatch_lines.append("    DO NOT read QR_REPORT_PATH yourself.")
            dispatch_lines.append("    DO NOT extract, summarize, or interpret the issues.")
            dispatch_lines.append("    The sub-agent reads the file directly.")
            dispatch_lines.append("  </qr_report_passthrough>")
        dispatch_lines.append("</subagent_dispatch>")
        dispatch_block = "\n".join(dispatch_lines)
        actions.append(dispatch_block)
        actions.append("")

        # Add post-dispatch instructions
        post_dispatch = step_info.get("post_dispatch", [])
        actions.extend(post_dispatch)

        # Add post-QR routing block for QR steps
        post_qr_config = step_info.get("post_qr_routing")
        if post_qr_config:
            from skills.lib.workflow.constants import QR_ITERATION_LIMIT
            from skills.lib.workflow.ast.nodes import ElementNode
            fix_target = post_qr_config.get("fix_target", "developer")

            routing_table = [
                "| QR Result              | Your Action                         |",
                "| ---------------------- | ----------------------------------- |",
                "| PASS (no issues)       | Invoke command from <if_pass> below |",
                "| ISSUES / concerns / *  | Invoke command from <if_fail> below |",
            ]

            routing_block = render(
                W.el(
                    "post_qr_routing",
                    ElementNode("role", {}, [TextNode("You are the ORCHESTRATOR. After QR returns, your ONLY action is routing.")]),
                    ElementNode(
                        "pedantic_mode",
                        {},
                        [
                            TextNode("EVERY issue is blocking. There are no 'minor concerns' or 'non-critical issues'."),
                            TextNode("If QR returns ANYTHING other than clean PASS, route to <if_fail>."),
                            TextNode(f"Defense: Max {QR_ITERATION_LIMIT} iterations, then escalate to user via AskUserQuestion."),
                        ],
                    ),
                    ElementNode("routing_table", {}, [TextNode("\n".join(routing_table))]),
                ).build(),
                XMLRenderer(),
            )
            actions.append("")
            actions.append(routing_block)

    # Determine next step
    next_step = step + 1

    # QR steps (6, 9, 12) use branching (if_pass/if_fail)
    if step in (6, 9, 12):
        base_cmd = f"python3 -m {MODULE_PATH} --step {next_step} --total-steps {total_steps}"
        return {
            "title": step_info["title"],
            "actions": actions,
            "if_pass": f"{base_cmd} --qr-status pass",
            "if_fail": f"{base_cmd} --qr-status fail",
        }
    else:
        # Non-QR steps use simple next command
        next_cmd = f"python3 -m {MODULE_PATH} --step {next_step} --total-steps {total_steps}"
        return {
            "title": step_info["title"],
            "actions": actions,
            "next": next_cmd,
        }


def get_step_guidance(step: int, total_steps: int,
                      qr_iteration: int = 1, qr_fail: bool = False,
                      qr_status: str = None) -> dict | str:
    """Returns guidance for a step."""

    status = QRStatus(qr_status) if qr_status else None
    state = LoopState.RETRY if qr_fail else LoopState.INITIAL
    qr = QRState(iteration=qr_iteration, state=state, status=status)

    handler = STEP_HANDLERS.get(step)
    if handler:
        step_info = STEPS.get(step, {})
        result = handler(step_info=step_info, step=step, qr=qr, total_steps=total_steps,
                        qr_iteration=qr_iteration, qr_fail=qr_fail, qr_status=qr_status)
        if isinstance(result, str):
            return result
        if result is not None:
            return result
        if not qr_status and step in (7, 10, 13):
            return {"error": f"--qr-status required for gate step {step}"}

    info = STEPS.get(step)
    if not info:
        return {"error": f"Invalid step {step}"}

    # Use generic handler for non-special steps
    return generic_step_handler(info, step, total_steps, qr=qr, qr_fail=qr_fail,
                                qr_iteration=qr_iteration, qr_status=qr_status)


def format_output(step: int, total_steps: int,
                  qr_iteration: int, qr_fail: bool, qr_status: str) -> str:
    """Format output for display using XML format."""
    guidance = get_step_guidance(step, total_steps, qr_iteration, qr_fail, qr_status)

    # Gate steps return string directly (already XML formatted)
    if isinstance(guidance, str):
        return guidance

    # Handle error case
    if "error" in guidance:
        return f"Error: {guidance['error']}"

    # Build step output using W.* API
    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(guidance["title"]),
            script="planner", step=str(step), total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        parts.append("""<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>
3. The <next> block re-states the command -- execute it
4. For branching <invoke_after>, choose based on outcome:
   - <if_pass>: Use when action succeeded / QR returned PASS
   - <if_fail>: Use when action failed / QR returned ISSUES

DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
</xml_format_mandate>""")
        parts.append("")
        parts.append("""<output_efficiency>
Keep each thinking step to 5 words max. Use notation:
  -> for implies
  | for alternatives
  ; for sequence

Example: "QR failed -> route step 8 | iteration++"
</output_efficiency>""")
        parts.append("")

    # Check if there's a next command
    next_cmd = guidance.get("next")
    if_pass = guidance.get("if_pass")
    if_fail = guidance.get("if_fail")

    if next_cmd or (if_pass and if_fail):
        parts.append("<workflow>")

    # Current action
    action_nodes = [TextNode(a) for a in guidance["actions"]]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    # Invoke after
    if if_pass and if_fail:
        from skills.lib.workflow.ast.nodes import ElementNode
        if_pass_node = ElementNode("if_pass", {}, [TextNode(if_pass)])
        if_fail_node = ElementNode("if_fail", {}, [TextNode(if_fail)])
        parts.append(render(W.el("invoke_after", if_pass_node, if_fail_node).build(), XMLRenderer()))
        parts.append("")
        parts.append(render(
            W.el("next",
                TextNode("After current_action completes, execute invoke_after."),
                TextNode(f"Re-read now: if_pass -> {if_pass}"),
                TextNode(f"            if_fail -> {if_fail}"),
                required="true"
            ).build(),
            XMLRenderer()
        ))
        parts.append("</workflow>")
    elif next_cmd:
        parts.append(render(W.el("invoke_after", TextNode(next_cmd)).build(), XMLRenderer()))
        parts.append("")
        parts.append(render(
            W.el("next",
                TextNode("After current_action completes, execute invoke_after."),
                TextNode(f"Re-read now: {next_cmd}"),
                required="true"
            ).build(),
            XMLRenderer()
        ))
        parts.append("</workflow>")

    return "\n".join(parts)


def main(
    step: int = None,
    total_steps: int = None,
    qr_iteration: int = 1,
    qr_fail: bool = False,
    qr_status: str = None,
):
    """Backward compatibility CLI entry point.

    Note: Parameters have defaults because actual values come from argparse.
    The annotations are metadata for the testing framework.
    """
    parser = argparse.ArgumentParser(
        description="Interactive Sequential Planner (13-step unified workflow)",
        epilog="Steps 1-5: planning | Steps 6-13: review with QR gates",
    )

    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    add_qr_args(parser)

    args = parser.parse_args()

    if args.step < 1 or args.total_steps < 1:
        sys.exit("Error: step and total-steps must be >= 1")

    if args.total_steps < 13:
        sys.exit("Error: workflow requires at least 13 steps")

    # Gate steps require --qr-status; provide helpful output if missing
    if args.step in (7, 10, 13) and not args.qr_status:
        gate = GATES[args.step]
        print(f"PLANNER - Step {args.step}/{args.total_steps}: {gate.qr_name} Gate")
        print()
        print("This is a gate step. Re-invoke with --qr-status pass or --qr-status fail")
        print("based on the QR output from the previous step.")
        sys.exit(0)

    print(format_output(args.step, args.total_steps,
                        args.qr_iteration, args.qr_fail, args.qr_status))


if __name__ == "__main__":
    main()
