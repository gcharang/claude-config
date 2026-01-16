#!/usr/bin/env python3
"""
Plan Executor - Execute approved plans through delegation.

Nine-step workflow:
  1. Execution Planning - analyze plan, build wave list
  2. Reconciliation - validate existing code (conditional)
  3. Implementation - dispatch developers (wave-aware parallel)
  4. Code QR - verify code quality (RULE 0/1/2)
  5. Code QR Gate - route pass/fail
  6. Documentation - TW pass
  7. Doc QR - verify documentation quality
  8. Doc QR Gate - route pass/fail
  9. Retrospective - present summary
"""

import argparse
import sys

from skills.lib.workflow.types import QRState, QRStatus, GateConfig, AgentRole, LoopState
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.workflow.cli import add_qr_args
from skills.planner.shared.resources import get_mode_script_path


# Module path for -m invocation
MODULE_PATH = "skills.planner.executor"


STEPS = {
    1: {
        "title": "Execution Planning",
        "actions": [
            "Plan file: $PLAN_FILE (substitute from context)",
            "",
            "ANALYZE plan:",
            "  - Count milestones and parse dependency diagram",
            "  - Group milestones into WAVES for execution",
            "  - Set up TodoWrite tracking",
            "",
            "WAVE ANALYSIS:",
            "  Parse the plan's 'Milestone Dependencies' diagram.",
            "  Group into waves: milestones at same depth = one wave.",
            "",
            "  Example diagram:",
            "    M0 (foundation)",
            "     |",
            "     +---> M1 (auth)     \\",
            "     |                    } Wave 2 (parallel)",
            "     +---> M2 (users)    /",
            "     |",
            "     +---> M3 (posts) ----> M4 (feed)",
            "            Wave 3          Wave 4",
            "",
            "  Output format:",
            "    Wave 1: [0]       (foundation, sequential)",
            "    Wave 2: [1, 2]    (parallel)",
            "    Wave 3: [3]       (sequential)",
            "    Wave 4: [4]       (sequential)",
            "",
            "WORKFLOW:",
            "  This step is ANALYSIS ONLY. Do NOT delegate yet.",
            "  Record wave groupings for step 3 (Implementation).",
        ],
    },
    2: {
        "title": "Reconciliation",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/reconciliation.py",
        "mode_total_steps": 4,
        "context_vars": {
            "PLAN_FILE": "path to the plan being executed",
            "N": "milestone number (run once per milestone)",
        },
        "invoke_suffix": " --milestone N",
        "pre_dispatch": [
            "Validate existing code against plan requirements BEFORE executing.",
            "",
            "For EACH milestone, launch quality-reviewer agent:",
        ],
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: SATISFIED | NOT_SATISFIED | PARTIALLY_SATISFIED",
        ],
        "routing": {
            "SATISFIED": "Mark milestone complete, skip execution",
            "NOT_SATISFIED": "Execute milestone normally",
            "PARTIALLY_SATISFIED": "Execute only missing parts",
        },
        "extra_instructions": [
            "",
            "Parallel execution: May run reconciliation for multiple milestones",
            "in parallel (multiple Task calls in single response) when milestones",
            "are independent.",
        ],
    },
    3: {
        "title": "Implementation",
        # Handled specially in format_output - has normal and fix modes
    },
    4: {
        "title": "Code QR",
        "is_qr": True,
        "qr_name": "CODE QR",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/post-impl-code.py",
        "mode_total_steps": 5,
        "context_vars": {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from all milestones",
        },
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES (XML grouped by milestone).",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "developer"},
    },
    # Step 5 is the Code QR gate - handled separately
    6: {
        "title": "Documentation",
        # Handled specially in format_output - has normal and fix modes
    },
    7: {
        "title": "Doc QR",
        "is_qr": True,
        "qr_name": "DOC QR",
        "is_dispatch": True,
        "dispatch_agent": "quality-reviewer",
        "mode_script": "qr/post-impl-doc.py",
        "mode_total_steps": 4,
        "context_vars": {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
        },
        "post_dispatch": [
            "The sub-agent will invoke the script and follow its guidance.",
            "",
            "Expected output: PASS or ISSUES.",
        ],
        "post_qr_routing": {"self_fix": False, "fix_target": "technical-writer"},
    },
    # Step 8 is the Doc QR gate - handled separately
    9: {
        "title": "Retrospective",
        "actions": [
            "PRESENT retrospective to user (do not write to file):",
            "",
            "EXECUTION RETROSPECTIVE",
            "=======================",
            "Plan: [path]",
            "Status: COMPLETED | BLOCKED | ABORTED",
            "",
            "Milestone Outcomes: | Milestone | Status | Notes |",
            "Reconciliation Summary: [if run]",
            "Plan Accuracy Issues: [if any]",
            "Deviations from Plan: [if any]",
            "Quality Review Summary: [counts by category]",
            "Feedback for Future Plans: [actionable suggestions]",
        ],
    },
}


