"""XML formatting functions for workflow scripts.

COMPOSITION PATTERN:

The workflow framework uses a two-layer composition model for XML output:

1. GUIDANCE LAYER: Functions return dicts with typed fields
   - get_step_*_guidance() -> {"title": str, "actions": list[str], "next": str, ...}
   - Actions list contains both plain strings AND XML blocks (from formatters)

2. RENDERING LAYER: format_step_output() assembles final XML
   - Takes dict fields as parameters
   - Calls smaller XML formatters (format_step_header, format_current_action, etc.)
   - Returns complete XML string via list + "\n".join() pattern

COMPOSABILITY:
  actions = [
      format_state_banner(...),    # Returns XML string
      "",                          # Blank line (plain string)
      "TASK: Do something",        # Plain string
      format_forbidden([...]),     # Returns XML string
  ]
  This mixing works because all formatters return strings.

ADDING NEW XML ELEMENTS:
  1. Create format_*() function that returns XML string via list+join
  2. Call it within actions list: actions.append(format_new_element(...))
  3. If element belongs outside <current_action>, add parameter to format_step_output()
"""

from skills.lib.workflow.types import (
    QRState,
    QRStatus,
    GateConfig,
    FlatCommand,
    BranchCommand,
    NextCommand,
)
from skills.lib.workflow.formatters.builder import wrap_xml
from skills.lib.workflow.constants import QR_ITERATION_LIMIT, get_blocking_severities


# =============================================================================
# Core XML Formatters
# =============================================================================


def format_step_header(
    script: str,
    step: int,
    total: int,
    title: str,
    phase: str = None,
) -> str:
    """Render the <step_header> XML tag.

    Args:
        script: Script name without .py (e.g., "planner", "plan-completeness")
        step: Current step number (1-indexed)
        total: Total steps in workflow
        title: Human-readable step title
        phase: Optional phase (e.g., "planning", "review") for planner.py

    Returns:
        XML string: <step_header script="..." step="..." total="...">Title</step_header>
    """
    attrs = [f'script="{script}"']
    if phase:
        attrs.append(f'phase="{phase}"')
    attrs.append(f'step="{step}"')
    attrs.append(f'total="{total}"')
    return f'<step_header {" ".join(attrs)}>{title}</step_header>'


def format_current_action(actions: list[str]) -> str:
    """Render the <current_action> XML block.

    Args:
        actions: List of action strings (empty strings become blank lines)

    Returns:
        XML string: <current_action>...</current_action>
    """
    return wrap_xml("current_action", *actions)


def format_invoke_after(cmd: NextCommand) -> str:
    """Render the <invoke_after> XML block.

    Args:
        cmd: Routing command - FlatCommand, BranchCommand, or None

    Returns:
        XML string: <invoke_after>...</invoke_after>, or empty string if None
    """
    if cmd is None:
        return ""
    if isinstance(cmd, BranchCommand):
        return wrap_xml(
            "invoke_after",
            f"<if_pass>{cmd.if_pass}</if_pass>",
            f"<if_fail>{cmd.if_fail}</if_fail>",
        )
    return wrap_xml("invoke_after", cmd.command)


def format_next_block(cmd: NextCommand) -> str:
    """Render the <next required="true"> block with RE2 pattern.

    This block appears after <invoke_after> to reinforce the execution requirement
    using the RE2 (Re-Reading) technique for improved instruction following.

    Args:
        cmd: Routing command - FlatCommand, BranchCommand, or None

    Returns:
        XML string with RE2-enhanced execution reminder, or empty string if None
    """
    if cmd is None:
        return ""
    if isinstance(cmd, BranchCommand):
        return wrap_xml(
            "next",
            "After current_action completes, execute invoke_after.",
            f"Re-read now: if_pass -> {cmd.if_pass}",
            f"            if_fail -> {cmd.if_fail}",
            required="true",
        )
    return wrap_xml(
        "next",
        "After current_action completes, execute invoke_after.",
        f"Re-read now: {cmd.command}",
        required="true",
    )


