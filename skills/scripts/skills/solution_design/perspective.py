#!/usr/bin/env python3
"""
Solution Design Perspective - Perspective-specific solution generation.

Two-step workflow per perspective:
  1. Generate  - Produce solutions using perspective-specific reasoning
  2. Validate  - Self-check solutions against quality criteria and format output
"""

import argparse
import sys

from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode
from skills.lib.workflow.types import FlatCommand
from skills.solution_design.perspectives import PERSPECTIVES, PERSPECTIVE_ORDER


# Module path for -m invocation
MODULE_PATH = "skills.solution_design.perspective"


# =============================================================================
# XML Formatters (perspective-specific)
# =============================================================================


def format_step_header(step: int, total: int, title: str, perspective: str) -> str:
    """Render step header with perspective context."""
    return render(
        W.el("step_header", TextNode(title),
            script="perspective", step=str(step), total=str(total), perspective=perspective
        ).build(),
        XMLRenderer()
    )


def format_solution_template() -> str:
    """Format the expected solution output structure."""
    return """<solution_format>
For each solution (1-3 solutions), output:

  <solution>
    <name>Brief descriptive name (3-7 words)</name>
    <what>What changes are made (concrete, specific)</what>
    <where>Which components/files/locations are affected</where>
    <mechanism>How this addresses the root cause</mechanism>
    <trade_offs>What you give up, costs incurred, complexity involved</trade_offs>
  </solution>

SOLUTION QUALITY REQUIREMENTS:
  - SPECIFIC: A reader could implement without asking clarifying questions
  - ACTIONABLE: Changes are concrete, not vague gestures like "improve X"
  - ADDRESSES ROOT CAUSE: Clear mechanism connecting solution to problem
  - NO TIME ESTIMATES: Do not include hours/days/weeks estimates

After all solutions, validate:

  <validation>
    <specific>yes | no | partial</specific>
    <actionable>yes | no | partial</actionable>
    <addresses_root_cause>yes | no | partial</addresses_root_cause>
  </validation>

  <summary count="N" quality="high | medium | low"/>
</solution_format>"""


def format_perspective_definition(perspective_id: str) -> str:
    """Format perspective definition for solution generation."""
    p = PERSPECTIVES[perspective_id]
    lines = [f'<perspective id="{perspective_id}">']
    lines.append(f"  <title>{p['title']}</title>")
    lines.append(f"  <core_question>{p['core_question']}</core_question>")
    lines.append("")
    lines.append("  <rationale>")
    lines.append(f"    {p['rationale']}")
    lines.append("  </rationale>")
    lines.append("")
    lines.append("  <generation_heuristics>")
    for h in p["generation_heuristics"]:
        lines.append(f"    <heuristic>{h}</heuristic>")
    lines.append("  </generation_heuristics>")
    lines.append("")
    lines.append("  <output_expectations>")
    lines.append(f"    {p['output_expectations']}")
    lines.append("  </output_expectations>")
    lines.append("</perspective>")
    return "\n".join(lines)


# =============================================================================
# Step Output
# =============================================================================


