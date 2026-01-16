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

from typing import Annotated
from skills.lib.workflow.core import (
    Outcome,
    StepContext,
    StepDef,
    Workflow,
    Arg,
)
from skills.lib.workflow.ast import W, XMLRenderer, render


# Maximum iterations for DEEPEN phase
MAX_DEEPEN_ITERATIONS = 4


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

SURVEY_EXPLORING_ACTIONS = [
    "DISPATCH Explore agent(s) targeting defined goals:",
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

DEEPEN_LOW_ACTIONS = [
    "DISPATCH targeted Explore agent(s):",
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


# Handler functions
def step_handler(ctx: StepContext) -> tuple[Outcome, dict]:
    """Generic handler for output-only steps."""
    return Outcome.OK, {}


def step_scope(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for SCOPE step with confidence progression."""
    confidence = ctx.workflow_params.get("confidence", "exploring")

    if confidence == "certain":
        return Outcome.OK, {"confidence": confidence}
    else:
        # Instruct to re-invoke with higher confidence when goals defined
        return Outcome.ITERATE, {"confidence": confidence}


def step_survey(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for SURVEY step with confidence progression."""
    confidence = ctx.workflow_params.get("confidence", "exploring")

    if confidence == "certain":
        return Outcome.OK, {"confidence": confidence}
    else:
        return Outcome.ITERATE, {"confidence": confidence}


def step_deepen(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for DEEPEN step with confidence progression and iteration cap."""
    iteration = ctx.workflow_params.get("iteration", 1)
    confidence = ctx.workflow_params.get("confidence", "exploring")

    # Exit conditions
    if confidence == "certain":
        return Outcome.OK, {"confidence": confidence, "iteration": iteration}
    elif iteration > MAX_DEEPEN_ITERATIONS:
        # Force transition to SYNTHESIZE
        return Outcome.OK, {"confidence": "capped", "iteration": iteration}
    else:
        return Outcome.ITERATE, {"iteration": iteration, "confidence": confidence}


def step_synthesize(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for SYNTHESIZE step with confidence progression."""
    confidence = ctx.workflow_params.get("confidence", "exploring")

    if confidence == "certain":
        return Outcome.OK, {"confidence": confidence}
    else:
        return Outcome.ITERATE, {"confidence": confidence}


# Workflow definition
WORKFLOW = Workflow(
    "codebase-analysis",
    StepDef(
        id="scope",
        title="SCOPE - Define understanding goals",
        phase="SCOPE",
        actions=SCOPE_ACTIONS,
        handler=step_scope,
        next={
            Outcome.OK: "survey",
            Outcome.ITERATE: "scope",
        },
    ),
    StepDef(
        id="survey",
        title="SURVEY - Initial exploration",
        phase="SURVEY",
        actions=SURVEY_EXPLORING_ACTIONS,  # Will be dynamic based on confidence
        handler=step_survey,
        next={
            Outcome.OK: "deepen",
            Outcome.ITERATE: "survey",
        },
    ),
    StepDef(
        id="deepen",
        title="DEEPEN - Targeted deep-dives",
        phase="DEEPEN",
        actions=DEEPEN_EXPLORING_ACTIONS,  # Will be dynamic based on confidence/iteration
        handler=step_deepen,
        next={
            Outcome.OK: "synthesize",
            Outcome.ITERATE: "deepen",
        },
    ),
    StepDef(
        id="synthesize",
        title="SYNTHESIZE - Structured summary output",
        phase="SYNTHESIZE",
        actions=SYNTHESIZE_EXPLORING_ACTIONS,  # Will be dynamic based on confidence
        handler=step_synthesize,
        next={
            Outcome.OK: None,  # Terminal
            Outcome.ITERATE: "synthesize",
        },
    ),
    description="Understanding-focused codebase comprehension workflow with confidence-driven iteration",
)


# Backward compatibility: CLI entry point
def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Codebase Analysis - Understanding-focused comprehension workflow",
        epilog="Phases: SCOPE (1) -> SURVEY (2) -> DEEPEN (3) -> SYNTHESIZE (4)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
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
    if args.total_steps != 4:
        sys.exit("ERROR: --total-steps must be 4 for this workflow")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")
    if args.iteration < 1:
        sys.exit("ERROR: --iteration must be >= 1")

    # Map step to phase and get appropriate actions
    step_map = {
        1: ("SCOPE", get_scope_actions(args.confidence)),
        2: ("SURVEY", get_survey_actions(args.confidence)),
        3: ("DEEPEN", get_deepen_actions(args.confidence, args.iteration)),
        4: ("SYNTHESIZE", get_synthesize_actions(args.confidence)),
    }

    phase, (title, actions, next_title) = step_map[args.step]

    output = render(W.text_output(
        step=args.step,
        total=args.total_steps,
        title=f"CODEBASE ANALYSIS - {title}",
        actions=actions
    ).build(), XMLRenderer())
    print(output)


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