def format_gate_result(status: str, message: str) -> str:
    """Render the <gate_result> XML block for gate steps.

    Args:
        status: "pass" or "fail"
        message: Gate result message (e.g., "GATE PASSED", "GATE FAILED (iteration 2)")

    Returns:
        XML string: <gate_result status="...">...</gate_result>
    """
    return f'<gate_result status="{status}">{message}</gate_result>'


def format_xml_mandate() -> str:
    """Return first-step guidance about XML format requirement.

    This is injected into step 1 of every script to teach agents the format.

    Returns:
        XML mandate block as string
    """
    return """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>
3. The <next> block re-states the command -- execute it
4. For branching <invoke_after>, choose based on outcome:
   - <if_pass>: Use when action succeeded / QR returned PASS
   - <if_fail>: Use when action failed / QR returned ISSUES

DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
</xml_format_mandate>"""


def format_step_output(
    script: str,
    step: int,
    total: int,
    title: str,
    actions: list[str],
    next_command: str = None,
    phase: str = None,
    if_pass: str = None,
    if_fail: str = None,
    is_step_one: bool = False,
    gate_result: tuple[str, str] = None,
) -> str:
    """Combine all XML parts into complete step output.

    Args:
        script: Script name without .py
        step: Current step number
        total: Total steps in workflow
        title: Step title
        actions: List of action strings
        next_command: Flat command for non-branching (mutually exclusive with if_pass/if_fail)
        phase: Optional phase for planner.py
        if_pass: Command if QR passes (for branching)
        if_fail: Command if QR fails (for branching)
        is_step_one: If True, prepend XML mandate to actions
        gate_result: Optional (status, message) tuple for gate steps (e.g., ("pass", "GATE PASSED"))

    Returns:
        Complete formatted output string
    """
    parts = []

    # Step header
    parts.append(format_step_header(script, step, total, title, phase))
    parts.append("")

    # XML mandate for step 1
    if is_step_one:
        parts.append(format_xml_mandate())
        parts.append("")

    # Gate result (for gate steps)
    if gate_result:
        status, message = gate_result
        parts.append(format_gate_result(status, message))
        parts.append("")

    # Convert legacy params to NextCommand
    cmd: NextCommand = None
    if if_pass and if_fail:
        cmd = BranchCommand(if_pass=if_pass, if_fail=if_fail)
    elif next_command:
        cmd = FlatCommand(command=next_command)

    # Wrap workflow elements when there's a next command
    if cmd:
        parts.append("<workflow>")

    # Current action
    parts.append(format_current_action(actions))
    parts.append("")

    # Invoke after and next block
    invoke_after = format_invoke_after(cmd)
    if invoke_after:
        parts.append(invoke_after)
        parts.append("")
        parts.append(format_next_block(cmd))
        parts.append("</workflow>")

    return "\n".join(parts)


# =============================================================================
# Extended XML Formatters
# =============================================================================


