#!/usr/bin/env python3
"""
DEPRECATED: Use analyze_workflow.py for new workflow architecture.
This file remains for backward compatibility with existing invocations.

Codebase Analysis Skill - Understanding-focused comprehension workflow.

Four-phase workflow:
  1. SCOPE      - Define understanding goals (silent, no user confirmation)
  2. SURVEY     - Initial exploration via Explore agent(s)
  3. DEEPEN     - Targeted deep-dives (1-4 iterations max)
  4. SYNTHESIZE - Structured summary output

Confidence-driven iteration:
  exploring -> low -> medium -> high -> certain

Each step loops until confidence = certain, then advances to next step.
"""

import argparse
import sys

from skills.lib.workflow import Confidence
from skills.lib.workflow.formatters.text import format_text_output


def _scope_non_certain() -> tuple[str, list[str], str | None]:
    """SCOPE step for exploring/low/medium/high confidence."""
    return (
        "SCOPE - Define understanding goals",
        [
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
            "NEXT: Re-invoke --step 1 --confidence certain when goals defined.",
        ],
        None,
    )


def _scope_certain() -> tuple[str, list[str], str | None]:
    """SCOPE step for certain confidence."""
    return (
        "SCOPE - Goals defined",
        [
            "Goals have been defined.",
            "",
            "PROCEED to SURVEY step.",
        ],
        "SURVEY",
    )


def get_scope_actions(confidence: Confidence) -> tuple[str, list[str], str | None]:
    """SCOPE step actions by confidence level.

    Returns (title, actions, next_title).
    next_title=None means re-invoke same step (instruction in actions).
    """
    if confidence == Confidence.CERTAIN:
        return _scope_certain()
    else:
        return _scope_non_certain()


def _survey_exploring() -> tuple[str, list[str], str | None]:
    """SURVEY step for exploring confidence."""
    return (
        "SURVEY - Initial exploration",
        [
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
            "NEXT: Re-invoke --step 2 --confidence low after results received.",
        ],
        None,
    )


def _survey_low() -> tuple[str, list[str], str | None]:
    """SURVEY step for low confidence."""
    return (
        "SURVEY - Process results",
        [
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
            "NEXT:",
            "  - Significant gaps: Re-invoke --step 2 --confidence low, dispatch more agents",
            "  - Minor gaps: Re-invoke --step 2 --confidence medium",
        ],
        None,
    )


def _survey_medium() -> tuple[str, list[str], str | None]:
    """SURVEY step for medium confidence."""
    return (
        "SURVEY - Coverage assessment",
        [
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
            "NEXT:",
            "  - Good coverage: Re-invoke --step 2 --confidence certain",
            "  - One specific gap: Dispatch agent, re-invoke --step 2 --confidence medium",
            "  - Multiple gaps: Re-invoke --step 2 --confidence low",
        ],
        None,
    )


def _survey_high() -> tuple[str, list[str], str | None]:
    """SURVEY step for high confidence."""
    return (
        "SURVEY - Final check",
        [
            "VERIFY initial map complete:",
            "  - All major components identified?",
            "  - Overall structure understood?",
            "  - Entry points and flows mapped?",
            "",
            "REMAINING questions are normal - DEEPEN addresses these.",
            "",
            "NEXT: Re-invoke --step 2 --confidence certain.",
        ],
        None,
    )


def _survey_certain() -> tuple[str, list[str], str | None]:
    """SURVEY step for certain confidence."""
    return (
        "SURVEY - Complete",
        [
            "Initial exploration complete.",
            "",
            "PROCEED to DEEPEN step.",
        ],
        "DEEPEN",
    )


def get_survey_actions(confidence: Confidence) -> tuple[str, list[str], str | None]:
    """SURVEY step actions by confidence level."""
    dispatch = {
        Confidence.EXPLORING: _survey_exploring,
        Confidence.LOW: _survey_low,
        Confidence.MEDIUM: _survey_medium,
        Confidence.HIGH: _survey_high,
        Confidence.CERTAIN: _survey_certain,
    }
    return dispatch[confidence]()


