#!/usr/bin/env python3
"""
5-step exploration workflow for decision-relevant context discovery.

Steps:
  1. Exploration Planning - parse decision criteria into investigation targets
  2. Execute Exploration - gather findings with decision-relevant depth
  3. Gap Analysis - check coverage against decision criteria
  4. Fill Gaps - additional exploration for uncovered criteria
  5. Format Output - compress into structured XML for main agent
"""

import argparse
import sys
from pathlib import Path

from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode


# Module path for -m invocation
MODULE_PATH = "skills.planner.explore"


DECISION_CRITERIA = """\
Step 3 (Approach Generation) needs:
  - Existing patterns to compare approaches (minimal vs idiomatic)
  - Constraints that favor one approach over another
  - Complexity factors for each approach

Step 4 (Assumption Surfacing) needs:
  - Ambiguities requiring user confirmation
  - Policy defaults encountered (timeouts, retries, etc.)
  - Architectural choices with multiple valid options

Step 5 (Milestone Planning) needs:
  - Files to modify (exact paths, purpose of each)
  - Failure modes and risks
  - Testable behaviors for acceptance criteria
  - Existing test coverage and patterns
"""


def get_output_schema() -> str:
    """Read the output format schema from resources."""
    format_path = Path(__file__).parent.parent / "resources" / "explore-output-format.md"
    if format_path.exists():
        return format_path.read_text()
    # Inline fallback if resource file not found
    return """\
<exploration_output task="[task]">
  <approach_inputs>
    <patterns><pattern name="" location="">[description]</pattern></patterns>
    <constraints><constraint impact="">[description]</constraint></constraints>
  </approach_inputs>
  <assumption_inputs>
    <ambiguities><ambiguity needs_confirmation="">[description]</ambiguity></ambiguities>
    <implicit_policies><policy area="">[description]</policy></implicit_policies>
  </assumption_inputs>
  <milestone_inputs>
    <files><file path="" purpose="">[description]</file></files>
    <failure_modes><failure risk="">[description]</failure></failure_modes>
    <test_coverage>
      <tests path="" type="">[description]</tests>
      <gaps>[description]</gaps>
    </test_coverage>
  </milestone_inputs>
</exploration_output>
"""


STEPS = {
    1: {
        "title": "Exploration Planning",
        "actions": [
            "You have been dispatched to explore the codebase for planning context.",
            "",
            "<decision_criteria>",
            DECISION_CRITERIA,
            "</decision_criteria>",
            "",
            "Parse the TASK into exploration questions guided by these criteria.",
            "",
            "For EACH consumer step, write specific investigation targets:",
            "  Step 3 (Approaches): What patterns exist? What constraints apply?",
            "  Step 4 (Assumptions): What's ambiguous? What policies are implicit?",
            "  Step 5 (Milestones): What files? What can fail? What's testable?",
            "",
            "OUTPUT: Numbered list of exploration targets with priority.",
            "  HIGH: Directly answers a decision criterion",
            "  MEDIUM: Provides context for decisions",
            "  LOW: Nice to have but not decision-critical",
            "",
            "Focus on HIGH priority targets. Skip LOW priority entirely.",
        ],
    },
    2: {
        "title": "Execute Exploration",
        "actions": [
            "Execute HIGH and MEDIUM priority explorations from step 1.",
            "",
            "For each target:",
            "  - Use appropriate tools (Glob, Grep, Read)",
            "  - Document findings with file:line references",
            "  - Capture HOW patterns work, not just THAT they exist",
            "",
            "DEPTH GUIDANCE:",
            "  If a pattern is relevant to approach comparison:",
            "    -> understand its constraints and tradeoffs",
            "  If a file will be modified:",
            "    -> understand its role, dependencies, key functions",
            "  If tests exist:",
            "    -> understand what behaviors they verify, what patterns they use",
            "",
            "OUTPUT: Raw findings organized by exploration target.",
        ],
    },
    3: {
        "title": "Gap Analysis",
        "actions": [
            "RE-READ the decision criteria:",
            "",
            "<decision_criteria>",
            DECISION_CRITERIA,
            "</decision_criteria>",
            "",
            "These criteria are the ONLY measure of completeness.",
            "",
            "For EACH criterion, assess against your findings:",
            "",
            "  Step 3 needs (Approach Generation):",
            "    [ ] Patterns for approach comparison?",
            "    [ ] Constraints favoring one approach?",
            "    [ ] Complexity factors?",
            "",
            "  Step 4 needs (Assumption Surfacing):",
            "    [ ] Ambiguities requiring confirmation?",
            "    [ ] Implicit policies encountered?",
            "    [ ] Architectural choices with options?",
            "",
            "  Step 5 needs (Milestone Planning):",
            "    [ ] Files with purposes?",
            "    [ ] Failure modes?",
            "    [ ] Testable behaviors?",
            "    [ ] Existing test coverage?",
            "",
            "Mark each: [COVERED] | [PARTIAL] | [GAP]",
            "",
            "For PARTIAL and GAP items ONLY, write targeted exploration:",
            "  - What specific question needs answering?",
            "  - Where to look?",
            "  - What depth is needed?",
            "",
            "DO NOT explore things outside the decision criteria.",
            "If all criteria are COVERED: state 'No gaps - skip step 4, proceed to step 5'",
        ],
    },
    4: {
        "title": "Fill Gaps",
        "actions": [
            "If step 3 found no gaps: Skip to step 5 immediately.",
            "",
            "Execute additional explorations from step 3's gap analysis:",
            "  - Focus on decision-critical gaps only",
            "  - Merge findings with step 2 results",
            "",
            "OUTPUT: Combined findings (step 2 + step 4 additions).",
        ],
    },
    5: {
        "title": "Format Output",
        "include_output_format": True,
        "actions": [
            "Structure findings using the XML output schema below.",
            "",
            "DECISION CRITERIA ARE THE FILTER:",
            "  The decision criteria determine what survives compression.",
            "",
            "<decision_criteria>",
            DECISION_CRITERIA,
            "</decision_criteria>",
            "",
            "FORBIDDEN:",
            "  - Including information IRRELEVANT to decision criteria",
            "    (wastes main agent context on noise)",
            "  - Removing information RELEVANT to decision criteria",
            "    (forces main agent to re-explore or guess)",
            "",
            "FOR EACH FINDING, ASK:",
            "  'Does this help the planner with approach comparison,",
            "   assumption surfacing, or milestone planning?'",
            "  YES -> include with sufficient context",
            "  NO  -> exclude entirely",
            "  MAYBE -> include if space permits, exclude if tight",
            "",
            "COMPRESSION TECHNIQUE:",
            "  - Merge redundant information",
            "  - Keep file:line references for verifiable claims",
            "  - Patterns: HOW they work, not just THAT they exist",
            "",
            "TOKEN BUDGET (ENFORCED - not soft guidance):",
            "  - Total return: MAX 1500 tokens",
            "  - Per section: MAX 500 tokens",
            "  - Per finding: MAX 50 tokens",
            "",
            "  VERBOSE (wrong): 'The module implements a factory pattern that",
            "                    creates service instances, enabling DI...'",
            "  DRAFT (right):   'Factory pattern -> DI + testability'",
            "",
            "  If findings exceed budget, OMIT low-relevance items.",
            "",
            "OUTPUT: XML-formatted exploration output using this schema:",
            "",
            # Output schema will be appended by format_output
        ],
    },
}


