#!/usr/bin/env python3
"""
Codebase Analysis Skill - Understanding-focused comprehension workflow.

Four-phase workflow with confidence-driven iteration:
  1. SCOPE      - Define understanding goals
  2. SURVEY     - Initial exploration
  3. DEEPEN     - Targeted deep-dives (1-4 iterations)
  4. SYNTHESIZE - Structured summary output

Confidence progression: exploring -> low -> medium -> high -> certain
Each step can loop internally until confidence = certain.
"""

import argparse
import sys

from skills.lib.workflow.core import StepDef, Workflow
from skills.lib.workflow.ast import (
    W, XMLRenderer, render, TextNode,
    RosterDispatchNode, render_roster_dispatch,
)
from skills.lib.workflow.ast.nodes import (
    StepHeaderNode, CurrentActionNode, InvokeAfterNode,
)
from skills.lib.workflow.ast.renderer import (
    render_step_header, render_current_action, render_invoke_after,
)


# Module path for -m invocation
MODULE_PATH = "skills.codebase_analysis.analyze_workflow"


# XML format mandate for step 1
XML_FORMAT_MANDATE = """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>
3. The <next> block re-states the command -- execute it
4. For branching <invoke_after>, choose based on outcome

DO NOT modify commands. DO NOT skip steps. DO NOT interpret.
</xml_format_mandate>"""


# Maximum iterations for DEEPEN phase
MAX_DEEPEN_ITERATIONS = 4


def build_explore_dispatch_guidance() -> str:
    """Generate Explore agent dispatch guidance using RosterDispatchNode pattern.

    Exploration goals are user-driven; each agent has distinct focus based on codebase structure.
    Actual agent targets determined at runtime by the LLM based on user's goals.
    """
    # Shared context from prior steps (SCOPE phase output)
    shared_context = """Analysis goals from SCOPE step:
- User intent and what they want to understand
- Identified focus areas (architecture, components, flows, etc.)
- Defined objectives (1-3 specific goals)"""

    # Placeholder agents - actual exploration focuses determined at runtime
    agents = (
        "[Exploration focus 1: e.g., 'Explore authentication flow']",
        "[Exploration focus 2: e.g., 'Explore database schema']",
        "[Exploration focus N: based on scope and codebase structure]",
    )

    node = RosterDispatchNode(
        agent_type="Explore",
        shared_context=shared_context,
        agents=agents,
        command="Use Task tool with subagent_type='Explore'",
        model="haiku",
        instruction="Dispatch Explore agents targeting defined goals. Use Task tool with Explore subagent_type.",
    )

    return render_roster_dispatch(node)


# Phase action definitions
SCOPE_ACTIONS = [
    "PARSE user intent:",
    "  - What codebase(s) are we analyzing?",
    "  - What is the user trying to understand?",
    "  - Are there specific areas of interest mentioned?",
    "",
    "IDENTIFY focus areas:",
    "  - Architecture/structure understanding",
    "  - Specific component/feature deep-dive",
    "  - Technology stack assessment",
    "  - Integration patterns",
    "  - Data flows",
    "",
    "DEFINE goals (1-3 specific objectives):",
    "  - 'Understand how [system X] processes [Y]'",
    "  - 'Map dependencies between [A] and [B]'",
    "  - 'Document data flow from [input] to [output]'",
    "",
    "DO NOT seek user confirmation. Goals are internal guidance.",
    "",
    "ADVANCE: When goals defined, re-invoke with higher confidence.",
]

def get_survey_exploring_actions() -> list[str]:
    """Generate SURVEY exploring actions with dispatch guidance."""
    dispatch_xml = build_explore_dispatch_guidance()
    return [
        "DISPATCH Explore agent(s) targeting defined goals:",
        "",
        dispatch_xml,
        "",
        "DISPATCH GUIDANCE:",
        "",
        "Single codebase, focused scope:",
        "  - One Explore agent with specific focus",
        "",
        "Large/broad scope:",
        "  - Multiple parallel Explore agents by boundary",
        "  - Example: frontend agent + backend agent + data agent",
        "",
        "Multiple repositories:",
        "  - One Explore agent per repository",
        "",
        "WAIT for Explore results before re-invoking this step.",
        "",
        "ADVANCE: After results received, re-invoke with --confidence low.",
    ]