def format_subagent_dispatch(
    agent: str,
    context_vars: dict[str, str],
    invoke_cmd: str,
    free_form: bool = False,
    qr_fix_mode: bool = False,
) -> str:
    """Render the <subagent_dispatch> XML block for agent delegation.

    Args:
        agent: Agent type to dispatch to (e.g., "quality-reviewer", "developer")
        context_vars: Dict of variable name -> description for substitution
        invoke_cmd: The command the sub-agent should run (with $VAR placeholders)
        free_form: If True, dispatch in free-form mode (no script invocation)
        qr_fix_mode: If True, inject QR_REPORT_PATH and add passthrough guidance

    Returns:
        XML string: <subagent_dispatch agent="...">...</subagent_dispatch>

    Example:
        format_subagent_dispatch(
            "quality-reviewer",
            {"PLAN_FILE": "path to plan", "MODIFIED_FILES": "list of files"},
            "python3 $MODE_SCRIPT --step 1 --total-steps 5"
        )
    """
    # When in fix mode, inject QR_REPORT_PATH into context_vars
    if qr_fix_mode:
        context_vars = dict(context_vars)  # copy to avoid mutation
        context_vars["QR_REPORT_PATH"] = "exact path from QR output"

    mode = "free-form" if free_form else "script"
    lines = [f'<subagent_dispatch agent="{agent}" mode="{mode}">']
    if context_vars:
        lines.append("  <context>")
        for name, description in context_vars.items():
            lines.append(f'    <var name="{name}">{description}</var>')
        lines.append("  </context>")
    if free_form:
        lines.append("  <free_form_instruction>")
        lines.append("    Do NOT include script invocation in your prompt.")
        lines.append("    Pass QR findings as context. The agent works in free-form mode.")
        lines.append("  </free_form_instruction>")
    else:
        lines.append(f"  <invoke>{invoke_cmd}</invoke>")
        lines.append("  <handoff_instruction>")
        lines.append(f'    Your Task tool prompt MUST begin with: "Start by invoking: {invoke_cmd}"')
        lines.append("    This is MANDATORY. The sub-agent follows the script, not free-form instructions.")
        lines.append("  </handoff_instruction>")
    # Add passthrough guidance when in fix mode
    if qr_fix_mode:
        lines.append("  <qr_report_passthrough>")
        lines.append("    CRITICAL: Include QR_REPORT_PATH verbatim in your Task prompt.")
        lines.append("    DO NOT read QR_REPORT_PATH yourself.")
        lines.append("    DO NOT extract, summarize, or interpret the issues.")
        lines.append("    The sub-agent reads the file directly.")
        lines.append("  </qr_report_passthrough>")
    lines.append("</subagent_dispatch>")
    return "\n".join(lines)


def format_state_banner(
    checkpoint: str,
    iteration: int,
    mode: str,
    explanation: list[str] = None,
) -> str:
    """Render the <state_banner> XML element for QR verification loops.

    Args:
        checkpoint: Name of the checkpoint (e.g., "QR-COMPLETENESS", "HOLISTIC QR")
        iteration: Loop iteration count (1 = initial, 2+ = re-verification)
        mode: Either "initial_review" or "re_verification"
        explanation: Optional list of explanation lines for re-verification

    Returns:
        XML string: <state_banner checkpoint="..." iteration="..." mode="...">
    """
    lines = [f'<state_banner checkpoint="{checkpoint}" iteration="{iteration}" mode="{mode}">']
    if explanation:
        for line in explanation:
            lines.append(line)
    lines.append("</state_banner>")
    return "\n".join(lines)


def format_qr_banner(checkpoint: str, qr: QRState) -> str:
    """Generate QR state banner with automatic mode selection.

    Every iteration uses fresh_review mode to avoid confirmation bias.
    Research shows "verify previous fixes" framing biases toward confirming
    rather than discovering issues. Each QR pass should be a clean slate.

    Args:
        checkpoint: QR checkpoint name (e.g., "QR-COMPLETENESS")
        qr: QR loop state

    Returns:
        Formatted state banner XML string
    """
    # Always use fresh_review - no biased "verify fixes" framing
    return format_state_banner(checkpoint, qr.iteration, "fresh_review")


def format_expected_output(
    if_pass: str,
    if_issues: str = None,
    categories: list[str] = None,
) -> str:
    """Render the <expected_output> XML block for mode script final steps.

    Args:
        if_pass: Output format when no issues found
        if_issues: Output format template when issues found
        categories: Optional list of issue categories for guidance

    Returns:
        XML string: <expected_output>...</expected_output>
    """
    lines = ["<expected_output>"]
    lines.append(f"  <if_pass>{if_pass}</if_pass>")
    if if_issues:
        lines.append("  <if_issues>")
        lines.append(if_issues)
        lines.append("  </if_issues>")
    if categories:
        lines.append("  <categories>")
        for cat in categories:
            lines.append(f"    <category>{cat}</category>")
        lines.append("  </categories>")
    lines.append("</expected_output>")
    return "\n".join(lines)


def format_forbidden(actions: list[str]) -> str:
    """Render the <forbidden> XML block for prohibited actions.

    Args:
        actions: List of prohibited action descriptions

    Returns:
        XML string: <forbidden>...</forbidden>
    """
    lines = ["<forbidden>"]
    for action in actions:
        lines.append(f"  <action>{action}</action>")
    lines.append("</forbidden>")
    return "\n".join(lines)