# Gate configuration for step 5 (Code QR Gate)
CODE_QR_GATE = GateConfig(
    qr_name="Code QR",
    work_step=3,
    pass_step=6,
    pass_message="Code quality verified. Proceed to documentation.",
    self_fix=False,
    fix_target=AgentRole.DEVELOPER,
)

# Gate configuration for step 8 (Doc QR Gate)
DOC_QR_GATE = GateConfig(
    qr_name="Doc QR",
    work_step=6,
    pass_step=9,
    pass_message="Documentation verified. Proceed to retrospective.",
    self_fix=False,
    fix_target=AgentRole.TECHNICAL_WRITER,
)


def format_gate(step: int, gate: GateConfig, qr: QRState, total_steps: int) -> str:
    """Format gate step output using W.* API."""
    from skills.lib.workflow.constants import QR_ITERATION_LIMIT, get_blocking_severities

    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(f"{gate.qr_name} Gate"),
            script="executor", step=str(step), total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # Gate result
    if qr.passed:
        parts.append('<gate_result status="pass">GATE PASSED</gate_result>')
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
        # Build fail actions similar to planner.py format_gate
        actions.append("<pedantic_enforcement>")
        actions.append("QR exists to catch problems BEFORE they reach production.")
        actions.append("See <severity_filter> below for which severities block at this iteration.")
        actions.append("</pedantic_enforcement>")
        actions.append("")

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
        next_cmd = f"python3 -m {MODULE_PATH} --step {gate.pass_step} --total-steps {total_steps}"
    else:
        next_iteration = qr.iteration + 1
        next_cmd = f"python3 -m {MODULE_PATH} --step {gate.work_step} --total-steps {total_steps} --qr-fail --qr-iteration {next_iteration}"

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