SURVEY_EXPLORING_ACTIONS = get_survey_exploring_actions()

SURVEY_LOW_ACTIONS = [
    "EXTRACT findings from Explore output:",
    "",
    "STRUCTURE:",
    "  - Directory organization",
    "  - File patterns",
    "  - Module boundaries",
    "",
    "PATTERNS:",
    "  - Architectural style (layered, microservices, monolithic)",
    "  - Code organization patterns",
    "  - Naming conventions",
    "",
    "FLOWS:",
    "  - Entry points",
    "  - Request/data flow paths",
    "  - Integration patterns",
    "",
    "DECISIONS:",
    "  - Technology choices",
    "  - Framework usage",
    "  - Dependencies",
    "",
    "IDENTIFY GAPS:",
    "  - Areas not covered by exploration",
    "  - Questions that remain unanswered",
    "",
    "ADVANCE:",
    "  - Significant gaps: Re-invoke with --confidence low, dispatch more agents",
    "  - Minor gaps: Re-invoke with --confidence medium",
]

SURVEY_MEDIUM_ACTIONS = [
    "ASSESS coverage against goals:",
    "  - Which goals have initial understanding?",
    "  - Which goals need more exploration?",
    "",
    "Balance breadth vs depth:",
    "  - SURVEY focuses on breadth (map the landscape)",
    "  - DEEPEN focuses on depth (understand specifics)",
    "",
    "Prefer advancing to DEEPEN over extending SURVEY.",
    "",
    "ADVANCE:",
    "  - Good coverage: Re-invoke with --confidence high",
    "  - One specific gap: Dispatch agent, re-invoke with --confidence medium",
    "  - Multiple gaps: Re-invoke with --confidence low",
]

SURVEY_HIGH_ACTIONS = [
    "VERIFY initial map complete:",
    "  - All major components identified?",
    "  - Overall structure understood?",
    "  - Entry points and flows mapped?",
    "",
    "REMAINING questions are normal - DEEPEN addresses these.",
    "",
    "ADVANCE: Re-invoke with --confidence certain to proceed to DEEPEN.",
]

DEEPEN_EXPLORING_ACTIONS = [
    "IDENTIFY areas needing deep understanding:",
    "",
    "Prioritize by:",
    "  - COMPLEXITY: Non-obvious behavior, intricate logic",
    "  - NOVELTY: Unfamiliar patterns, unique approaches",
    "  - CENTRALITY: Core to user's goals",
    "",
    "SELECT 1-3 targets for this iteration:",
    "  - Specific component/module",
    "  - Particular data flow",
    "  - Integration mechanism",
    "  - Implementation pattern",
    "",
    "For each target:",
    "  - What specifically do we need to understand?",
    "  - What questions remain unanswered?",
    "",
    "ADVANCE: Re-invoke with --confidence low.",
]

def get_deepen_low_actions() -> list[str]:
    """Generate DEEPEN low-confidence actions with dispatch guidance."""
    dispatch_xml = build_explore_dispatch_guidance()
    return [
        "DISPATCH targeted Explore agent(s):",
        "",
        dispatch_xml,
        "",
        "Focus on specific targets identified:",
        "  - Provide clear focus area",
        "  - Include specific questions to answer",
        "  - Reference files/components from SURVEY",
        "",
        "WAIT for results before re-invoking this step.",
        "",
        "ADVANCE: After results, re-invoke with --confidence medium.",
    ]


DEEPEN_LOW_ACTIONS = get_deepen_low_actions()