def format_step_1(perspective_id: str) -> str:
    """Format step 1: solution generation prompt."""
    p = PERSPECTIVES[perspective_id]

    actions = [
        f"PERSPECTIVE: {p['title']}",
        f"CORE QUESTION: {p['core_question']}",
        "",
        "YOUR TASK:",
        "Generate 1-3 solutions from THIS perspective only. Think from this perspective's",
        "reasoning mode--not comprehensively across all considerations.",
        "",
        "PERSPECTIVE DEFINITION:",
        "",
        format_perspective_definition(perspective_id),
        "",
        "GENERATION GUIDANCE:",
        "  - Follow the generation heuristics above",
        "  - Generate solutions that this perspective would UNIQUELY suggest",
        "  - Do not generate solutions any perspective would suggest",
        "  - It is acceptable to generate only 1 solution if that's what this perspective suggests",
        "  - Each solution must be CONCRETE and ACTIONABLE, not vague",
        "",
        "ROOT CAUSE CONTEXT:",
        "  The root cause should be in your context from the orchestrator.",
        "  If you don't have a root cause, STOP and report the error.",
        "",
        "SOLUTION REQUIREMENTS:",
        "  - WHAT: Specify concrete changes (not 'improve X' or 'add better Y')",
        "  - WHERE: Identify specific components, files, or locations",
        "  - MECHANISM: Explain HOW this addresses the root cause",
        "  - TRADE-OFFS: What costs, downsides, or complexity exists",
        "  - NO TIME ESTIMATES: Do not include hours/days/weeks",
        "",
        "EVALUATION CONTEXT:",
        "  Your dispatch prompt includes evaluation criteria (viability, flaw severity,",
        "  trade-off dimensions). When documenting TRADE-OFFS:",
        "  - Address the PRIMARY DIMENSIONS from those criteria",
        "  - If your solution might hit a SIGNIFICANT or FATAL condition, note it explicitly",
        "",
        "  This is NOT about being conservative. Explore your perspective fully.",
        "  But when you know a trade-off exists, name it using the criteria's terminology.",
        "",
        "Generate your solutions now, then proceed to validation.",
    ]

    xml_mandate = """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>
3. The <next> block re-states the command -- execute it
4. For branching <invoke_after>, choose based on outcome:
   - <if_pass>: Use when action succeeded / QR returned PASS
   - <if_fail>: Use when action failed / QR returned ISSUES
</xml_format_mandate>"""

    action_nodes = [TextNode(a) for a in actions]
    cmd_text = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 2 --total-steps 2 --perspective {perspective_id}" />'

    parts = [
        format_step_header(1, 2, "Generate", perspective_id),
        "",
        xml_mandate,
        "",
        render(W.el("current_action", *action_nodes).build(), XMLRenderer()),
        "",
        render(W.el("invoke_after", TextNode(cmd_text)).build(), XMLRenderer()),
    ]
    return "\n".join(parts)


def format_step_2(perspective_id: str) -> str:
    """Format step 2: validation and output."""
    p = PERSPECTIVES[perspective_id]

    actions = [
        f"PERSPECTIVE: {p['title']}",
        "",
        "VALIDATE AND FORMAT your solutions from Step 1.",
        "",
        "QUALITY CRITERIA:",
        "  SPECIFIC: Could someone implement this without asking clarifying questions?",
        "  ACTIONABLE: Are the changes concrete, or just vague gestures?",
        "  ADDRESSES ROOT CAUSE: Is there a clear mechanism connecting solution to problem?",
        "",
        "For each solution that fails a criterion:",
        "  - Either revise to meet the criterion",
        "  - Or remove if it cannot be made concrete",
        "",
        "EVALUATION CRITERIA CHECK:",
        "  Review the evaluation criteria from your dispatch context.",
        "  For each solution, note:",
        "  - Does it meet VIABILITY criteria? If uncertain, flag the uncertainty.",
        "  - Does it risk any FATAL conditions? If yes, either:",
        "      (a) Explain why it actually avoids the condition, OR",
        "      (b) Flag it explicitly: 'Risk: may trigger [condition] because [reason]'",
        "  - Are trade-offs documented on the PRIMARY DIMENSIONS?",
        "",
        "  DO NOT eliminate solutions just because they have risks.",
        "  Flag risks; let Challenge and Select handle evaluation.",
        "",
        format_solution_template(),
        "",
        f'OUTPUT your solutions now wrapped in <perspective_output id="{perspective_id}">.',
    ]

    action_nodes = [TextNode(a) for a in actions]

    parts = [
        format_step_header(2, 2, "Validate", perspective_id),
        "",
        render(W.el("current_action", *action_nodes).build(), XMLRenderer()),
        "",
        "COMPLETE - Return solutions to orchestrator.",
    ]
    return "\n".join(parts)


STEP_HANDLERS = {
    1: lambda perspective: format_step_1(perspective),
    2: lambda perspective: format_step_2(perspective),
}


def format_output(step: int, total_steps: int, perspective: str) -> str:
    """Format output for the given step."""
    handler = STEP_HANDLERS.get(step, lambda _: format_step_2(perspective))
    return handler(perspective)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Solution Design Perspective - Perspective-specific solution generation",
        epilog=f"Perspectives: {', '.join(PERSPECTIVE_ORDER)}",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument(
        "--perspective", type=str, required=True, choices=PERSPECTIVE_ORDER
    )

    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 2:
        sys.exit("ERROR: --total-steps must be >= 2")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps, args.perspective))


if __name__ == "__main__":
    main()