def format_routing(cases: dict[str, str]) -> str:
    """Render the <routing> XML block for conditional logic.

    Args:
        cases: Dict of result value -> action description

    Returns:
        XML string: <routing>...</routing>
    """
    lines = ["<routing>"]
    for result, action in cases.items():
        lines.append(f'  <case result="{result}">{action}</case>')
    lines.append("</routing>")
    return "\n".join(lines)


def format_post_qr_routing(self_fix: bool = False, fix_target: str = "developer") -> str:
    """Render the <post_qr_routing> XML block for QR dispatch steps.

    This block appears WITHIN <current_action> to ensure the orchestrator
    sees routing instructions alongside dispatch instructions. It addresses
    the failure mode where orchestrator acts on QR findings instead of
    invoking the gate step.

    Args:
        self_fix: If True, orchestrator fixes issues directly (plan structure).
                  If False, orchestrator delegates to sub-agent in free-form mode.
        fix_target: Agent to delegate to (ignored if self_fix=True)

    Returns:
        XML string with routing table and forbidden actions
    """
    lines = ["", "<post_qr_routing>"]
    lines.append("<role>You are the ORCHESTRATOR. After QR returns, your ONLY action is routing.</role>")
    lines.append("")
    lines.append("<pedantic_mode>")
    lines.append("EVERY issue is blocking. There are no 'minor concerns' or 'non-critical issues'.")
    lines.append("If QR returns ANYTHING other than clean PASS, route to <if_fail>.")
    lines.append(f"Defense: Max {QR_ITERATION_LIMIT} iterations, then escalate to user via AskUserQuestion.")
    lines.append("</pedantic_mode>")
    lines.append("")
    lines.append("<routing_table>")
    lines.append("| QR Result              | Your Action                         |")
    lines.append("| ---------------------- | ----------------------------------- |")
    lines.append("| PASS (no issues)       | Invoke command from <if_pass> below |")
    lines.append("| ISSUES / concerns / *  | Invoke command from <if_fail> below |")
    lines.append("</routing_table>")
    lines.append("")
    lines.append("<forbidden>")
    lines.append("Reading files to 'understand' the issues -- gate step handles this")
    lines.append("Interpreting 'concerns' as non-blocking -- ALL issues block")
    lines.append("Using your judgment to skip issues -- QR is pedantic by design")
    if self_fix:
        lines.append("Delegating to sub-agents -- plan structure is YOUR responsibility")
    else:
        lines.append(f"Using Edit/Write tools -- delegate to {fix_target} instead")
        lines.append("Fixing code/docs yourself -- you orchestrate, sub-agents implement")
    lines.append("Skipping the gate step -- it decides next action based on QR result")
    lines.append("</forbidden>")
    lines.append("</post_qr_routing>")
    return "\n".join(lines)


def format_resource(name: str, purpose: str, content: str) -> str:
    """Render the <resource> XML block for injected reference content.

    Args:
        name: Resource identifier (e.g., "default-conventions")
        purpose: Why this resource is being injected (e.g., "policy-defaults")
        content: The full resource content

    Returns:
        XML string: <resource name="..." purpose="...">...</resource>
    """
    lines = [f'<resource name="{name}" purpose="{purpose}">']
    lines.append(content)
    lines.append("</resource>")
    return "\n".join(lines)


def format_detection_questions(
    category: str,
    questions: list[dict[str, str]],
) -> str:
    """Render the <detection_questions> XML block for factored verification.

    Args:
        category: Category name (e.g., "temporal-contamination")
        questions: List of dicts with "id" and "text" keys

    Returns:
        XML string: <detection_questions>...</detection_questions>
    """
    lines = [f'<detection_questions category="{category}">']
    for q in questions:
        qid = q.get("id", "")
        text = q.get("text", "")
        lines.append(f'  <question id="{qid}">{text}</question>')
    lines.append("</detection_questions>")
    return "\n".join(lines)


