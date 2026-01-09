#!/usr/bin/env python3
"""
Solution Design Skill - Perspective-parallel solution generation.

Seven-step workflow:
  1. Context    - Establish problem, constraints, success criteria
  2. Dispatch   - Select perspectives and launch parallel sub-agents
  3. Aggregate  - Collect solutions, deduplicate, build roster
  4. Synthesize - Analyze convergence/tension, generate cross-cutting solutions
  5. Challenge  - Stress-test all solutions (pure and synthesized equally)
  6. Select     - Rank, build trade-off matrix, produce recommendations
  7. Output     - Generate final report (plain text)

Design note: This skill generates solutions for a given root cause. It does NOT
identify problems or perform root cause analysis--that belongs upstream
(e.g., problem-analysis skill).
"""

import argparse
import sys

from skills.lib.workflow.formatters import (
    format_step_header,
    format_xml_mandate,
    format_current_action,
)
from skills.solution_design.perspectives import PERSPECTIVES, PERSPECTIVE_ORDER


# Module paths for -m invocation
MODULE_PATH = "skills.solution_design.design"
PERSPECTIVE_MODULE_PATH = "skills.solution_design.perspective"


def format_invoke_after(command: str) -> str:
    """Render invoke after block for design workflow."""
    return f"<invoke_after>\n{command}\n</invoke_after>"


# =============================================================================
# Perspective summaries for selection guidance
# =============================================================================

PERSPECTIVE_SUMMARIES = [
    ("minimal", "Minimal Intervention", "What is the smallest change that addresses the root cause?"),
    ("structural", "Structural/Comprehensive", "What design change would make this class of problem impossible?"),
    ("stateless", "Stateless/Functional", "What if we eliminated or dramatically simplified state?"),
    ("domain", "Domain-Modeled", "What concept from the problem domain are we failing to represent?"),
    ("removal", "Removal/Simplification", "What if we removed something instead of adding?"),
    ("firstprinciples", "First Principles", "If we derived from fundamental truths rather than convention, what solution emerges?"),
    ("upstream", "Upstream/Prevention", "What if we solved this at an earlier point in the causal chain?"),
]


# =============================================================================
# XML Formatters (design-specific)
# =============================================================================


def format_perspective_selection_guidance() -> str:
    """Format guidance for launching all perspectives."""
    lines = ['<perspective_dispatch>']
    lines.append("  Launch ALL perspectives in parallel.")
    lines.append("  Each perspective reasons differently; synthesis handles deduplication.")
    lines.append("</perspective_dispatch>")
    return "\n".join(lines)


def format_parallel_dispatch() -> str:
    """Format the parallel dispatch block for step 2."""
    lines = ['<parallel_dispatch agent="general-purpose">']
    lines.append("  <mandatory>")
    lines.append("    You MUST launch EXACTLY 7 sub-agents in a SINGLE message.")
    lines.append("    One agent for each perspective listed below. No selection. No filtering.")
    lines.append("    If you launch fewer than 7 agents, you have failed this step.")
    lines.append("  </mandatory>")
    lines.append("")
    lines.append("  <agents_to_launch>")
    for p_id, p_title, p_question in PERSPECTIVE_SUMMARIES:
        lines.append(f'    <agent perspective="{p_id}">')
        lines.append(f'      {p_title}: {p_question}')
        lines.append(f'    </agent>')
    lines.append("  </agents_to_launch>")
    lines.append("")
    lines.append("  <model_selection>")
    lines.append("    If user requested a specific model, use that for ALL agents.")
    lines.append("    Otherwise, default by perspective:")
    lines.append("      - HAIKU: minimal")
    lines.append("      - SONNET: structural, domain, stateless, removal, upstream")
    lines.append("      - OPUS: firstprinciples")
    lines.append("  </model_selection>")
    lines.append("")
    lines.append("  <agent_prompt_template>")
    lines.append("    Generate solutions for this root cause from the $PERSPECTIVE perspective.")
    lines.append("")
    lines.append("    ROOT CAUSE: [include verbatim from Step 1]")
    lines.append("    HARD CONSTRAINTS: [include from Step 1]")
    lines.append("")
    lines.append(f'    Start: <invoke working-dir=".claude/skills/scripts" cmd="python3 -m {PERSPECTIVE_MODULE_PATH} --step 1 --total-steps 2 --perspective $PERSPECTIVE_ID" />')
    lines.append("  </agent_prompt_template>")
    lines.append("</parallel_dispatch>")
    return "\n".join(lines)