def step_5_handler(step_info, total_steps):
    """Handler for step 5 (include output schema)."""
    actions = list(step_info.get("actions", []))
    schema = get_output_schema()
    actions.append("<output_schema>")
    actions.append(schema)
    actions.append("</output_schema>")
    return {
        "title": step_info["title"],
        "actions": actions,
        "next": None,
    }


def generic_step_handler(step_info, step, total_steps):
    """Generic handler for standard steps."""
    actions = list(step_info.get("actions", []))
    next_cmd = None
    if step < total_steps:
        next_cmd = f"python3 -m {MODULE_PATH} --step {step + 1} --total-steps {total_steps}"
    return {
        "title": step_info["title"],
        "actions": actions,
        "next": next_cmd,
    }


STEP_HANDLERS = {
    5: step_5_handler,
}


def get_step_guidance(step: int, total_steps: int) -> dict:
    """Return guidance dict for the specified step."""
    info = STEPS.get(step)
    if not info:
        return {"error": f"Invalid step {step}"}

    handler = STEP_HANDLERS.get(step, generic_step_handler)
    if step == 5:
        return handler(info, total_steps)
    else:
        return handler(info, step, total_steps)


def format_output(step: int, total_steps: int) -> str:
    """Format step output using XML format."""
    guidance = get_step_guidance(step, total_steps)

    if "error" in guidance:
        return f"Error: {guidance['error']}"

    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(guidance["title"]),
            script="explore", step=str(step), total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        parts.append("<xml_format_mandate>")
        parts.append("CRITICAL: All script outputs use XML format. You MUST:")
        parts.append("")
        parts.append("1. Execute the action in <current_action>")
        parts.append("2. When complete, invoke the exact command in <invoke_after>")
        parts.append("3. The <next> block re-states the command -- execute it")
        parts.append("4. For branching <invoke_after>, choose based on outcome:")
        parts.append("   - <if_pass>: Use when action succeeded / QR returned PASS")
        parts.append("   - <if_fail>: Use when action failed / QR returned ISSUES")
        parts.append("")
        parts.append("DO NOT modify commands. DO NOT skip steps. DO NOT interpret.")
        parts.append("</xml_format_mandate>")
        parts.append("")
        parts.append("<thinking_efficiency>")
        parts.append("Max 5 words per step. Symbolic notation preferred.")
        parts.append('Good: "Patterns needed -> grep auth -> found 3"')
        parts.append('Bad: "For the patterns we need, let me search for auth..."')
        parts.append("</thinking_efficiency>")
        parts.append("")

    # Current action
    action_nodes = [TextNode(a) for a in guidance["actions"]]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))

    # Invoke after and next block
    next_command = guidance.get("next")
    if next_command:
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

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="5-step exploration workflow for decision-relevant context discovery",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)

    args = parser.parse_args()

    if args.step < 1 or args.total_steps < 1:
        print("Error: step and total-steps must be >= 1", file=sys.stderr)
        sys.exit(1)

    if args.total_steps < 5:
        print("Error: workflow requires at least 5 steps", file=sys.stderr)
        sys.exit(1)

    print(format_output(args.step, args.total_steps))


if __name__ == "__main__":
    main()