DEEPEN_MEDIUM_ACTIONS = [
    "PROCESS deep-dive findings:",
    "",
    "EXTRACT understanding:",
    "  - How does this component work?",
    "  - What are the key mechanisms?",
    "  - How does it integrate with other parts?",
    "",
    "ASSESS depth achieved:",
    "  - Questions answered?",
    "  - Understanding sufficient for goals?",
    "  - New questions emerged?",
    "",
    "ADVANCE:",
    "  - Understanding sufficient: Re-invoke with --confidence high",
    "  - Need more on SAME target: Re-invoke with --confidence low",
    "  - New target identified: Re-invoke with --confidence exploring, increment --iteration",
]

DEEPEN_HIGH_ACTIONS = [
    "ASSESS overall understanding:",
    "",
    "Check against goals:",
    "  - Can we explain the key aspects?",
    "  - Are the important flows clear?",
    "  - Do we understand the critical decisions?",
    "",
    "At maximum iterations: Must advance to SYNTHESIZE.",
    "",
    "ADVANCE:",
    "  - Understanding complete: Re-invoke with --confidence certain",
    "  - More depth needed: Re-invoke with --confidence exploring, increment --iteration",
]

SYNTHESIZE_EXPLORING_ACTIONS = [
    "BEGIN assembling findings into structured summary.",
    "",
    "PREPARE sections:",
    "",
    "STRUCTURE:",
    "  - Directory organization",
    "  - Module boundaries",
    "  - Component relationships",
    "",
    "PATTERNS:",
    "  - Architectural patterns",
    "  - Design patterns",
    "  - Code organization patterns",
    "",
    "FLOWS:",
    "  - Request flows",
    "  - Data flows",
    "  - Integration flows",
    "",
    "DECISIONS:",
    "  - Technology choices and rationale",
    "  - Framework selections",
    "  - Architectural decisions",
    "",
    "CONTEXT:",
    "  - Purpose and intent",
    "  - Constraints and trade-offs",
    "  - Evolution and history (if evident)",
    "",
    "ADVANCE: Re-invoke with --confidence low.",
]

SYNTHESIZE_LOW_MEDIUM_ACTIONS = [
    "REFINE summary sections:",
    "",
    "ENSURE completeness:",
    "  - All goals addressed?",
    "  - Key findings included?",
    "  - Important context provided?",
    "",
    "CHECK clarity:",
    "  - Is the structure clear?",
    "  - Are patterns well-explained?",
    "  - Are flows understandable?",
    "",
    "VERIFY framing:",
    "  - Facts and observations (not judgments)",
    "  - Understanding-focused (not problem-finding)",
    "  - Structured and organized",
    "",
    "Do not over-iterate. Aim for good enough, not perfect.",
    "",
    "ADVANCE:",
    "  - Ready for output: Re-invoke with --confidence high",
    "  - Needs refinement: Continue refining at current confidence",
]

SYNTHESIZE_HIGH_ACTIONS = [
    "FINAL verification:",
    "  - Summary addresses user's original intent?",
    "  - Structure/Patterns/Flows/Decisions/Context all present?",
    "  - Framing is understanding-focused (not auditing)?",
    "",
    "ADVANCE: Re-invoke with --confidence certain to output final summary.",
]

SYNTHESIZE_CERTAIN_ACTIONS = [
    "OUTPUT structured summary:",
    "",
    "FORMAT:",
    "",
    "# Codebase Understanding Summary",
    "",
    "## Structure",
    "[Directory organization, module boundaries, component relationships]",
    "",
    "## Patterns",
    "[Architectural patterns, design patterns, code organization]",
    "",
    "## Flows",
    "[Request flows, data flows, integration patterns]",
    "",
    "## Decisions",
    "[Technology choices, framework selections, architectural decisions]",
    "",
    "## Context",
    "[Purpose, constraints, trade-offs, evolution]",
    "",
    "WORKFLOW COMPLETE - Present summary to user.",
]


