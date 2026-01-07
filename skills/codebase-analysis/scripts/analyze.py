#!/usr/bin/env python3
"""
Codebase Analysis Skill - Understanding-focused comprehension workflow.

Four-phase workflow:
  1. SCOPE      - Define understanding goals (silent, no user confirmation)
  2. SURVEY     - Initial exploration via Explore agent(s)
  3. DEEPEN     - Targeted deep-dives (1-4 iterations max)
  4. SYNTHESIZE - Structured summary output

Confidence-driven iteration:
  exploring -> low -> medium -> high -> certain

Each step loops until confidence = certain, then advances to next step.

Usage:
    python3 analyze.py --step 1 --total-steps 4 --confidence exploring
    python3 analyze.py --step 3 --total-steps 4 --confidence low --iteration 2
"""

import argparse
import sys
from pathlib import Path

# Add .claude/ to path for skills.* imports
_claude_dir = Path(__file__).resolve().parents[3]
if str(_claude_dir) not in sys.path:
    sys.path.insert(0, str(_claude_dir))

from skills.lib.workflow.formatters.text import format_text_output


CONFIDENCE_LEVELS = ["exploring", "low", "medium", "high", "certain"]


def get_scope_actions(confidence: str) -> tuple[str, list[str], str]:
    """SCOPE step actions by confidence level."""
    if confidence in ["exploring", "low", "medium", "high"]:
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
                "ADVANCE to SURVEY with confidence=certain when goals defined.",
            ],
            "SURVEY",
        )
    else:  # certain
        return (
            "SCOPE - Goals defined",
            [
                "Goals have been defined.",
                "",
                "PROCEED to SURVEY step.",
            ],
            "SURVEY",
        )


def get_survey_actions(confidence: str) -> tuple[str, list[str], str]:
    """SURVEY step actions by confidence level."""
    if confidence == "exploring":
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
                "After dispatch: Re-invoke with confidence=low.",
            ],
            "SURVEY (processing results)",
        )
    elif confidence == "low":
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
                "If significant gaps: Re-invoke with confidence=low, dispatch more agents.",
                "If minor gaps: Advance to confidence=medium.",
            ],
            "SURVEY (coverage assessment)",
        )
    elif confidence == "medium":
        return (
            "SURVEY - Coverage assessment",
            [
                "ASSESS coverage against goals:",
                "  - Which goals have initial understanding?",
                "  - Which goals need more exploration?",
                "",
                "OPTIONS:",
                "  - Good coverage: Advance to confidence=high",
                "  - One specific gap: Dispatch targeted Explore agent, stay medium",
                "  - Multiple gaps: Return to confidence=low, dispatch agents",
                "",
                "Balance breadth vs depth:",
                "  - SURVEY focuses on breadth (map the landscape)",
                "  - DEEPEN focuses on depth (understand specifics)",
                "",
                "Prefer advancing to DEEPEN over extending SURVEY.",
            ],
            "SURVEY (final check) or DEEPEN",
        )
    elif confidence == "high":
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
                "ADVANCE to DEEPEN with confidence=certain, iteration=1.",
            ],
            "DEEPEN",
        )
    else:  # certain
        return (
            "SURVEY - Complete",
            [
                "Initial exploration complete.",
                "",
                "PROCEED to DEEPEN step.",
            ],
            "DEEPEN",
        )


def get_deepen_actions(confidence: str, iteration: int) -> tuple[str, list[str], str]:
    """DEEPEN step actions by confidence level and iteration."""
    max_iterations = 4

    if iteration > max_iterations:
        return (
            f"DEEPEN - Max iterations reached (iteration {iteration}/{max_iterations})",
            [
                "Maximum DEEPEN iterations reached.",
                "",
                "FORCE transition to SYNTHESIZE.",
            ],
            "SYNTHESIZE",
        )

    if confidence == "exploring":
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
                "ADVANCE to confidence=low.",
            ],
            f"DEEPEN iteration {iteration} (dispatch)",
        )
    elif confidence == "low":
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
                f"Pass --iteration {iteration} to agent context.",
                "",
                "WAIT for results before re-invoking this step.",
                "",
                "After dispatch: Re-invoke with confidence=medium.",
            ],
            f"DEEPEN iteration {iteration} (processing)",
        )
    elif confidence == "medium":
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
                "OPTIONS:",
                "  - Understanding sufficient: Advance to confidence=high",
                "  - Need more detail on SAME target: Stay medium, dispatch again",
                "  - New target identified: Return to exploring, increment iteration",
            ],
            f"DEEPEN iteration {iteration} (assessment) or iteration {iteration + 1}",
        )
    elif confidence == "high":
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
                "OPTIONS:",
                "  - Understanding complete: Advance to SYNTHESIZE with confidence=certain",
                f"  - More depth needed: Start iteration {iteration + 1}",
                f"    (return to confidence=exploring, increment iteration)",
                "",
                f"At iteration {max_iterations}: Must advance to SYNTHESIZE.",
            ],
            f"SYNTHESIZE or DEEPEN iteration {iteration + 1}",
        )
    else:  # certain
        return (
            "DEEPEN - Complete",
            [
                "Deep understanding achieved.",
                "",
                "PROCEED to SYNTHESIZE step.",
            ],
            "SYNTHESIZE",
        )


def get_synthesize_actions(confidence: str) -> tuple[str, list[str], str]:
    """SYNTHESIZE step actions by confidence level."""
    if confidence == "exploring":
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
                "ADVANCE to confidence=low.",
            ],
            "SYNTHESIZE (refining)",
        )
    elif confidence in ["low", "medium"]:
        status = "low" if confidence == "low" else "medium"
        return (
            f"SYNTHESIZE - Refine summary ({status} confidence)",
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
                "OPTIONS:",
                "  - Ready for output: Advance to confidence=high",
                "  - Needs refinement: Stay at current confidence, refine more",
                "",
                "Do not over-iterate. Aim for good enough, not perfect.",
            ],
            "SYNTHESIZE (final check)",
        )
    elif confidence == "high":
        return (
            "SYNTHESIZE - Final check",
            [
                "FINAL verification:",
                "  - Summary addresses user's original intent?",
                "  - Structure/Patterns/Flows/Decisions/Context all present?",
                "  - Framing is understanding-focused (not auditing)?",
                "",
                "ADVANCE to confidence=certain for output.",
            ],
            "Output ready",
        )
    else:  # certain
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
            "Complete",
        )


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
        choices=CONFIDENCE_LEVELS,
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

    # Map step to actions
    if args.step == 1:
        title, actions, next_title = get_scope_actions(args.confidence)
    elif args.step == 2:
        title, actions, next_title = get_survey_actions(args.confidence)
    elif args.step == 3:
        title, actions, next_title = get_deepen_actions(args.confidence, args.iteration)
    else:  # step 4
        title, actions, next_title = get_synthesize_actions(args.confidence)

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