def format_forbidden(actions: list[str]) -> str:
    """Render forbidden actions block."""
    lines = ["<forbidden>"]
    for action in actions:
        lines.append(f"  <action>{action}</action>")
    lines.append("</forbidden>")
    return "\n".join(lines)


def format_synthesis_analysis_template() -> str:
    """Format the synthesis analysis output structure."""
    return """<synthesis_output_format>
<convergence>
  <item solutions="A, B" aspect="Both propose validation at API boundary"/>
  <item solutions="C, D" aspect="Both suggest eliminating state"/>
</convergence>

<tensions>
  <item solutions="A, E" description="A adds guard clause; E removes code path producing the input"/>
  <item solutions="B, F" description="B adds complexity; F simplifies by removal"/>
</tensions>

<themes>
  <theme name="boundary validation" solutions="A, B, D" strength="strong"/>
  <theme name="state simplification" solutions="C, E" strength="moderate"/>
</themes>

<synthesized_solutions>
  <!-- Only if warranted. Zero is a valid outcome. -->
  <solution>
    <name>Combined boundary + simplification approach</name>
    <inspired_by>Theme: boundary validation (A, B, D) + stateless insight (C)</inspired_by>
    <what>...</what>
    <where>...</where>
    <mechanism>...</mechanism>
    <effort>...</effort>
    <trade_offs>...</trade_offs>
  </solution>
</synthesized_solutions>
</synthesis_output_format>"""


def format_final_report_template() -> str:
    """Format the final report structure (plain text)."""
    return """
================================================================================
                         SOLUTION DESIGN REPORT
================================================================================

ROOT CAUSE:
[verbatim from Step 1]

CONSTRAINTS:
  Hard: [list]
  Soft: [list]

SUCCESS CRITERIA:
[how we know the solution worked]

COST OF INACTION:
[what happens if we don't fix this]

--------------------------------------------------------------------------------

SYNTHESIS INSIGHTS:

  Convergence: [where perspectives agreed]
  Tensions: [where perspectives conflicted]
  Themes: [patterns across solutions]

--------------------------------------------------------------------------------

SOLUTIONS:

  [1] SOLUTION NAME [STATUS: recommended | viable | conditional]
      Perspective: [source or "synthesized from X, Y"]
      Description: [what changes]
      Location: [where]
      Mechanism: [how it addresses root cause]
      Trade-offs: [what you give up, including complexity]
      Weaknesses: [from challenge phase]

  [2] ...

  ELIMINATED:
  - [name]: [reason]

--------------------------------------------------------------------------------

TRADE-OFF MATRIX:

  | Solution       | Complexity | Risk | Reversibility | Scope  |
  |----------------|------------|------|---------------|--------|
  | Solution #1    | low        | low  | high          | local  |
  | ...            |            |      |               |        |

--------------------------------------------------------------------------------

DECISION FRAMEWORK:

  If [priority] is paramount -> [solution] because [reason]
  If [priority] is paramount -> [solution] because [reason]
  ...

--------------------------------------------------------------------------------

RECOMMENDATION:

[explicit recommendation or "No clear winner - key discriminating factor is X"]

================================================================================
""".strip()


# =============================================================================
# Step Definitions
# =============================================================================