def format_verification_checklist(
    name: str,
    checks: list[dict[str, str]],
) -> str:
    """Render the <verification_checklist> XML block.

    Args:
        name: Checklist identifier (e.g., "plan-structure", "code-presence")
        checks: List of dicts with keys: element, criterion, if_missing

    Returns:
        XML string: <verification_checklist>...</verification_checklist>
    """
    lines = [f'<verification_checklist name="{name}">']
    for check in checks:
        element = check.get("element", "")
        criterion = check.get("criterion", "")
        if_missing = check.get("if_missing", "")
        lines.append(
            f'  <check element="{element}" criterion="{criterion}" '
            f'if_missing="{if_missing}" />'
        )
    lines.append("</verification_checklist>")
    return "\n".join(lines)


def format_incorrect_behavior(
    description: str,
    consequence: str,
) -> str:
    """Render the <incorrect_behavior> XML block for anti-pattern examples.

    Use after format_forbidden() to show concrete example of what to avoid.
    Research: Contrastive examples (+9.8 to +16.0 points on reasoning tasks).

    Args:
        description: What the incorrect behavior looks like
        consequence: Why this behavior is problematic

    Returns:
        XML string: <incorrect_behavior>...</incorrect_behavior>
    """
    lines = ["<incorrect_behavior>"]
    lines.append(f"  <example>{description}</example>")
    lines.append(f"  <consequence>{consequence}</consequence>")
    lines.append("</incorrect_behavior>")
    return "\n".join(lines)


def format_orchestrator_constraint() -> str:
    """Render the <orchestrator_constraint> XML block.

    Use in dispatch steps to reinforce orchestrator role boundaries.
    Research: Role-Specialized Subagents prevent role drift.

    Returns:
        XML string: <orchestrator_constraint>...</orchestrator_constraint>
    """
    lines = ["<orchestrator_constraint>"]
    lines.append("You are the ORCHESTRATOR. You delegate, you never implement.")
    lines.append("Your agents are highly capable. Trust them with ANY issue.")
    lines.append("PROHIBITED: Edit, Write tools. REQUIRED: Task tool dispatch.")
    lines.append("</orchestrator_constraint>")
    return "\n".join(lines)


def format_factored_verification_rationale() -> str:
    """Render the <factored_verification> rationale block.

    Explains WHY factored verification is structured the way it is.
    Research: Factored verification +10pp accuracy, 45% hallucination cut.

    Returns:
        XML string with rationale for factored verification approach
    """
    lines = ["<factored_verification rationale='true'>"]
    lines.append("Read criteria BEFORE code to prevent confirmation bias.")
    lines.append("Write expectations first, examine second, compare third.")
    lines.append("You MUST record expected behavior BEFORE reading implementation.")
    lines.append("</factored_verification>")
    return "\n".join(lines)


def format_open_question_guidance() -> str:
    """Render guidance block for using open questions in verification.

    Research: Models agree with yes/no regardless of correctness.
    Open questions force factual recall.

    Returns:
        XML string with open question verification principle
    """
    lines = ["<verification_principle>"]
    lines.append("Use OPEN questions, not yes/no.")
    lines.append("  WRONG: 'Does the code handle errors?' (model agrees regardless)")
    lines.append("  RIGHT: 'What error handling exists here?' (forces examination)")
    lines.append("</verification_principle>")
    return "\n".join(lines)