def _deepen_max_iterations(iteration: int, max_iterations: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step when max iterations reached."""
    return (
        f"DEEPEN - Max iterations reached (iteration {iteration}/{max_iterations})",
        [
            "Maximum DEEPEN iterations reached.",
            "",
            "FORCE transition to SYNTHESIZE.",
        ],
        "SYNTHESIZE",
    )


def _deepen_exploring(iteration: int, max_iterations: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step for exploring confidence."""
    return (
        f"DEEPEN - Identify depth targets (iteration {iteration}/{max_iterations})",
        [
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
            f"NEXT: Re-invoke --step 3 --confidence low --iteration {iteration}.",
        ],
        None,
    )


def _deepen_low(iteration: int, max_iterations: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step for low confidence."""
    return (
        f"DEEPEN - Dispatch deep-dive (iteration {iteration}/{max_iterations})",
        [
            "DISPATCH targeted Explore agent(s):",
            "",
            "Focus on specific targets identified:",
            "  - Provide clear focus area",
            "  - Include specific questions to answer",
            "  - Reference files/components from SURVEY",
            "",
            "WAIT for results before re-invoking this step.",
            "",
            f"NEXT: Re-invoke --step 3 --confidence medium --iteration {iteration}.",
        ],
        None,
    )


def _deepen_medium(iteration: int, max_iterations: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step for medium confidence."""
    return (
        f"DEEPEN - Process results (iteration {iteration}/{max_iterations})",
        [
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
            "NEXT:",
            f"  - Understanding sufficient: Re-invoke --step 3 --confidence high --iteration {iteration}",
            f"  - Need more on SAME target: Re-invoke --step 3 --confidence low --iteration {iteration}",
            f"  - New target identified: Re-invoke --step 3 --confidence exploring --iteration {iteration + 1}",
        ],
        None,
    )


def _deepen_high(iteration: int, max_iterations: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step for high confidence."""
    return (
        f"DEEPEN - Iteration complete (iteration {iteration}/{max_iterations})",
        [
            "ASSESS overall understanding:",
            "",
            "Check against goals:",
            "  - Can we explain the key aspects?",
            "  - Are the important flows clear?",
            "  - Do we understand the critical decisions?",
            "",
            f"At iteration {max_iterations}: Must advance to SYNTHESIZE.",
            "",
            "NEXT:",
            f"  - Understanding complete: Re-invoke --step 3 --confidence certain --iteration {iteration}",
            f"  - More depth needed: Re-invoke --step 3 --confidence exploring --iteration {iteration + 1}",
        ],
        None,
    )


def _deepen_certain(iteration: int, max_iterations: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step for certain confidence."""
    return (
        "DEEPEN - Complete",
        [
            "Deep understanding achieved.",
            "",
            "PROCEED to SYNTHESIZE step.",
        ],
        "SYNTHESIZE",
    )


def get_deepen_actions(confidence: Confidence, iteration: int) -> tuple[str, list[str], str | None]:
    """DEEPEN step actions by confidence level and iteration."""
    max_iterations = 4

    if iteration > max_iterations:
        return _deepen_max_iterations(iteration, max_iterations)

    dispatch = {
        Confidence.EXPLORING: _deepen_exploring,
        Confidence.LOW: _deepen_low,
        Confidence.MEDIUM: _deepen_medium,
        Confidence.HIGH: _deepen_high,
        Confidence.CERTAIN: _deepen_certain,
    }
    return dispatch[confidence](iteration, max_iterations)


def _synthesize_exploring() -> tuple[str, list[str], str | None]:
    """SYNTHESIZE step for exploring confidence."""
    return (
        "SYNTHESIZE - Begin assembly",
        [
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
            "NEXT: Re-invoke --step 4 --confidence low.",
        ],
        None,
    )


def _synthesize_low_medium(confidence: Confidence) -> tuple[str, list[str], str | None]:
    """SYNTHESIZE step for low/medium confidence."""
    return (
        f"SYNTHESIZE - Refine summary ({confidence.value} confidence)",
        [
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
            "NEXT:",
            "  - Ready for output: Re-invoke --step 4 --confidence high",
            f"  - Needs refinement: Re-invoke --step 4 --confidence {confidence.value}",
        ],
        None,
    )


def _synthesize_high() -> tuple[str, list[str], str | None]:
    """SYNTHESIZE step for high confidence."""
    return (
        "SYNTHESIZE - Final check",
        [
            "FINAL verification:",
            "  - Summary addresses user's original intent?",
            "  - Structure/Patterns/Flows/Decisions/Context all present?",
            "  - Framing is understanding-focused (not auditing)?",
            "",
            "NEXT: Re-invoke --step 4 --confidence certain.",
        ],
        None,
    )


def _synthesize_certain() -> tuple[str, list[str], str | None]:
    """SYNTHESIZE step for certain confidence."""
    return (
        "SYNTHESIZE - Output summary",
        [
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
        ],
        None,
    )


def get_synthesize_actions(confidence: Confidence) -> tuple[str, list[str], str | None]:
    """SYNTHESIZE step actions by confidence level."""
    if confidence == Confidence.EXPLORING:
        return _synthesize_exploring()
    elif confidence in (Confidence.LOW, Confidence.MEDIUM):
        return _synthesize_low_medium(confidence)
    elif confidence == Confidence.HIGH:
        return _synthesize_high()
    else:
        return _synthesize_certain()


def main():
    parser = argparse.ArgumentParser(
        description="Codebase Analysis - Understanding-focused comprehension workflow",
        epilog="Phases: SCOPE (1) -> SURVEY (2) -> DEEPEN (3) -> SYNTHESIZE (4)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument(
        "--confidence",
        type=str,
        choices=[c.value for c in Confidence],
        default="exploring",
        help="Current confidence level (exploring/low/medium/high/certain)",
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

    # Convert string to Confidence enum
    confidence = Confidence(args.confidence)

    # Map step to actions
    if args.step == 1:
        title, actions, next_title = get_scope_actions(confidence)
    elif args.step == 2:
        title, actions, next_title = get_survey_actions(confidence)
    elif args.step == 3:
        title, actions, next_title = get_deepen_actions(confidence, args.iteration)
    else:  # step 4
        title, actions, next_title = get_synthesize_actions(confidence)

    print(
        format_text_output(
            step=args.step,
            total=args.total_steps,
            title=f"CODEBASE ANALYSIS - {title}",
            actions=actions,
            next_title=next_title,
        )
    )


if __name__ == "__main__":
    main()
