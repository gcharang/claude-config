#!/usr/bin/env python3
"""
Solution Design Skill - Perspective-parallel solution generation.

Nine-step workflow:
  1. Context    - Establish problem, constraints, success criteria
  2. Calibrate  - Infer evaluation criteria from problem + project + defaults
  3. Reflect    - Validate inferred criteria, resolve conflicts, finalize
  4. Dispatch   - Select perspectives and launch parallel sub-agents
  5. Aggregate  - Collect solutions, deduplicate, build roster
  6. Synthesize - Analyze convergence/tension, generate cross-cutting solutions
  7. Challenge  - Stress-test all solutions (pure and synthesized equally)
  8. Select     - Rank, build trade-off matrix, produce recommendations
  9. Output     - Generate final report (plain text)

Design note: This skill generates solutions for a given root cause. It does NOT
identify problems or perform root cause analysis--that belongs upstream
(e.g., problem-analysis skill).
"""

import argparse
import sys
from typing import Annotated

from skills.lib.workflow.core import (
    Workflow,
    StepDef,
    StepContext,
    Outcome,
    Arg,
)
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode, ElementNode
from skills.lib.workflow.types import FlatCommand
from skills.solution_design.perspectives import PERSPECTIVES, PERSPECTIVE_ORDER
from skills.solution_design.defaults import format_all_defaults


# Module paths for -m invocation
MODULE_PATH = "skills.solution_design.design"
PERSPECTIVE_MODULE_PATH = "skills.solution_design.perspective"




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


AGENT_PROMPT_TEMPLATE = """Generate solutions for this root cause from the $PERSPECTIVE perspective.

ROOT CAUSE: [include verbatim from Step 1]
HARD CONSTRAINTS: [include from Step 1]

EVALUATION CRITERIA (from Step 3 - FINALIZED_CRITERIA):
These criteria will be used to evaluate your solutions. Use them to:
- Avoid proposing solutions with obviously fatal flaws
- Flag risks that match significant/minor conditions
- Be explicit about trade-offs on the weighted dimensions

VIABILITY:
  [Include viability criteria from FINALIZED_CRITERIA]
  A solution must meet ALL these criteria to be considered viable.

FLAW SEVERITY:
  FATAL (solution will be eliminated):
    [List fatal conditions from FINALIZED_CRITERIA]

  SIGNIFICANT (solution viable but with documented issues):
    [List significant conditions from FINALIZED_CRITERIA]

  MINOR (noted as trade-off):
    [List minor conditions from FINALIZED_CRITERIA]

TRADEOFF DIMENSIONS:
  PRIMARY (weighted in ranking):
    [List primary dimensions with weights from FINALIZED_CRITERIA]

  When describing trade-offs, address these dimensions explicitly.

GUIDANCE:
- Still explore your perspective FULLY--do not only generate 'safe' solutions
- If your perspective suggests something that might hit a fatal condition,
  either explain why it doesn't, or note the risk explicitly
- Be specific about how your solutions perform on the primary trade-off dimensions"""


# =============================================================================
# XML Formatters (design-specific)
# =============================================================================


def format_perspective_selection_guidance() -> str:
    """Format guidance for launching all perspectives."""
    return render(
        W.el("perspective_dispatch",
            TextNode("Launch ALL perspectives in parallel."),
            TextNode("Each perspective reasons differently; synthesis handles deduplication.")
        ).build(),
        XMLRenderer()
    )