def format_step_3_implementation(qr: QRState, total_steps: int, milestone_count: int) -> str:
    """Format step 3 implementation output."""
    parts = []

    # Step header
    if qr.state == LoopState.RETRY:
        parts.append(render(
            W.el("step_header", TextNode("Implementation - Fix Mode"),
                script="executor", step="3", total=str(total_steps)
            ).build(),
            XMLRenderer()
        ))
    else:
        parts.append(render(
            W.el("step_header", TextNode("Implementation"),
                script="executor", step="3", total=str(total_steps)
            ).build(),
            XMLRenderer()
        ))
    parts.append("")

    parts.append("<workflow>")

    actions = []
    if qr.state == LoopState.RETRY:
        # Fix mode
        banner = render(W.el("state_banner", checkpoint="IMPLEMENTATION FIX", iteration=str(qr.iteration), mode="fix").build(), XMLRenderer())
        actions.append(banner)
        actions.append("")
        actions.append("FIX MODE: Code QR found issues.")
        actions.append("")

        constraint = render(
            W.el(
                "orchestrator_constraint",
                TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
                TextNode("Your agents are highly capable. Trust them with ANY issue."),
                TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
            ).build(),
            XMLRenderer(),
        )
        actions.append(constraint)
        actions.append("")

        # Build dispatch inline (free-form mode)
        context_vars = {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
            "QR_REPORT_PATH": "exact path from QR output",
        }
        dispatch_lines = ['<subagent_dispatch agent="developer" mode="free-form">']
        dispatch_lines.append("  <context>")
        for name, description in context_vars.items():
            dispatch_lines.append(f'    <var name="{name}">{description}</var>')
        dispatch_lines.append("  </context>")
        dispatch_lines.append("  <free_form_instruction>")
        dispatch_lines.append("    Do NOT include script invocation in your prompt.")
        dispatch_lines.append("    Pass QR findings as context. The agent works in free-form mode.")
        dispatch_lines.append("  </free_form_instruction>")
        dispatch_lines.append("  <qr_report_passthrough>")
        dispatch_lines.append("    CRITICAL: Include QR_REPORT_PATH verbatim in your Task prompt.")
        dispatch_lines.append("    DO NOT read QR_REPORT_PATH yourself.")
        dispatch_lines.append("    DO NOT extract, summarize, or interpret the issues.")
        dispatch_lines.append("    The sub-agent reads the file directly.")
        dispatch_lines.append("  </qr_report_passthrough>")
        dispatch_lines.append("</subagent_dispatch>")
        actions.append("\n".join(dispatch_lines))
        actions.append("")
        actions.append("Developer reads QR report and fixes issues in <milestone> blocks.")
        actions.append("After developer completes, re-run Code QR for fresh verification.")
    else:
        # Normal mode
        constraint = render(
            W.el(
                "orchestrator_constraint",
                TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
                TextNode("Your agents are highly capable. Trust them with ANY issue."),
                TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
            ).build(),
            XMLRenderer(),
        )
        actions.extend([
            "Execute ALL milestones using wave-aware parallel dispatch.",
            "",
            "WAVE-AWARE EXECUTION:",
            "  - Milestones within same wave: dispatch in PARALLEL",
            "    (Multiple Task calls in single response)",
            "  - Waves execute SEQUENTIALLY",
            "    (Wait for wave N to complete before starting wave N+1)",
            "",
            "Use waves identified in step 1.",
            "",
            constraint,
            "",
            "FOR EACH WAVE:",
            "  1. Dispatch developer agents for ALL milestones in wave:",
            "     Task(developer): Milestone N",
            "     Task(developer): Milestone M  (if parallel)",
            "",
            "  2. Each prompt must include:",
            "     - Plan file: $PLAN_FILE",
            "     - Milestone: [number and name]",
            "     - Files: [exact paths to create/modify]",
            "     - Acceptance criteria: [from plan]",
            "",
            "  3. Wait for ALL agents in wave to complete",
            "",
            "  4. Run tests: pytest / tsc / go test -race",
            "     Pass criteria: 100% tests pass, zero warnings",
            "",
            "  5. Proceed to next wave (repeat 1-4)",
            "",
            "After ALL waves complete, proceed to Code QR.",
            "",
            "ERROR HANDLING (you NEVER fix code yourself):",
            "  Clear problem + solution: Task(developer) immediately",
            "  Difficult/unclear problem: Task(debugger) to diagnose first",
            "  Uncertain how to proceed: AskUserQuestion with options",
        ])

    # Current action
    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    # Invoke after
    next_cmd = f"python3 -m {MODULE_PATH} --step 4 --total-steps {total_steps}"
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