STEPS = {
    1: {
        "title": "Context",
        "brief": "Establish problem, constraints, success criteria",
        "actions": [
            "ESTABLISH THE PROBLEM CONTEXT",
            "",
            "1. CHECK FOR ROOT CAUSE INPUT:",
            "   - Look for problem-analysis output in context (ROOT CAUSE section)",
            "   - Or user-provided problem statement",
            "   - If NO root cause found: STOP and ask for clarification using AskUserQuestion",
            "",
            "2. EXTRACT OR CONFIRM ROOT CAUSE:",
            "   - State the root cause clearly (what condition exists that causes the problem)",
            "   - Root cause should be a POSITIVE CONDITION, not an absence",
            "   - WRONG: 'Missing validation' (prescribes solution)",
            "   - RIGHT: 'User input reaches SQL query unsanitized' (describes condition)",
            "",
            "3. IDENTIFY CONSTRAINTS:",
            "   HARD constraints (non-negotiable):",
            "     - Time limits, budget limits",
            "     - Compatibility requirements",
            "     - Safety requirements",
            "     - Regulatory requirements",
            "",
            "   SOFT constraints (preferences, can trade off):",
            "     - Performance targets",
            "     - Elegance, team familiarity",
            "     - Consistency with existing patterns",
            "",
            "4. ESTABLISH SUCCESS CRITERIA:",
            "   - How will we know the solution worked?",
            "   - What observations or measurements indicate success?",
            "",
            "5. ESTABLISH 'DO NOTHING' BASELINE:",
            "   - What happens if we don't fix this?",
            "   - What is the cost of inaction?",
            "   - This becomes the comparison point for all solutions",
            "",
            "OUTPUT (structured for subsequent steps):",
            "  ROOT_CAUSE: [the condition to address]",
            "  HARD_CONSTRAINTS: [list]",
            "  SOFT_CONSTRAINTS: [list]",
            "  SUCCESS_CRITERIA: [how we know it worked]",
            "  COST_OF_INACTION: [what happens if we don't fix]",
        ],
    },
    2: {
        "title": "Dispatch",
        "brief": "Launch all perspectives as parallel sub-agents",
        "needs_dispatch": True,  # Flag for format_output
    },
    3: {
        "title": "Aggregate",
        "brief": "Collect solutions, deduplicate, build roster",
        "actions": [
            "COLLECT AND ORGANIZE SOLUTIONS",
            "",
            "This step is MECHANICAL. Do NOT evaluate quality or identify patterns.",
            "Those responsibilities belong to subsequent steps.",
            "",
            "1. COLLECT all solutions from all perspective sub-agents",
            "   - Each perspective produces 1-3 solutions in structured format",
            "   - Preserve all solution details (what, where, mechanism, effort, trade-offs)",
            "",
            "2. DEDUPLICATE:",
            "   - Identify solutions that are the SAME APPROACH with different phrasing",
            "   - When merging duplicates, PRESERVE ATTRIBUTION:",
            "     'Proposed by: minimal, upstream' (shows convergence)",
            "   - Note: Convergence is INFORMATION, not automatic priority boost",
            "",
            "3. BUILD SOLUTION ROSTER:",
            "   - Flat list of distinct solutions",
            "   - Each tagged with source perspective(s)",
            "   - Sequential numbering for reference",
            "",
            "4. VERIFY COVERAGE:",
            "   - Check: Do we have at least one solution from each dispatched perspective?",
            "   - If a perspective sub-agent failed or produced nothing, NOTE THE GAP",
            "",
            format_forbidden([
                "Do NOT evaluate solution quality",
                "Do NOT identify patterns or themes",
                "Do NOT rank or prioritize",
                "Do NOT eliminate any solutions",
            ]),
            "",
            "OUTPUT:",
            "  SOLUTION_ROSTER: [numbered list of distinct solutions with perspective attribution]",
            "  GAPS: [any perspectives that produced no solutions]",
        ],
    },
    4: {
        "title": "Synthesize",
        "brief": "Analyze convergence/tension, generate cross-cutting solutions",
        "actions": [
            "ANALYZE SOLUTION RELATIONSHIPS AND GENERATE CROSS-CUTTING SOLUTIONS",
            "",
            "1. ANALYZE CONVERGENCE:",
            "   - Which solutions from DIFFERENT perspectives point to the same approach?",
            "   - Document: 'Solutions A and B both propose X'",
            "   - Convergence is evidence of robust insight (emerged from different reasoning)",
            "   - BUT: Convergence does NOT automatically elevate priority",
            "",
            "2. ANALYZE TENSION:",
            "   - Which solutions CONFLICT or represent different approaches to the same aspect?",
            "   - Example: Minimal='add guard clause' vs Removal='eliminate code path'",
            "   - Document tensions explicitly--they are VALUABLE INFO for user's decision",
            "   - Do NOT try to resolve tensions; surface them",
            "",
            "3. IDENTIFY THEMES:",
            "   - What concepts appear across MULTIPLE solutions even when solutions differ?",
            "   - Look for: 'boundary validation', 'state isolation', 'type safety'",
            "   - Themes appearing in 3+ solutions are SYNTHESIS CANDIDATES",
            "",
            "4. GENERATE CROSS-CUTTING SOLUTIONS (IF WARRANTED):",
            "   For each strong theme, ask:",
            "   'Is there a solution that fully embodies this theme in a way no single",
            "    perspective captured?'",
            "",
            "   IF YES: Articulate with SAME SPECIFICITY as pure solutions:",
            "     - what, where, mechanism, effort, trade-offs",
            "     - Tag as 'synthesized' with attribution to inspiring solutions",
            "",
            "   IF NO: Document 'No cross-cutting solutions generated'",
            "   This is a VALID and COMMON outcome. Do not force artificial combinations.",
            "",
            format_synthesis_analysis_template(),
            "",
            "CRITICAL CONSTRAINTS:",
            format_forbidden([
                "Do NOT remove any pure solutions",
                "Do NOT rank or prioritize solutions",
                "Do NOT elevate synthesized solutions over pure ones",
                "Synthesized solutions are HYPOTHESES, not conclusions",
            ]),
            "",
            "OUTPUT:",
            "  CONVERGENCE: [which solutions agreed, on what]",
            "  TENSIONS: [which solutions conflict, how]",
            "  THEMES: [patterns across solutions]",
            "  SYNTHESIZED_SOLUTIONS: [0-2 cross-cutting solutions if warranted]",
            "  ENRICHED_ROSTER: [all pure solutions + any synthesized solutions]",
        ],
    },
    5: {
        "title": "Challenge",
        "brief": "Stress-test all solutions (pure and synthesized equally)",
        "actions": [
            "STRESS-TEST ALL SOLUTIONS",
            "",
            "For EACH solution in the enriched roster (pure AND synthesized):",
            "",
            "APPLY ADVERSARIAL SCRUTINY:",
            "  1. What inputs or conditions would cause this to FAIL?",
            "  2. What is the STRONGEST ARGUMENT against this solution?",
            "  3. What HIDDEN COMPLEXITY or COST isn't captured in the description?",
            "  4. What SECOND-ORDER EFFECTS might this create?",
            "  5. Does this actually ADDRESS THE ROOT CAUSE or merely treat symptoms?",
            "",
            "CATEGORIZE ISSUES FOUND:",
            "  FATAL: Invalidates the solution under stated constraints",
            "         -> Mark solution as ELIMINATED with reason",
            "  SIGNIFICANT: Real problem that affects viability",
            "         -> Document issue, solution remains VIABLE WITH ISSUES",
            "  MINOR: Downside but manageable",
            "         -> Note as trade-off, solution remains VIABLE",
            "",
            "UPDATE SOLUTION STATUS:",
            "  ELIMINATED: Fatal flaw found (document reason)",
            "  VIABLE: Passed challenge (may have documented issues)",
            "",
            "COVERAGE CHECK:",
            "  - Ensure at least 2 viable solutions remain",
            "  - If ALL solutions eliminated: document why, note that constraints may",
            "    need relaxation or problem needs reframing",
            "",
            "CRITICAL: Pure and synthesized solutions are challenged IDENTICALLY.",
            "          Origin does not affect scrutiny level.",
            "",
            "OUTPUT:",
            "  CHALLENGED_ROSTER: [each solution with status and findings]",
            "  ELIMINATED: [solutions with fatal flaws + reasons]",
            "  VIABLE: [solutions that survived challenge]",
        ],
    },
    6: {
        "title": "Select",
        "brief": "Rank, build trade-off matrix, produce recommendations",
        "actions": [
            "EVALUATE AND PRODUCE RECOMMENDATIONS",
            "",
            "1. RANK SURVIVING SOLUTIONS:",
            "   - Order by overall viability given stated constraints",
            "   - Document ranking criteria used",
            "   - Origin (pure vs synthesized) does NOT factor into ranking",
            "",
            "2. BUILD TRADE-OFF MATRIX:",
            "   For each dimension that matters (based on constraints):",
            "",
            "   | Solution    | Complexity | Risk | Reversibility | Scope | [other dims] |",
            "   |-------------|------------|------|---------------|-------|--------------|",
            "   | Solution #1 | low        | low  | high          | local | ...          |",
            "",
            "   Typical dimensions: complexity, risk, reversibility, scope of change",
            "   Add problem-specific dimensions as relevant",
            "   Do NOT include time estimates (hours/days/weeks)",
            "",
            "3. NOTE CONVERGENCE AND TENSION:",
            "   - From synthesis analysis, surface for user's consideration",
            "   - If multiple perspectives proposed a solution, note as corroborating evidence",
            "   - If solutions represent genuine tensions, highlight the choice",
            "",
            "4. PRODUCE DECISION FRAMEWORK:",
            "   Conditional recommendations:",
            "",
            "   'If [priority] is paramount -> [solution] because [reason]'",
            "",
            "   Include 3-5 conditionals covering main priority trade-offs",
            "",
            "5. MAKE EXPLICIT RECOMMENDATION:",
            "   - If one solution clearly dominates (better on most dimensions,",
            "     not worse on any): Recommend it explicitly",
            "   - If no clear winner: Say so and identify the KEY DISCRIMINATING FACTOR",
            "     the user must decide based on their priorities",
            "",
            "6. COMPARE TO 'DO NOTHING' BASELINE:",
            "   - What is gained by implementing vs not implementing?",
            "   - If cost of inaction is low and solutions are high-effort,",
            "     doing nothing might be the right choice",
            "",
            "OUTPUT:",
            "  RANKED_SOLUTIONS: [ordered list with ranking rationale]",
            "  TRADE_OFF_MATRIX: [table comparing solutions on key dimensions]",
            "  DECISION_FRAMEWORK: [conditional recommendations]",
            "  RECOMMENDATION: [explicit recommendation or key discriminating factor]",
        ],
    },
    7: {
        "title": "Output",
        "brief": "Generate final report (plain text)",
        "actions": [
            "GENERATE FINAL REPORT",
            "",
            "Produce the final Solution Design Report in PLAIN TEXT format.",
            "This report should be self-contained and actionable.",
            "",
            "CRITICAL - SOLUTION NUMBERING:",
            "  - Renumber ALL solutions sequentially: #1, #2, #3, etc.",
            "  - Use ONLY these final numbers throughout the ENTIRE report",
            "  - DROP any internal identifiers from earlier steps (S1, S2, etc.)",
            "  - In SOLUTIONS section: use [1], [2], [3]",
            "  - In TRADE-OFF MATRIX: use 'Solution #1', 'Solution #2'",
            "  - In DECISION FRAMEWORK: use '#1', '#2' or solution NAME",
            "  - In RECOMMENDATION: use '#1', '#2' or solution NAME",
            "  - NEVER reference identifiers the reader hasn't seen defined",
            "",
            format_final_report_template(),
            "",
            "ENSURE THE REPORT INCLUDES:",
            "  - Root cause (verbatim from Step 1)",
            "  - All constraints (hard and soft)",
            "  - Success criteria",
            "  - Cost of inaction baseline",
            "  - Synthesis insights (convergence, tensions, themes)",
            "  - All viable solutions with full details",
            "  - Eliminated solutions with reasons",
            "  - Trade-off matrix",
            "  - Decision framework (conditional recommendations)",
            "  - Explicit recommendation (or key discriminating factor)",
            "",
            "Present the report to the user.",
        ],
    },
}