def format_gate_actions(
    qr: QRState,
    pass_message: str,
    self_fix: bool = False,
    fix_target: str = "developer",
) -> list[str]:
    """Generate actions list for a gate step.

    Args:
        qr: QR loop state (must have status set for gate steps)
        pass_message: Message to show when gate passes
        self_fix: If True, orchestrator fixes issues directly
        fix_target: Agent to delegate to if self_fix is False

    Returns:
        List of action strings for the gate step
    """
    actions = []
    if qr.passed:
        actions.append(pass_message)
        actions.append("")
        actions.append(format_forbidden([
            "Asking the user whether to proceed - the workflow is deterministic",
            "Offering alternatives to the next step - all steps are mandatory",
            "Interpreting 'proceed' as optional - EXECUTE immediately",
        ]))
    else:
        # Pedantic mode reminder
        actions.extend([
            "<pedantic_enforcement>",
            "QR exists to catch problems BEFORE they reach production.",
            "See <severity_filter> below for which severities block at this iteration.",
            "</pedantic_enforcement>",
            "",
        ])

        # Progressive de-escalation guidance using get_blocking_severities
        blocking = get_blocking_severities(qr.iteration)
        if blocking == {"MUST", "SHOULD", "COULD"}:
            actions.extend([
                "<severity_filter>",
                f"ITERATION {qr.iteration} of {QR_ITERATION_LIMIT}: All severities block (MUST, SHOULD, COULD)",
                "Fix ALL issues reported by QR before proceeding.",
                "</severity_filter>",
                "",
            ])
        elif blocking == {"MUST", "SHOULD"}:
            actions.extend([
                "<severity_filter>",
                f"ITERATION {qr.iteration} of {QR_ITERATION_LIMIT}: Only MUST and SHOULD severities block",
                "COULD severity issues (DEAD_CODE, FORMATTER_FIXABLE, MINOR_INCONSISTENCY) may be deferred.",
                "Focus on MUST and SHOULD issues. COULD issues are noted but do not block.",
                "</severity_filter>",
                "",
            ])
        else:  # blocking == {"MUST"}
            actions.extend([
                "<severity_filter>",
                f"ITERATION {qr.iteration} of {QR_ITERATION_LIMIT}: Only MUST severity blocks",
                "SHOULD and COULD severity issues may be deferred.",
                "Focus ONLY on MUST issues (knowledge loss, unrecoverable if missed).",
                "SHOULD issues (structural debt) are noted but do not block.",
                "COULD issues (cosmetic) are noted but do not block.",
                "",
                "If NO MUST issues remain, this gate PASSES despite SHOULD/COULD issues.",
                "</severity_filter>",
                "",
            ])

        next_iteration = qr.iteration + 1
        if next_iteration > QR_ITERATION_LIMIT:
            actions.extend([
                "<iteration_limit_reached>",
                f"QR has failed {qr.iteration} times at this checkpoint.",
                "",
                "NOTE: At iteration 5+, only MUST severity issues should block.",
                "If QR is reporting SHOULD/COULD issues only, consider proceeding.",
                "",
                "MANDATORY: Use AskUserQuestion NOW:",
                f"  question: 'QR has found issues across {QR_ITERATION_LIMIT} iterations. How to proceed?'",
                "  header: 'QR Loop'",
                "  options:",
                "    - label: 'Continue iterating'",
                "      description: 'Keep fixing until QR passes'",
                "    - label: 'Fix MUST issues only'",
                "      description: 'Accept SHOULD/COULD issues, fix MUST issues'",
                "    - label: 'Skip this check'",
                "      description: 'Accept current state, note remaining issues'",
                "    - label: 'Abort'",
                "      description: 'Stop and review'",
                "",
                "<human_override_recording>",
                "If user selects 'Skip this check' or 'Fix MUST issues only':",
                "",
                "1. Record accepted risks to plan's Decision Log:",
                "   Add to ## Decision Log section (create if missing):",
                "   | Issue | Rationale | Iteration |",
                "   | ----- | --------- | --------- |",
                "   | [Each MUST issue text] | [User's selected option] | {qr.iteration} |",
                "",
                "2. Instruct TW to add :TODO: comments at code locations:",
                "   For each accepted MUST issue with a file/line reference:",
                "   Delegate to @agent-technical-writer in free-form mode:",
                "   'Add :TODO: comments at [file:line] marking accepted risk: [issue text]'",
                "</human_override_recording>",
                "</iteration_limit_reached>",
                "",
            ])
            actions.extend([
                "<when_user_says_continue>",
                "When user selects 'Continue iterating':",
                "  1. IMMEDIATELY invoke the exact command from <invoke_after> below",
                "  2. The Python script provides the fix guidance - invoke it first",
                "  3. Iteration counter is already incremented in the command",
                "</when_user_says_continue>",
                "",
            ])
        # Gate is pure router - work step provides FIX guidance
        if self_fix:
            actions.extend([
                "NEXT ACTION:",
                "  Invoke the command in <invoke_after> below.",
                "  The next step will provide fix guidance for plan structure issues.",
                "",
            ])
        else:
            actions.extend([
                "NEXT ACTION:",
                "  Invoke the command in <invoke_after> below.",
                f"  The next step will dispatch {fix_target} with fix guidance.",
                "",
                "<qr_report_path_passthrough>",
                "QR_REPORT_PATH from QR output MUST be passed to the work step.",
                "You do NOT read this file. The sub-agent reads it.",
                "</qr_report_path_passthrough>",
                "",
            ])
        actions.append(format_forbidden([
            "Fixing issues directly from this gate step",
            "Spawning agents directly from this gate step",
            "Using Edit/Write tools yourself",
            "Proceeding without invoking the next step",
            "Interpreting 'minor issues' as skippable",
        ]))
    return actions