# Workflow definition (metadata only, execution via CLI)
WORKFLOW = Workflow(
    "codebase-analysis",
    StepDef(id="scope", title="SCOPE - Define understanding goals", actions=SCOPE_ACTIONS, phase="SCOPE"),
    StepDef(id="survey", title="SURVEY - Initial exploration", actions=SURVEY_EXPLORING_ACTIONS, phase="SURVEY"),
    StepDef(id="deepen", title="DEEPEN - Targeted deep-dives", actions=DEEPEN_EXPLORING_ACTIONS, phase="DEEPEN"),
    StepDef(id="synthesize", title="SYNTHESIZE - Structured summary output", actions=SYNTHESIZE_EXPLORING_ACTIONS, phase="SYNTHESIZE"),
    description="Understanding-focused codebase comprehension workflow with confidence-driven iteration",
    validate=False,
)


# =============================================================================
# Output Formatting
# =============================================================================


def format_output(step: int, confidence: str, iteration: int) -> str:
    """Format output for display using XML building blocks."""
    # Map step to phase and get appropriate actions
    step_map = {
        1: ("SCOPE", get_scope_actions(confidence)),
        2: ("SURVEY", get_survey_actions(confidence)),
        3: ("DEEPEN", get_deepen_actions(confidence, iteration)),
        4: ("SYNTHESIZE", get_synthesize_actions(confidence)),
    }

    phase, (title, actions, next_phase) = step_map[step]
    full_title = f"CODEBASE ANALYSIS - {title}"

    parts = []

    # Step header
    parts.append(render_step_header(StepHeaderNode(
        title=full_title,
        script="codebase-analysis",
        step=str(step)
    )))
    parts.append("")

    # XML mandate on step 1
    if step == 1 and confidence == "exploring":
        parts.append(XML_FORMAT_MANDATE)
        parts.append("")

    # Current action
    parts.append(render_current_action(CurrentActionNode(actions)))
    parts.append("")

    # Invoke after - build the next command based on state
    next_cmd = build_next_command(step, WORKFLOW.total_steps, confidence, iteration, next_phase)
    if next_cmd:
        parts.append(render_invoke_after(InvokeAfterNode(cmd=next_cmd)))
    else:
        parts.append("WORKFLOW COMPLETE - Present summary to user.")

    return "\n".join(parts)


def build_next_command(step: int, total_steps: int, confidence: str, iteration: int, next_phase: str | None) -> str | None:
    """Build the invoke command for the next step."""
    base_cmd = f'python3 -m {MODULE_PATH}'

    if step == 1:  # SCOPE
        if confidence == "certain":
            # Advance to SURVEY
            return f'{base_cmd} --step 2 --confidence exploring'
        else:
            # Re-invoke SCOPE with placeholder for confidence
            return f'{base_cmd} --step 1 --confidence {{exploring|low|medium|high|certain}}'

    elif step == 2:  # SURVEY
        if confidence == "certain":
            # Advance to DEEPEN
            return f'{base_cmd} --step 3 --confidence exploring --iteration 1'
        else:
            # Re-invoke SURVEY with placeholder for confidence
            return f'{base_cmd} --step 2 --confidence {{exploring|low|medium|high|certain}}'

    elif step == 3:  # DEEPEN
        if confidence == "certain" or iteration > MAX_DEEPEN_ITERATIONS:
            # Advance to SYNTHESIZE
            return f'{base_cmd} --step 4 --confidence exploring'
        elif confidence == "exploring" and iteration > 1:
            # New iteration cycle
            return f'{base_cmd} --step 3 --confidence {{exploring|low|medium|high|certain}} --iteration {iteration}'
        else:
            # Continue current iteration
            next_iter = iteration if confidence != "exploring" else iteration
            return f'{base_cmd} --step 3 --confidence {{exploring|low|medium|high|certain}} --iteration {next_iter}'

    elif step == 4:  # SYNTHESIZE
        if confidence == "certain":
            # Workflow complete
            return None
        else:
            # Re-invoke SYNTHESIZE with placeholder for confidence
            return f'{base_cmd} --step 4 --confidence {{exploring|low|medium|high|certain}}'

    return None


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Codebase Analysis - Understanding-focused comprehension workflow",
        epilog="Phases: SCOPE (1) -> SURVEY (2) -> DEEPEN (3) -> SYNTHESIZE (4)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument(
        "--confidence",
        type=str,
        choices=["exploring", "low", "medium", "high", "certain"],
        default="exploring",
        help="Current confidence level",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=1,
        help="Iteration count (DEEPEN step only, max 4)",
    )
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.step > WORKFLOW.total_steps:
        sys.exit(f"ERROR: --step cannot exceed {WORKFLOW.total_steps}")
    if args.iteration < 1:
        sys.exit("ERROR: --iteration must be >= 1")

    print(format_output(args.step, args.confidence, args.iteration))