# =============================================================================
# Output Formatting
# =============================================================================


def format_output(step: int, total_steps: int) -> str:
    """Format output for display."""
    info = STEPS.get(step, STEPS[7])
    is_complete = step >= total_steps

    parts = []

    # Step header
    parts.append(format_step_header("design", step, total_steps, info["title"]))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        parts.append(format_xml_mandate())
        parts.append("")

    # Build actions
    actions = []

    if step == 2:
        # Step 2: Launch all perspectives in parallel
        actions.append("DISPATCH ALL PERSPECTIVE SUB-AGENTS")
        actions.append("")
        actions.append("Using the ROOT_CAUSE and CONSTRAINTS from Step 1:")
        actions.append("")
        actions.append(format_perspective_selection_guidance())
        actions.append("")
        actions.append(format_parallel_dispatch())
        actions.append("")
        actions.append("WAIT for all perspective agents to complete before proceeding.")
    else:
        # Other steps use actions from STEPS dict
        if "actions" in info:
            actions.extend(info["actions"])

    parts.append(format_current_action(actions))
    parts.append("")

    # Invoke after
    if is_complete:
        parts.append("COMPLETE - Present final report to user.")
    else:
        next_step = step + 1
        parts.append(format_invoke_after(
            f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step {next_step} --total-steps {total_steps}" />'
        ))

    return "\n".join(parts)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Solution Design Skill - Perspective-parallel solution generation",
        epilog="Steps: context -> dispatch -> aggregate -> synthesize -> challenge -> select -> output",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 7:
        sys.exit("ERROR: --total-steps must be >= 7 (7 steps in workflow)")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps))


if __name__ == "__main__":
    main()