def build_perspective_dispatch() -> str:
    """Build parallel dispatch block for perspective agents."""
    agents = [
        {"id": p_id, "title": p_title, "task": p_question}
        for p_id, p_title, p_question in PERSPECTIVE_SUMMARIES
    ]
    model_per_agent = {"minimal": "HAIKU", "firstprinciples": "OPUS"}
    invoke_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {PERSPECTIVE_MODULE_PATH} --step 1 --total-steps 2 --perspective $PERSPECTIVE_ID" />'

    lines = [f'<parallel_dispatch agent="general-purpose" count="{len(agents)}">']

    lines.append("  <mandatory>")
    lines.append("    You MUST launch EXACTLY 7 sub-agents in a SINGLE message.")
    lines.append("    If you launch fewer agents, you have failed this step.")
    lines.append("  </mandatory>")
    lines.append("")

    lines.append("  <instruction>")
    instruction = "Launch ALL perspective agents listed below.\nOne agent for each perspective. No selection. No filtering."
    for line in instruction.split("\n"):
        lines.append(f"    {line}" if line else "")
    lines.append("  </instruction>")
    lines.append("")

    lines.append("  <model_selection>")
    lines.append("    Use SONNET (default) for all agents.")
    lines.append("    Per-agent overrides:")
    for agent_id, agent_model in model_per_agent.items():
        lines.append(f"      - {agent_model}: {agent_id}")
    lines.append("  </model_selection>")
    lines.append("")

    lines.append("  <agents_to_launch>")
    for a in agents:
        agent_id = a.get("id", "")
        lines.append(f'    <agent perspective="{agent_id}">')
        if "title" in a:
            lines.append(f"      {a['title']}: {a.get('task', '')}")
        elif "task" in a:
            lines.append(f"      {a['task']}")
        lines.append("    </agent>")
    lines.append("  </agents_to_launch>")
    lines.append("")

    lines.append("  <agent_prompt_template>")
    for line in AGENT_PROMPT_TEMPLATE.split("\n"):
        lines.append(f"    {line}" if line else "")
    lines.append("")
    lines.append(f"    Start: {invoke_cmd}")
    lines.append("  </agent_prompt_template>")

    lines.append("</parallel_dispatch>")

    return "\n".join(lines)