def get_scope_actions(confidence: str) -> tuple[str, list[str], str | None]:
    """Get SCOPE actions based on confidence."""
    if confidence == "certain":
        return ("Goals defined", ["Goals have been defined.", "", "PROCEED to SURVEY step."], "SURVEY")
    else:
        return ("Define understanding goals", SCOPE_ACTIONS, None)


def get_survey_actions(confidence: str) -> tuple[str, list[str], str | None]:
    """Get SURVEY actions based on confidence."""
    if confidence == "certain":
        return ("Complete", ["Initial exploration complete.", "", "PROCEED to DEEPEN step."], "DEEPEN")
    elif confidence == "high":
        return ("Final check", SURVEY_HIGH_ACTIONS, None)
    elif confidence == "medium":
        return ("Coverage assessment", SURVEY_MEDIUM_ACTIONS, None)
    elif confidence == "low":
        return ("Process results", SURVEY_LOW_ACTIONS, None)
    else:  # exploring
        return ("Initial exploration", SURVEY_EXPLORING_ACTIONS, None)


def get_deepen_actions(confidence: str, iteration: int) -> tuple[str, list[str], str | None]:
    """Get DEEPEN actions based on confidence and iteration."""
    if iteration > MAX_DEEPEN_ITERATIONS:
        return (
            f"Max iterations reached (iteration {iteration}/{MAX_DEEPEN_ITERATIONS})",
            ["Maximum DEEPEN iterations reached.", "", "FORCE transition to SYNTHESIZE."],
            "SYNTHESIZE",
        )

    if confidence == "certain":
        return ("Complete", ["Deep understanding achieved.", "", "PROCEED to SYNTHESIZE step."], "SYNTHESIZE")
    elif confidence == "high":
        return (f"Iteration complete (iteration {iteration}/{MAX_DEEPEN_ITERATIONS})", DEEPEN_HIGH_ACTIONS, None)
    elif confidence == "medium":
        return (f"Process results (iteration {iteration}/{MAX_DEEPEN_ITERATIONS})", DEEPEN_MEDIUM_ACTIONS, None)
    elif confidence == "low":
        return (f"Dispatch deep-dive (iteration {iteration}/{MAX_DEEPEN_ITERATIONS})", DEEPEN_LOW_ACTIONS, None)
    else:  # exploring
        return (f"Identify depth targets (iteration {iteration}/{MAX_DEEPEN_ITERATIONS})", DEEPEN_EXPLORING_ACTIONS, None)


def get_synthesize_actions(confidence: str) -> tuple[str, list[str], str | None]:
    """Get SYNTHESIZE actions based on confidence."""
    if confidence == "certain":
        return ("Output summary", SYNTHESIZE_CERTAIN_ACTIONS, None)
    elif confidence == "high":
        return ("Final check", SYNTHESIZE_HIGH_ACTIONS, None)
    elif confidence in ("low", "medium"):
        return (f"Refine summary ({confidence} confidence)", SYNTHESIZE_LOW_MEDIUM_ACTIONS, None)
    else:  # exploring
        return ("Begin assembly", SYNTHESIZE_EXPLORING_ACTIONS, None)


if __name__ == "__main__":
    main()