def format_step_6_documentation(qr: QRState, total_steps: int) -> str:
    """Format step 6 documentation output."""
    mode_script = get_mode_script_path("tw/post-impl.py")
    parts = []

    # Step header
    if qr.state == LoopState.RETRY:
        parts.append(render(
            W.el("step_header", TextNode("Documentation - Fix Mode"),
                script="executor", step="6", total=str(total_steps)
            ).build(),
            XMLRenderer()
        ))
    else:
        parts.append(render(
            W.el("step_header", TextNode("Documentation"),
                script="executor", step="6", total=str(total_steps)
            ).build(),
            XMLRenderer()
        ))
    parts.append("")

    parts.append("<workflow>")

    actions = []
    constraint = render(
        W.el(
            "orchestrator_constraint",
            TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
            TextNode("Your agents are highly capable. Trust them with ANY issue."),
            TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
        ).build(),
        XMLRenderer(),
    )

    if qr.state == LoopState.RETRY:
        # Fix mode
        banner = render(W.el("state_banner", checkpoint="DOCUMENTATION FIX", iteration=str(qr.iteration), mode="fix").build(), XMLRenderer())
        actions.append(banner)
        actions.append("")
        actions.append("FIX MODE: Doc QR found issues.")
        actions.append("")
        actions.append(constraint)
        actions.append("")

        # Build dispatch inline (script mode with QR fix)
        invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps 6 --qr-fail --qr-iteration {qr.iteration}"
        context_vars = {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
            "QR_REPORT_PATH": "exact path from QR output",
        }
        dispatch_lines = ['<subagent_dispatch agent="technical-writer" mode="script">']
        dispatch_lines.append("  <context>")
        for name, description in context_vars.items():
            dispatch_lines.append(f'    <var name="{name}">{description}</var>')
        dispatch_lines.append("  </context>")
        dispatch_lines.append(f"  <invoke>{invoke_cmd}</invoke>")
        dispatch_lines.append("  <handoff_instruction>")
        dispatch_lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
        dispatch_lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
        dispatch_lines.append("  </handoff_instruction>")
        dispatch_lines.append("  <qr_report_passthrough>")
        dispatch_lines.append("    CRITICAL: Include QR_REPORT_PATH verbatim in your Task prompt.")
        dispatch_lines.append("    DO NOT read QR_REPORT_PATH yourself.")
        dispatch_lines.append("    DO NOT extract, summarize, or interpret the issues.")
        dispatch_lines.append("    The sub-agent reads the file directly.")
        dispatch_lines.append("  </qr_report_passthrough>")
        dispatch_lines.append("</subagent_dispatch>")
        actions.append("\n".join(dispatch_lines))
        actions.append("")
        actions.append("TW reads QR report and fixes documentation issues.")
        actions.append("After TW completes, re-run Doc QR for fresh verification.")
    else:
        # Normal mode
        actions.append(constraint)
        actions.append("")

        # Build dispatch inline (script mode)
        invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps 6"
        context_vars = {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
        }
        dispatch_lines = ['<subagent_dispatch agent="technical-writer" mode="script">']
        dispatch_lines.append("  <context>")
        for name, description in context_vars.items():
            dispatch_lines.append(f'    <var name="{name}">{description}</var>')
        dispatch_lines.append("  </context>")
        dispatch_lines.append(f"  <invoke>{invoke_cmd}</invoke>")
        dispatch_lines.append("  <handoff_instruction>")
        dispatch_lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
        dispatch_lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
        dispatch_lines.append("  </handoff_instruction>")
        dispatch_lines.append("</subagent_dispatch>")
        actions.append("\n".join(dispatch_lines))
        actions.append("")
        actions.append("The sub-agent will invoke the script and follow its guidance.")
        actions.append("")
        actions.append("Expected output: Documentation report format")
        actions.append("")
        actions.append("Skip if ALL milestones were documentation-only.")

    # Current action
    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    # Invoke after
    next_cmd = f"python3 -m {MODULE_PATH} --step 7 --total-steps {total_steps}"
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