def format_forbidden(actions: list[str]) -> str:
    """Render forbidden actions block."""
    action_nodes = [ElementNode("action", {}, [TextNode(a)]) for a in actions]
    return render(W.el("forbidden", *action_nodes).build(), XMLRenderer())


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
        "title": "Calibrate",
        "brief": "Infer evaluation criteria from problem + project + defaults",
        "actions": [
            "CALIBRATE EVALUATION CRITERIA",
            "",
            "Before generating and evaluating solutions, establish the criteria that will be used",
            "to assess them. This ensures consistent, context-appropriate evaluation.",
            "",
            "INPUT: Root cause, constraints, and success criteria from Step 1.",
            "",
            "INFERENCE HIERARCHY (in priority order):",
            "  1. PROBLEM INFERENCE: What does the problem statement imply about evaluation?",
            "  2. PROJECT INFERENCE: What does the project context suggest? (if available)",
            "  3. DEFAULT CONVENTIONS: Fallback when no specific inference possible",
            "",
            "INFER EACH OF THE FOLLOWING:",
            "",
            "1. VIABILITY DEFINITION",
            "   What makes a solution 'viable' for THIS problem?",
            "",
            "   Problem signals to look for:",
            "   - Urgency indicators (production, blocking, critical) -> speed matters",
            "   - Scope indicators (architectural, long-term, foundation) -> thoroughness matters",
            "   - Domain indicators (security, performance, reliability) -> domain excellence matters",
            "",
            "   Default if no signals:",
            "   - Addresses root cause through clear mechanism",
            "   - Respects all hard constraints",
            "   - Is implementable with reasonable effort",
            "",
            "2. FLAW SEVERITY WEIGHTING",
            "   What makes a flaw fatal vs significant vs minor for THIS problem?",
            "",
            "   Problem type determines severity:",
            "   - Security problem -> security regressions are FATAL, not significant",
            "   - Performance problem -> performance overhead weighted more severely",
            "   - Reliability problem -> failure modes are FATAL",
            "   - Maintainability problem -> complexity weighted more severely",
            "",
            "   Hard constraints from Step 1:",
            "   - Each hard constraint violation -> FATAL",
            "",
            "   Default categorization:",
            "   - FATAL: Doesn't address root cause, violates hard constraint, creates worse problem",
            "   - SIGNIFICANT: Substantial soft-constraint violation, requires unavailable resources",
            "   - MINOR: Manageable downside, acceptable complexity increase",
            "",
            "3. TRADE-OFF DIMENSIONS",
            "   Which dimensions should the trade-off matrix include for THIS problem?",
            "",
            "   Extract from problem and constraints:",
            "   - Each soft constraint suggests a dimension",
            "   - Problem type suggests primary dimensions",
            "",
            "   Default dimensions (always consider):",
            "   - Complexity, Risk, Reversibility, Scope",
            "",
            "   Assign weights (high/medium/low) based on problem priorities.",
            "",
            "4. SYNTHESIS THRESHOLD",
            "   How aggressively should we synthesize cross-cutting solutions?",
            "",
            "   Problem complexity determines appetite:",
            "   - Simple, focused -> conservative (3+ solutions, strong theme)",
            "   - Complex, multi-faceted -> moderate (2+ solutions, moderate theme)",
            "   - Exploratory -> aggressive (2+ solutions, any pattern)",
            "",
            "   Default: conservative",
            "",
            "DEFAULT CRITERIA (use as fallback when inference produces nothing):",
            "",
            format_all_defaults(),
            "",
            "OUTPUT your inferred criteria in the following format.",
            "Tag each criterion with its source (problem, project, or default).",
            "Include rationale explaining WHY each inference fits this problem.",
            "",
            "<evaluation_criteria>",
            "  <viability_definition>",
            "    <source>problem | project | default</source>",
            "    <criteria>",
            "      <criterion>...</criterion>",
            "    </criteria>",
            "    <rationale>Why these criteria fit this problem</rationale>",
            "  </viability_definition>",
            "",
            "  <flaw_severity>",
            "    <source>problem | project | default</source>",
            "    <fatal_conditions>",
            "      <condition>...</condition>",
            "    </fatal_conditions>",
            "    <significant_conditions>",
            "      <condition>...</condition>",
            "    </significant_conditions>",
            "    <minor_conditions>",
            "      <condition>...</condition>",
            "    </minor_conditions>",
            "    <rationale>Why this severity weighting fits this problem</rationale>",
            "  </flaw_severity>",
            "",
            "  <tradeoff_dimensions>",
            "    <source>problem | project | default</source>",
            "    <primary_dimensions>",
            '      <dimension name="..." weight="high | medium | low">',
            "        <why>Explanation of why this dimension matters here</why>",
            "      </dimension>",
            "    </primary_dimensions>",
            "    <secondary_dimensions>",
            '      <dimension name="..."/>',
            "    </secondary_dimensions>",
            "    <rationale>Why these dimensions fit this problem</rationale>",
            "  </tradeoff_dimensions>",
            "",
            "  <synthesis_threshold>",
            "    <source>problem | project | default</source>",
            "    <minimum_solutions_for_theme>3</minimum_solutions_for_theme>",
            "    <theme_strength_required>strong | moderate</theme_strength_required>",
            "    <synthesize_appetite>conservative | moderate | aggressive</synthesize_appetite>",
            "    <rationale>Why this threshold fits this problem</rationale>",
            "  </synthesis_threshold>",
            "</evaluation_criteria>",
        ],
    },
    3: {
        "title": "Reflect",
        "brief": "Validate inferred criteria, resolve conflicts, finalize",
        "actions": [
            "REFLECT ON INFERRED CRITERIA",
            "",
            "Review the evaluation criteria from Step 2. Validate and finalize them.",
            "",
            "VALIDATION CHECKS:",
            "",
            "1. CONSISTENCY CHECK",
            "   - Do viability criteria align with flaw severity?",
            "     (If something makes a solution non-viable, it should be fatal)",
            "   - Do trade-off dimensions cover the soft constraints?",
            "   - Does synthesis threshold match problem complexity?",
            "",
            "   If inconsistent: Identify the conflict and resolve it.",
            "",
            "2. COMPLETENESS CHECK",
            "   - Is every hard constraint mapped to a fatal flaw condition?",
            "   - Are obvious dimensions missing from trade-offs?",
            "   - Is the viability definition operational (actually usable for decisions)?",
            "",
            "   If incomplete: Add missing elements.",
            "",
            "3. SPECIFICITY CHECK",
            "   - Are criteria specific enough to produce consistent judgments?",
            "   - Are criteria too specific (would incorrectly exclude valid solutions)?",
            "   - Is there appropriate room for legitimate judgment?",
            "",
            "   If over-specified: Loosen criteria.",
            "   If under-specified: Add clarification.",
            "",
            "4. CONFLICT RESOLUTION",
            "   If problem signals conflict (e.g., urgent AND architectural):",
            "   - Determine which takes priority for THIS specific problem",
            "   - Document the conflict and resolution",
            "   - Adjust criteria accordingly",
            "",
            "   Priority order for conflicts:",
            "   - Hard constraints are inviolable",
            "   - Problem-specific signals override project patterns",
            "   - Explicit user instructions override all inferences",
            "",
            "MAKE ADJUSTMENTS as needed based on validation.",
            "",
            "OUTPUT:",
            "",
            "<finalized_criteria>",
            "  <viability_definition>...</viability_definition>",
            "  <flaw_severity>...</flaw_severity>",
            "  <tradeoff_dimensions>...</tradeoff_dimensions>",
            "  <synthesis_threshold>...</synthesis_threshold>",
            "",
            "  <validation>",
            "    <consistency_check>pass | fail</consistency_check>",
            "    <completeness_check>pass | fail</completeness_check>",
            "    <specificity_check>pass | fail</specificity_check>",
            "    <adjustments_made>",
            "      <adjustment>Description of any changes made during reflection</adjustment>",
            "    </adjustments_made>",
            "  </validation>",
            "</finalized_criteria>",
            "",
            "The finalized criteria will be used in:",
            "  - Step 4 (Dispatch): Agents see criteria to generate informed solutions",
            "  - Step 6 (Synthesize): synthesis_threshold determines theme requirements",
            "  - Step 7 (Challenge): viability_definition and flaw_severity for evaluation",
            "  - Step 8 (Select): tradeoff_dimensions for matrix and ranking",
        ],
    },
    4: {
        "title": "Dispatch",
        "brief": "Launch all perspectives as parallel sub-agents",
        "needs_dispatch": True,
    },
    5: {
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
            "   - Preserve all solution details (what, where, mechanism, trade-offs)",
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
    6: {
        "title": "Synthesize",
        "brief": "Analyze convergence/tension, generate cross-cutting solutions",
        "actions": [
            "ANALYZE SOLUTION RELATIONSHIPS AND GENERATE CROSS-CUTTING SOLUTIONS",
            "",
            "Reference FINALIZED_CRITERIA.synthesis_threshold from Step 3:",
            "  - minimum_solutions_for_theme: How many solutions must share a theme?",
            "  - theme_strength_required: How central must the theme be?",
            "  - synthesize_appetite: conservative | moderate | aggressive",
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
            "   - Apply synthesis_threshold: themes appearing in N+ solutions are candidates",
            "",
            "4. GENERATE CROSS-CUTTING SOLUTIONS (IF WARRANTED):",
            "   Apply synthesis threshold:",
            "   - CONSERVATIVE: Only synthesize when 3+ solutions share strong theme",
            "   - MODERATE: Synthesize when 2+ solutions share moderate theme",
            "   - AGGRESSIVE: Synthesize when any clear pattern emerges",
            "",
            "   For each qualified theme, ask:",
            "   'Is there a solution that fully embodies this theme in a way no single",
            "    perspective captured?'",
            "",
            "   IF YES: Articulate with SAME SPECIFICITY as pure solutions:",
            "     - what, where, mechanism, trade-offs",
            "     - Tag as 'synthesized' with attribution to inspiring solutions",
            "",
            "   IF NO: Document 'No cross-cutting solutions generated'",
            "   Zero synthesized solutions is ALWAYS a valid outcome.",
            "   Do not force synthesis to have output.",
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
    7: {
        "title": "Challenge",
        "brief": "Stress-test all solutions using calibrated criteria",
        "actions": [
            "STRESS-TEST ALL SOLUTIONS",
            "",
            "Reference FINALIZED_CRITERIA from Step 3 for evaluation.",
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
            "VIABILITY CHECK using viability_definition:",
            "  Does solution meet ALL viability criteria from Step 3?",
            "  If NO: Solution is ELIMINATED (not viable)",
            "  If YES: Solution proceeds to severity categorization",
            "",
            "CATEGORIZE ISSUES using flaw_severity from Step 3:",
            "",
            "  FATAL (from flaw_severity.fatal_conditions):",
            "    Apply the specific fatal conditions inferred for this problem.",
            "    -> Mark solution as ELIMINATED with reason",
            "",
            "  SIGNIFICANT (from flaw_severity.significant_conditions):",
            "    Apply the specific significant conditions inferred for this problem.",
            "    -> Document issue, solution remains VIABLE WITH ISSUES",
            "",
            "  MINOR (from flaw_severity.minor_conditions):",
            "    Apply the specific minor conditions inferred for this problem.",
            "    -> Note as trade-off, solution remains VIABLE",
            "",
            "UPDATE SOLUTION STATUS:",
            "  ELIMINATED: Fatal flaw found or viability criteria not met (document reason)",
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
    8: {
        "title": "Select",
        "brief": "Rank using calibrated dimensions, produce recommendations",
        "actions": [
            "EVALUATE AND PRODUCE RECOMMENDATIONS",
            "",
            "Reference FINALIZED_CRITERIA.tradeoff_dimensions from Step 3.",
            "",
            "1. RANK SURVIVING SOLUTIONS:",
            "   - Order by overall viability given stated constraints",
            "   - Document ranking criteria used",
            "   - Origin (pure vs synthesized) does NOT factor into ranking",
            "",
            "2. BUILD TRADE-OFF MATRIX using calibrated dimensions:",
            "",
            "   PRIMARY DIMENSIONS (must appear in matrix, from Step 3):",
            "   Include all primary dimensions with their weights.",
            "",
            "   SECONDARY DIMENSIONS (include if solutions vary, from Step 3):",
            "   Check if solutions differ on these; include only if relevant.",
            "",
            "   DIMENSION WEIGHTING:",
            "   When ranking solutions, weight dimensions according to calibrated weights.",
            "   High-weight dimensions contribute more to overall ranking.",
            "",
            "   | Solution    | [Dim1] | [Dim2] | [Dim3] | ... |",
            "   |-------------|--------|--------|--------|-----|",
            "   | Solution #1 | value  | value  | value  | ... |",
            "",
            "   Do NOT include excluded dimensions.",
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
            "  TRADE_OFF_MATRIX: [table comparing solutions on calibrated dimensions]",
            "  DECISION_FRAMEWORK: [conditional recommendations]",
            "  RECOMMENDATION: [explicit recommendation or key discriminating factor]",
        ],
    },
    9: {
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
            "  - Evaluation criteria used (from Step 3)",
            "  - Synthesis insights (convergence, tensions, themes)",
            "  - All viable solutions with full details",
            "  - Eliminated solutions with reasons",
            "  - Trade-off matrix (using calibrated dimensions)",
            "  - Decision framework (conditional recommendations)",
            "  - Explicit recommendation (or key discriminating factor)",
            "",
            "Present the report to the user.",
        ],
    },
}


# =============================================================================
# Step Handlers
# =============================================================================


def step_handler(ctx: StepContext) -> tuple[Outcome, dict]:
    """Generic handler for output-only steps."""
    return Outcome.OK, {}


# =============================================================================
# Workflow Definition
# =============================================================================


WORKFLOW = Workflow(
    "solution-design",
    StepDef(
        id="context",
        title="Context",
        phase="PREPARATION",
        actions=STEPS[1]["actions"],
        handler=step_handler,
        next={Outcome.OK: "calibrate"},
    ),
    StepDef(
        id="calibrate",
        title="Calibrate",
        phase="PREPARATION",
        actions=STEPS[2]["actions"],
        handler=step_handler,
        next={Outcome.OK: "reflect"},
    ),
    StepDef(
        id="reflect",
        title="Reflect",
        phase="PREPARATION",
        actions=STEPS[3]["actions"],
        handler=step_handler,
        next={Outcome.OK: "dispatch"},
    ),
    StepDef(
        id="dispatch",
        title="Dispatch",
        phase="GENERATION",
        actions=[
            "DISPATCH ALL PERSPECTIVE SUB-AGENTS",
            "",
            "Using the ROOT_CAUSE, CONSTRAINTS from Step 1",
            "and FINALIZED_CRITERIA from Step 3:",
            "",
            format_perspective_selection_guidance(),
            "",
            build_perspective_dispatch(),
            "",
            "WAIT for all perspective agents to complete before proceeding.",
        ],
        handler=step_handler,
        next={Outcome.OK: "aggregate"},
    ),
    StepDef(
        id="aggregate",
        title="Aggregate",
        phase="GENERATION",
        actions=STEPS[5]["actions"],
        handler=step_handler,
        next={Outcome.OK: "synthesize"},
    ),
    StepDef(
        id="synthesize",
        title="Synthesize",
        phase="EVALUATION",
        actions=STEPS[6]["actions"],
        handler=step_handler,
        next={Outcome.OK: "challenge"},
    ),
    StepDef(
        id="challenge",
        title="Challenge",
        phase="EVALUATION",
        actions=STEPS[7]["actions"],
        handler=step_handler,
        next={Outcome.OK: "select"},
    ),
    StepDef(
        id="select",
        title="Select",
        phase="EVALUATION",
        actions=STEPS[8]["actions"],
        handler=step_handler,
        next={Outcome.OK: "output"},
    ),
    StepDef(
        id="output",
        title="Output",
        phase="DELIVERY",
        actions=STEPS[9]["actions"],
        handler=step_handler,
        next={Outcome.OK: None},
    ),
    description="Perspective-parallel solution generation workflow",
)


def format_output(step: int, total_steps: int) -> str:
    """Format output for display."""
    info = STEPS.get(step, STEPS[9])
    is_complete = step >= total_steps

    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(info["title"]),
            script="design", step=str(step), total=str(total_steps)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # XML mandate for step 1
    if step == 1:
        xml_mandate = """<xml_format_mandate>
CRITICAL: All script outputs use XML format. You MUST:

1. Execute the action in <current_action>
2. When complete, invoke the exact command in <invoke_after>
3. The <next> block re-states the command -- execute it
4. For branching <invoke_after>, choose based on outcome:
   - <if_pass>: Use when action succeeded / QR returned PASS
   - <if_fail>: Use when action failed / QR returned ISSUES
</xml_format_mandate>"""
        parts.append(xml_mandate)
        parts.append("")

    # Build actions
    actions = []

    if step == 4:
        # Step 4: Launch all perspectives in parallel (Dispatch)
        actions.append("DISPATCH ALL PERSPECTIVE SUB-AGENTS")
        actions.append("")
        actions.append("Using the ROOT_CAUSE, CONSTRAINTS from Step 1")
        actions.append("and FINALIZED_CRITERIA from Step 3:")
        actions.append("")
        actions.append(format_perspective_selection_guidance())
        actions.append("")
        actions.append(build_perspective_dispatch())
        actions.append("")
        actions.append("WAIT for all perspective agents to complete before proceeding.")
    else:
        # Other steps use actions from STEPS dict
        if "actions" in info:
            actions.extend(info["actions"])

    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    # Invoke after
    if is_complete:
        parts.append("COMPLETE - Present final report to user.")
    else:
        next_step = step + 1
        cmd_text = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step {next_step} --total-steps {total_steps}" />'
        parts.append(render(W.el("invoke_after", TextNode(cmd_text)).build(), XMLRenderer()))

    return "\n".join(parts)


def main(
    step: int = None,
    total_steps: int = None,
):
    """Entry point with backward compatibility for CLI invocation.

    Note: Parameters have defaults because actual values come from argparse.
    The annotations are metadata for the testing framework.
    """
    parser = argparse.ArgumentParser(
        description="Solution Design Skill - Perspective-parallel solution generation",
        epilog="Steps: context -> calibrate -> reflect -> dispatch -> aggregate -> synthesize -> challenge -> select -> output",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 9:
        sys.exit("ERROR: --total-steps must be >= 9 (9 steps in workflow)")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps))


if __name__ == "__main__":
    main()