def format_gate_step(
    script: str,
    step: int,
    total: int,
    gate: GateConfig,
    qr: QRState,
    cmd_template: str,
    phase: str = None,
) -> str:
    """Format a complete gate step output.

    Unified gate formatting for planner.py and executor.py.
    Extracts the common gate pattern that was duplicated in both files.

    Args:
        script: Script name without .py (e.g., "planner", "executor")
        step: Current step number
        total: Total steps in workflow
        gate: Gate configuration (qr_name, pass_step, etc.)
        qr: QR loop state (must have status set)
        cmd_template: Command template for routing (e.g., "python3 planner.py")
        phase: Optional phase for planner.py

    Returns:
        Complete formatted gate step output
    """
    # Build gate result
    if qr.passed:
        gate_result = ("pass", "GATE PASSED")
    else:
        gate_result = ("fail", f"GATE FAILED (iteration {qr.iteration} of {QR_ITERATION_LIMIT})")

    # Build actions using format_gate_actions helper
    actions = format_gate_actions(
        qr=qr,
        pass_message=gate.pass_message,
        self_fix=gate.self_fix,
        fix_target=gate.fix_target or "developer",
    )

    # Build commands
    pass_cmd = None
    if gate.pass_step is not None:
        pass_cmd = f"{cmd_template} --step {gate.pass_step} --total-steps {total}"

    next_iteration = qr.iteration + 1
    fail_cmd = (
        f"{cmd_template} --step {gate.work_step} --total-steps {total} "
        f"--qr-fail --qr-iteration {next_iteration}"
    )

    # Determine which command to use
    if qr.passed:
        next_command = pass_cmd
    else:
        next_command = fail_cmd

    return format_step_output(
        script=script,
        step=step,
        total=total,
        title=f"{gate.qr_name} Gate",
        actions=actions,
        phase=phase,
        gate_result=gate_result,
        next_command=next_command,
    )


def format_qr_file_output(passed: bool, report_path: str = None) -> str:
    """Format minimal QR output for main agent.

    WHY: Token optimization. Main agent only needs PASS/FAIL to route.
    Full report written to file at report_path. Executor reads file directly.
    Reduces main agent context by ~95% for QR results.

    INVISIBLE KNOWLEDGE: Turn boundary isolation means orchestrator forgets
    <post_qr_routing> guidance from dispatch step after sub-agent returns.
    The <orchestrator_action> block here is the ONLY guidance visible when
    orchestrator decides next action. Without it, orchestrator acts on QR
    findings directly instead of invoking gate step first.

    Args:
        passed: True if QR passed, False if issues found
        report_path: Path to full report file (required if passed=False)

    Returns:
        Simple text with routing reminder for orchestrator
    """
    if passed:
        return "RESULT: PASS"
    else:
        # Orchestrator action block prevents premature fixing.
        # This is the ONLY guidance orchestrator sees after QR returns.
        return f"""RESULT: FAIL
QR_REPORT_PATH: {report_path}

<orchestrator_action>
STOP. Do NOT fix issues yet. Do NOT read QR_REPORT_PATH.
Your ONLY action: Invoke the gate step command from <if_fail>.
Pass QR_REPORT_PATH to subsequent steps - you NEVER read this file.
</orchestrator_action>"""