def format_step_1_planning(qr: QRState, total_steps: int, reconciliation_check: bool, **kw) -> str:
    """Format step 1 planning output."""
    info = STEPS[1]
    parts = []

    parts.append(render(
        W.el("step_header", TextNode(info["title"]),
            script="executor", step="1", total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

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

    parts.append("<workflow>")

    actions = list(info["actions"])
    actions.extend([
        "",
        "=" * 70,
        "MANDATORY NEXT ACTION",
        "=" * 70,
    ])
    if reconciliation_check:
        next_command = f"python3 -m {MODULE_PATH} --step 2 --total-steps {total_steps} --reconciliation-check"
    else:
        actions.extend([
            "Proceed to Implementation step.",
            "Use the wave groupings from your analysis.",
            "=" * 70,
        ])
        next_command = f"python3 -m {MODULE_PATH} --step 3 --total-steps {total_steps}"

    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    parts.append(render(W.el("invoke_after", TextNode(next_command)).build(), XMLRenderer()))
    parts.append("")
    parts.append(render(
        W.el("next",
            TextNode("After current_action completes, execute invoke_after."),
            TextNode(f"Re-read now: {next_command}"),
            required="true"
        ).build(),
        XMLRenderer()
    ))
    parts.append("</workflow>")

    return "\n".join(parts)


def format_step_4_code_qr(qr: QRState, total_steps: int, **kw) -> str:
    """Format step 4 code QR output with branching."""
    info = STEPS[4]
    parts = []

    parts.append(render(
        W.el("step_header", TextNode(info["title"]),
            script="executor", step="4", total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    parts.append("<workflow>")

    actions = []
    banner = render(W.el("state_banner", checkpoint=info["qr_name"], iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
    actions.append(banner)
    actions.append("")

    pre_dispatch = info.get("pre_dispatch", [])
    actions.extend(pre_dispatch)

    constraint = render(
        W.el(
            "orchestrator_constraint",
            TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
            TextNode("Your agents are highly capable. Trust them with ANY issue."),
            TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
        ).build(),
        XMLRenderer(),
    )
    actions.append(constraint)
    actions.append("")

    mode_script = get_mode_script_path(info["mode_script"])
    mode_total_steps = info.get("mode_total_steps", 5)
    dispatch_agent = info.get("dispatch_agent", "agent")
    context_vars = info.get("context_vars", {})
    invoke_suffix = info.get("invoke_suffix", "")
    invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps {mode_total_steps}{invoke_suffix}"

    dispatch_lines = [f'<subagent_dispatch agent="{dispatch_agent}" mode="script">']
    if context_vars:
        dispatch_lines.append("  <context>")
        for name, description in context_vars.items():
            dispatch_lines.append(f'    <var name="{name}">{description}</var>')
        dispatch_lines.append("  </context>")
    dispatch_lines.append(f"  <invoke>{invoke_cmd}</invoke>")
    dispatch_lines.append("  <handoff_instruction>")
    dispatch_lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
    dispatch_lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
    dispatch_lines.append("  </handoff_instruction>")
    dispatch_lines.append("</subagent_dispatch>")
    actions.append("\n".join(dispatch_lines))
    actions.append("")

    post_dispatch = info.get("post_dispatch", [])
    actions.extend(post_dispatch)

    post_qr_config = info.get("post_qr_routing")
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
        actions.append(routing_block)

    routing = info.get("routing")
    if routing:
        from skills.lib.workflow.ast.nodes import ElementNode
        cases = [ElementNode("case", {"result": result}, [TextNode(action)]) for result, action in routing.items()]
        routing_block = render(W.el("routing", *cases).build(), XMLRenderer())
        actions.append("")
        actions.append(routing_block)

    extra_instructions = info.get("extra_instructions", [])
    actions.extend(extra_instructions)

    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    if_pass = f"python3 -m {MODULE_PATH} --step 5 --total-steps {total_steps} --qr-status pass"
    if_fail = f"python3 -m {MODULE_PATH} --step 5 --total-steps {total_steps} --qr-status fail"

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

    return "\n".join(parts)


def format_step_7_doc_qr(qr: QRState, total_steps: int, **kw) -> str:
    """Format step 7 doc QR output with branching."""
    info = STEPS[7]
    parts = []

    parts.append(render(
        W.el("step_header", TextNode(info["title"]),
            script="executor", step="7", total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    parts.append("<workflow>")

    actions = []
    banner = render(W.el("state_banner", checkpoint=info["qr_name"], iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
    actions.append(banner)
    actions.append("")

    pre_dispatch = info.get("pre_dispatch", [])
    actions.extend(pre_dispatch)

    constraint = render(
        W.el(
            "orchestrator_constraint",
            TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
            TextNode("Your agents are highly capable. Trust them with ANY issue."),
            TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
        ).build(),
        XMLRenderer(),
    )
    actions.append(constraint)
    actions.append("")

    mode_script = get_mode_script_path(info["mode_script"])
    mode_total_steps = info.get("mode_total_steps", 5)
    dispatch_agent = info.get("dispatch_agent", "agent")
    context_vars = info.get("context_vars", {})
    invoke_suffix = info.get("invoke_suffix", "")
    invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps {mode_total_steps}{invoke_suffix}"

    dispatch_lines = [f'<subagent_dispatch agent="{dispatch_agent}" mode="script">']
    if context_vars:
        dispatch_lines.append("  <context>")
        for name, description in context_vars.items():
            dispatch_lines.append(f'    <var name="{name}">{description}</var>')
        dispatch_lines.append("  </context>")
    dispatch_lines.append(f"  <invoke>{invoke_cmd}</invoke>")
    dispatch_lines.append("  <handoff_instruction>")
    dispatch_lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
    dispatch_lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
    dispatch_lines.append("  </handoff_instruction>")
    dispatch_lines.append("</subagent_dispatch>")
    actions.append("\n".join(dispatch_lines))
    actions.append("")

    post_dispatch = info.get("post_dispatch", [])
    actions.extend(post_dispatch)

    post_qr_config = info.get("post_qr_routing")
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
        actions.append(routing_block)

    routing = info.get("routing")
    if routing:
        from skills.lib.workflow.ast.nodes import ElementNode
        cases = [ElementNode("case", {"result": result}, [TextNode(action)]) for result, action in routing.items()]
        routing_block = render(W.el("routing", *cases).build(), XMLRenderer())
        actions.append("")
        actions.append(routing_block)

    extra_instructions = info.get("extra_instructions", [])
    actions.extend(extra_instructions)

    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    if_pass = f"python3 -m {MODULE_PATH} --step 8 --total-steps {total_steps} --qr-status pass"
    if_fail = f"python3 -m {MODULE_PATH} --step 8 --total-steps {total_steps} --qr-status fail"

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

    return "\n".join(parts)


STEP_HANDLERS = {
    1: format_step_1_planning,
    3: lambda qr, total_steps, milestone_count, **kw: format_step_3_implementation(qr, total_steps, milestone_count),
    4: format_step_4_code_qr,
    5: lambda qr, total_steps, qr_status, **kw: format_gate(5, CODE_QR_GATE, qr, total_steps) if qr_status else "Error: --qr-status required for step 5",
    6: lambda qr, total_steps, **kw: format_step_6_documentation(qr, total_steps),
    7: format_step_7_doc_qr,
    8: lambda qr, total_steps, qr_status, **kw: format_gate(8, DOC_QR_GATE, qr, total_steps) if qr_status else "Error: --qr-status required for step 8",
}


def format_output(step: int, total_steps: int,
                  qr_iteration: int, qr_fail: bool, qr_status: str,
                  reconciliation_check: bool, milestone_count: int) -> str:
    """Format output for display using XML format."""

    # Construct QRState from legacy parameters
    status = QRStatus(qr_status) if qr_status else None
    state = LoopState.RETRY if qr_fail else LoopState.INITIAL
    qr = QRState(iteration=qr_iteration, state=state, status=status)

    # Dispatch to step-specific handlers
    handler = STEP_HANDLERS.get(step)
    if handler:
        return handler(qr=qr, total_steps=total_steps, qr_status=qr_status,
                      milestone_count=milestone_count, reconciliation_check=reconciliation_check)

    # Generic step handling
    info = STEPS.get(step, STEPS[9])

    # Handle QR step in fix mode (developer/TW fixes, not QR re-run)
    if info.get("is_qr") and qr.state == LoopState.RETRY:
        post_qr_config = info.get("post_qr_routing", {})
        fix_target = post_qr_config.get("fix_target", "developer")
        qr_name = info.get("qr_name", "QR")

        parts = []

        # Step header
        parts.append(render(
            W.el("step_header", TextNode(f"{info['title']} - Fix Mode"),
                script="executor", step=str(step), total=str(total_steps)
            ).build(),
            XMLRenderer()
        ))
        parts.append("")

        parts.append("<workflow>")

        fix_actions = []
        banner = render(W.el("state_banner", checkpoint=qr_name, iteration=str(qr.iteration), mode="fix").build(), XMLRenderer())
        fix_actions.append(banner)
        fix_actions.append("")
        fix_actions.append(f"FIX MODE: {qr_name} found issues.")
        fix_actions.append("")

        constraint = render(
            W.el(
                "orchestrator_constraint",
                TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
                TextNode("Your agents are highly capable. Trust them with ANY issue."),
                TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
            ).build(),
            XMLRenderer(),
        )
        fix_actions.append(constraint)
        fix_actions.append("")

        # Build free-form dispatch inline
        context_vars = {
            "PLAN_FILE": "path to the executed plan",
            "MODIFIED_FILES": "actual file paths from milestones",
            "QR_REPORT_PATH": "exact path from QR output",
        }
        dispatch_lines = [f'<subagent_dispatch agent="{fix_target}" mode="free-form">']
        dispatch_lines.append("  <context>")
        for name, description in context_vars.items():
            dispatch_lines.append(f'    <var name="{name}">{description}</var>')
        dispatch_lines.append("  </context>")
        dispatch_lines.append("  <free_form_instruction>")
        dispatch_lines.append("    Do NOT include script invocation in your prompt.")
        dispatch_lines.append("    Pass QR findings as context. The agent works in free-form mode.")
        dispatch_lines.append("  </free_form_instruction>")
        dispatch_lines.append("  <qr_report_passthrough>")
        dispatch_lines.append("    CRITICAL: Include QR_REPORT_PATH verbatim in your Task prompt.")
        dispatch_lines.append("    DO NOT read QR_REPORT_PATH yourself.")
        dispatch_lines.append("    DO NOT extract, summarize, or interpret the issues.")
        dispatch_lines.append("    The sub-agent reads the file directly.")
        dispatch_lines.append("  </qr_report_passthrough>")
        dispatch_lines.append("</subagent_dispatch>")
        fix_actions.append("\n".join(dispatch_lines))
        fix_actions.append("")
        fix_actions.append(f"{fix_target.title()} reads QR report and fixes issues.")
        fix_actions.append(f"After {fix_target} completes, re-run {qr_name} for fresh verification.")

        action_nodes = [TextNode(a) for a in fix_actions]
        parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
        parts.append("")

        next_cmd = f"python3 -m {MODULE_PATH} --step {step} --total-steps {total_steps}"
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

    is_complete = step >= total_steps

    # Build actions
    actions = []

    # Add QR banner for QR steps using XML format
    if info.get("is_qr"):
        qr_name = info.get("qr_name", "QR")
        banner = render(W.el("state_banner", checkpoint=qr_name, iteration=str(qr.iteration), mode="fresh_review").build(), XMLRenderer())
        actions.append(banner)
        actions.append("")

    # Handle dispatch steps with new structure
    if info.get("is_dispatch"):
        # Add pre-dispatch instructions
        pre_dispatch = info.get("pre_dispatch", [])
        actions.extend(pre_dispatch)

        # Add orchestrator constraint before dispatch
        constraint = render(
            W.el(
                "orchestrator_constraint",
                TextNode("You are the ORCHESTRATOR. You delegate, you never implement."),
                TextNode("Your agents are highly capable. Trust them with ANY issue."),
                TextNode("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch."),
            ).build(),
            XMLRenderer(),
        )
        actions.append(constraint)
        actions.append("")

        # Generate dispatch block inline
        mode_script = get_mode_script_path(info["mode_script"])
        mode_total_steps = info.get("mode_total_steps", 5)
        dispatch_agent = info.get("dispatch_agent", "agent")
        context_vars = info.get("context_vars", {})
        invoke_suffix = info.get("invoke_suffix", "")
        invoke_cmd = f"python3 -m {mode_script} --step 1 --total-steps {mode_total_steps}{invoke_suffix}"

        dispatch_lines = [f'<subagent_dispatch agent="{dispatch_agent}" mode="script">']
        if context_vars:
            dispatch_lines.append("  <context>")
            for name, description in context_vars.items():
                dispatch_lines.append(f'    <var name="{name}">{description}</var>')
            dispatch_lines.append("  </context>")
        dispatch_lines.append(f"  <invoke>{invoke_cmd}</invoke>")
        dispatch_lines.append("  <handoff_instruction>")
        dispatch_lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
        dispatch_lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
        dispatch_lines.append("  </handoff_instruction>")
        dispatch_lines.append("</subagent_dispatch>")
        actions.append("\n".join(dispatch_lines))
        actions.append("")

        # Add post-dispatch instructions
        post_dispatch = info.get("post_dispatch", [])
        actions.extend(post_dispatch)

        # Add post-QR routing block for QR steps
        post_qr_config = info.get("post_qr_routing")
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
            actions.append(routing_block)

        # Add routing block if present
        routing = info.get("routing")
        if routing:
            from skills.lib.workflow.ast.nodes import ElementNode
            cases = [ElementNode("case", {"result": result}, [TextNode(action)]) for result, action in routing.items()]
            routing_block = render(W.el("routing", *cases).build(), XMLRenderer())
            actions.append("")
            actions.append(routing_block)

        # Add extra instructions if present
        extra_instructions = info.get("extra_instructions", [])
        actions.extend(extra_instructions)
    elif "actions" in info:
        # Non-dispatch step with explicit actions
        actions.extend(info["actions"])

    # Build next command(s)
    next_command = None
    if_pass = None
    if_fail = None

    if is_complete:
        # Final step - no invoke_after, just present retrospective
        actions.append("")
        actions.append("EXECUTION COMPLETE - Present retrospective to user.")
    else:
        next_command = f"python3 -m {MODULE_PATH} --step {step + 1} --total-steps {total_steps}"

    # Build step output using W.* API
    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(info["title"]),
            script="executor", step=str(step), total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # Check if there's a next command
    if next_command or (if_pass and if_fail):
        parts.append("<workflow>")

    # Current action
    action_nodes = [TextNode(a) for a in actions]
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
    elif next_command:
        parts.append(render(W.el("invoke_after", TextNode(next_command)).build(), XMLRenderer()))
        parts.append("")
        parts.append(render(
            W.el("next",
                TextNode("After current_action completes, execute invoke_after."),
                TextNode(f"Re-read now: {next_command}"),
                required="true"
            ).build(),
            XMLRenderer()
        ))
        parts.append("</workflow>")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Plan Executor - Execute approved plans",
        epilog="Steps: plan -> reconcile -> implement -> code QR -> gate -> docs -> doc QR -> gate -> retrospective",
    )

    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    add_qr_args(parser)
    parser.add_argument("--reconciliation-check", action="store_true")
    parser.add_argument("--milestone-count", type=int, default=0)

    args = parser.parse_args()

    if args.step < 1 or args.step > 9:
        sys.exit("Error: step must be 1-9")

    if args.step == 5 and not args.qr_status:
        sys.exit("Error: --qr-status required for step 5")

    if args.step == 8 and not args.qr_status:
        sys.exit("Error: --qr-status required for step 8")

    print(format_output(args.step, args.total_steps,
                        args.qr_iteration, args.qr_fail, args.qr_status,
                        args.reconciliation_check, args.milestone_count))


if __name__ == "__main__":
    main()
