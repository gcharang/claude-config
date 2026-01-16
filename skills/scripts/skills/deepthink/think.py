#!/usr/bin/env python3
"""
DeepThink Skill - Structured reasoning for open-ended analytical questions.

Fourteen-step workflow (1-14):
  1. Context Clarification  - Remove bias from input (S2A)
  2. Abstraction            - Domain, first principles, key concepts
  3. Characterization       - Question type, answer structure, mode determination
  4. Analogical Recall      - Direct/cross-domain analogies, anti-patterns
  5. Planning               - Sub-questions, success criteria
  6. Sub-Agent Design       - Generate sub-agent task definitions (Full only)
  7. Design Critique        - Coverage, overlap, appropriateness (Full only)
  8. Design Revision        - Revise based on critique (Full only)
  9. Dispatch               - Launch sub-agents in parallel (Full only)
  10. Quality Gate          - Filter low-quality outputs (Full only)
  11. Aggregation           - Agreement/disagreement maps (Full only)
  12. Initial Synthesis     - First-pass integration
  13. Iterative Refinement  - Verification loop until confident
  14. Formatting & Output   - Format and present final answer

Two modes: Full (all steps) and Quick (skips 6-11).
"""

import argparse
import sys
from typing import Annotated

from skills.lib.workflow.core import (
    Arg,
    Outcome,
    StepContext,
    StepDef,
    Workflow,
)
from skills.lib.workflow.ast import W, XMLRenderer, render
from skills.lib.workflow.ast.nodes import TextNode


MAX_ITERATIONS = 5
MODULE_PATH = "skills.deepthink.think"
SUBAGENT_MODULE_PATH = "skills.deepthink.subagent"


def format_step_output(
    step: int,
    total: int,
    title: str,
    actions: list[str],
    next_command: str = None,
    is_step_zero: bool = False,
) -> str:
    """Format complete step output using AST builder API.

    Args:
        step: Current step number (1-indexed)
        total: Total steps
        title: Step title
        actions: List of action strings
        next_command: Command to invoke after (None = workflow complete)
        is_step_zero: If True, prepend XML mandate (for step 1)
    """
    parts = []

    # Step header
    parts.append(render(
        W.el("step_header", TextNode(title),
            script="deepthink", step=str(step), total=str(total)
        ).build(),
        XMLRenderer()
    ))
    parts.append("")

    # XML mandate for step 1 (first step)
    if is_step_zero:
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

    # Current action
    action_nodes = [TextNode(a) for a in actions]
    parts.append(render(W.el("current_action", *action_nodes).build(), XMLRenderer()))
    parts.append("")

    # Invoke after or complete
    if next_command:
        parts.append(render(W.el("invoke_after", TextNode(next_command)).build(), XMLRenderer()))
    elif step >= total:
        # step is 1-indexed, total is count, so step==total means last step
        parts.append("WORKFLOW COMPLETE - Present results to user.")

    return "\n".join(parts)


STEPS = {
    1: {
        "title": "Context Clarification",
        "brief": "Extract objective content, remove bias from input",
        "actions": [
            "You are an expert analytical reasoner tasked with systematic deep analysis.",
            "",
            "PART 0 - CONTEXT SUFFICIENCY:",
            "  Before analyzing, assess whether you have sufficient context:",
            "  ",
            "  A. EXISTING CONTEXT: What relevant information is already in this conversation?",
            "     (prior codebase analysis, problem discoveries, architecture understanding)",
            "  ",
            "  B. SUFFICIENCY JUDGMENT: For this question, is existing context:",
            "     - SUFFICIENT: Can reason directly from available information",
            "     - PARTIAL: Have some context but need targeted exploration",
            "     - INSUFFICIENT: Need exploration before meaningful reasoning",
            "  ",
            "  C. IF NOT SUFFICIENT: Before proceeding to Part A, explore:",
            "     - Use Read/Glob/Grep tools to gather necessary context",
            "     - Focus on specific files/patterns relevant to the question",
            "     - Stop exploring when you have enough to reason -- avoid over-exploration",
            "     - Document what you found in a brief EXPLORATION SUMMARY",
            "  ",
            "  If context is SUFFICIENT, proceed directly to Part A.",
            "",
            "Extract objective, relevant content from the user's question.",
            "",
            "Read the question again before proceeding.",
            "",
            "Separate it from framing, opinion, or irrelevant information.",
            "",
            "PART A - CLARIFIED QUESTION:",
            "  Restate the core question in neutral, objective terms.",
            "  Remove leading language, embedded opinions, or assumptions.",
            "  If multiple sub-questions exist, list them clearly.",
            "",
            "PART B - EXTRACTED CONTEXT:",
            "  List factual context from input relevant to answering.",
            "  Exclude opinions, preferences, or irrelevant details.",
            "",
            "PART C - NOTED BIASES:",
            "  Identify framing effects, leading language, or embedded assumptions.",
            "  Note these so subsequent steps can guard against them.",
            "  If none detected, state 'No significant biases detected.'",
            "",
            "OUTPUT FORMAT:",
            "```",
            "CLARIFIED QUESTION:",
            "[neutral restatement]",
            "",
            "EXTRACTED CONTEXT:",
            "- [fact 1]",
            "- [fact 2]",
            "",
            "NOTED BIASES:",
            "- [bias 1] or 'No significant biases detected.'",
            "```",
            "",
            "The CLARIFIED QUESTION will be used as the working question for all subsequent steps.",
        ],
    },
    2: {
        "title": "Abstraction",
        "brief": "Identify domain, first principles, key concepts",
        "actions": [
            "Before diving into specifics, step back and identify high-level context.",
            "Work through this thoroughly. Avoid shortcuts. Show reasoning step by step.",
            "",
            "PART A - DOMAIN:",
            "  What field or domain does this question primarily belong to?",
            "  Are there adjacent domains that might offer relevant perspectives?",
            "",
            "PART B - FIRST PRINCIPLES:",
            "  What fundamental principles should guide any answer?",
            "  What would an expert consider non-negotiable constraints or truths?",
            "",
            "PART C - KEY CONCEPTS:",
            "  What core concepts must be understood to answer well?",
            "  Define any terms that might be ambiguous or contested.",
            "",
            "PART D - WHAT MAKES THIS HARD:",
            "  Why isn't the answer obvious? What makes this genuinely difficult?",
            "  Is it contested? Under-specified? Trade-off-laden? Novel?",
            "",
            "OUTPUT FORMAT:",
            "```",
            "DOMAIN: [primary domain]",
            "ADJACENT DOMAINS: [list]",
            "",
            "FIRST PRINCIPLES:",
            "- [principle 1]",
            "- [principle 2]",
            "",
            "KEY CONCEPTS:",
            "- [concept]: [definition if ambiguous]",
            "",
            "DIFFICULTY ANALYSIS:",
            "[why this is hard]",
            "```",
        ],
    },
    3: {
        "title": "Characterization",
        "brief": "Classify question type, determine mode",
        "actions": [
            "Classify this question to determine appropriate analysis approach.",
            "",
            "PART A - QUESTION TYPE:",
            "  Classify as one of:",
            "  - TAXONOMY/CLASSIFICATION: Seeking a way to organize or categorize",
            "  - TRADE-OFF ANALYSIS: Seeking to understand competing concerns",
            "  - DEFINITIONAL: Seeking to clarify meaning or boundaries",
            "  - EVALUATIVE: Seeking judgment on quality, correctness, fitness",
            "  - EXPLORATORY: Seeking to understand a space of possibilities",
            "",
            "PART B - ANSWER STRUCTURE:",
            "  Based on question type, what structure should the final answer take?",
            "  (e.g., 'proposed taxonomy with rationale' or 'decision framework')",
            "",
            "PART C - EVALUATION CRITERIA:",
            "  How should we judge whether an answer is good?",
            "  What distinguishes excellent from mediocre?",
            "  List 3-5 specific criteria.",
            "",
            "PART D - MODE DETERMINATION:",
            "  Should this use FULL mode (with sub-agents) or QUICK mode (direct synthesis)?",
            "",
            "  Use QUICK mode if ALL true:",
            "  - Relatively narrow scope",
            "  - Single analytical perspective likely sufficient",
            "  - No significant trade-offs between competing values",
            "  - High confidence in what a good answer looks like",
            "",
            "  Otherwise, use FULL mode.",
            "",
            "OUTPUT FORMAT:",
            "```",
            "QUESTION TYPE: [type]",
            "",
            "ANSWER STRUCTURE: [description]",
            "",
            "EVALUATION CRITERIA:",
            "1. [criterion 1]",
            "2. [criterion 2]",
            "...",
            "",
            "MODE: [FULL | QUICK]",
            "RATIONALE: [why this mode]",
            "```",
        ],
    },
    4: {
        "title": "Analogical Recall",
        "brief": "Retrieve similar problems from memory",
        "actions": [
            "Recall similar problems that might inform this analysis.",
            "Work through thoroughly. Consider multiple analogies before selecting.",
            "",
            "PART A - DIRECT ANALOGIES:",
            "  What similar problems in the same domain have been addressed?",
            "  How were they approached? What worked and what didn't?",
            "",
            "PART B - CROSS-DOMAIN ANALOGIES:",
            "  What problems in OTHER domains share structural similarity?",
            "  What can we learn from how those were solved?",
            "",
            "PART C - ANTI-PATTERNS:",
            "  What are known bad approaches to problems like this?",
            "  What mistakes do people commonly make?",
            "",
            "PART D - ANALOGICAL INSIGHTS:",
            "  What specific insights from these analogies should inform our approach?",
            "  Which analogies are most relevant and why?",
            "",
            "OUTPUT FORMAT:",
            "```",
            "DIRECT ANALOGIES:",
            "- [analogy 1]: [lesson]",
            "",
            "CROSS-DOMAIN ANALOGIES:",
            "- [domain]: [problem]: [insight]",
            "",
            "ANTI-PATTERNS:",
            "- [bad approach]: [why it fails]",
            "",
            "KEY INSIGHTS:",
            "- [insight to apply]",
            "```",
        ],
    },
    5: {
        "title": "Planning",
        "brief": "Define sub-questions and success criteria",
        "actions": [
            "Devise a plan for analyzing this question.",
            "",
            "PART A - SUB-QUESTIONS:",
            "  Break into sub-questions that collectively address the main question.",
            "  Each sub-question should be:",
            "  - Specific enough to analyze",
            "  - Distinct from other sub-questions",
            "  - Necessary (not just nice-to-have)",
            "",
            "PART B - SUCCESS CRITERIA:",
            "  What would a successful analysis look like?",
            "  How will we know when we've done enough exploration?",
            "",
            "PART C - SYNTHESIS CRITERIA:",
            "  When multiple perspectives provide different answers, how resolve?",
            "  What principles should guide synthesis?",
            "",
            "PART D - ANTICIPATED CHALLENGES:",
            "  What aspects will be hardest to address?",
            "  Where do you expect disagreement or uncertainty?",
            "",
            "OUTPUT FORMAT:",
            "```",
            "SUB-QUESTIONS:",
            "1. [question 1]",
            "2. [question 2]",
            "...",
            "",
            "SUCCESS CRITERIA:",
            "- [criterion]",
            "",
            "SYNTHESIS CRITERIA:",
            "- [principle for resolving disagreement]",
            "",
            "ANTICIPATED CHALLENGES:",
            "- [challenge]",
            "```",
        ],
    },
    6: {
        "title": "Sub-Agent Design",
        "brief": "Generate sub-agent task definitions",
        "actions": [
            "Design sub-agents to explore this question from different angles.",
            "",
            "HOW SUB-AGENTS WORK:",
            "  - All launch simultaneously (parallel execution)",
            "  - Each receives the same inputs: original question + shared context",
            "  - Each produces independent output returned to you for aggregation",
            "  - Sub-agents cannot see or build on each other's work",
            "",
            "Your task: design WHAT each sub-agent analyzes, knowing they work in isolation.",
            "",
            "You have complete freedom in how you divide the analytical work.",
            "",
            "DIVISION STRATEGIES:",
            "",
            "You may divide analytical work using any of these (or combinations):",
            "",
            "  By Perspective/Lens",
            "    Different epistemological viewpoints examining the same problem.",
            "    A skeptic examines assuming the obvious answer is wrong;",
            "    an optimist examines assuming success is achievable.",
            "",
            "  By Role/Stakeholder",
            "    Who has skin in the game? Different priorities and constraints.",
            "",
            "  By Dimension/Facet",
            "    Multiple orthogonal aspects that can be analyzed independently.",
            "",
            "  By Methodology/Approach",
            "    Different analytical frameworks applied to the same question.",
            "",
            "  By Scope/Scale",
            "    Micro, meso, macro. Problems look different at different scales.",
            "",
            "  By Time Horizon",
            "    Short-term vs long-term. Tactical vs strategic.",
            "",
            "  By Hypothesis",
            "    Assign sub-agents to steelman competing hypotheses.",
            "",
            "  By Facet",
            "    Identify independent aspects analyzable without depending on",
            "    each other's conclusions.",
            "",
            "You may combine strategies.",
            "",
            "For each sub-agent, specify:",
            "  1. NAME: Short descriptive name",
            "  2. DIVISION STRATEGY: Which strategy this represents",
            "  3. TASK DESCRIPTION: What specifically to analyze",
            "  4. ASSIGNED SUB-QUESTIONS: Which sub-questions to address",
            "  5. UNIQUE VALUE: Why this will produce insights others won't",
            "",
            "OUTPUT FORMAT:",
            "```",
            "SUB-AGENT 1:",
            "- Name: [name]",
            "- Strategy: [strategy]",
            "- Task: [description]",
            "- Sub-Questions: [list]",
            "- Unique Value: [why this matters]",
            "",
            "SUB-AGENT 2:",
            "[etc.]",
            "",
            "DIVISION RATIONALE:",
            "[why this particular division]",
            "```",
        ],
    },
    7: {
        "title": "Design Critique",
        "brief": "Self-critique sub-agent design",
        "actions": [
            "Critically evaluate the sub-agent design from Step 6.",
            "",
            "PART A - COVERAGE:",
            "  Do sub-agents collectively cover all sub-questions from Step 5?",
            "  Are there important angles NO sub-agent will address?",
            "  List any gaps.",
            "",
            "PART B - OVERLAP:",
            "  Do any sub-agents duplicate work unnecessarily?",
            "  Is there productive tension vs wasteful redundancy?",
            "  List any problematic overlaps.",
            "",
            "PART C - APPROPRIATENESS:",
            "  Is division strategy well-suited to this question?",
            "  Would a different strategy yield better insights?",
            "  Are task descriptions clear enough to execute?",
            "",
            "PART D - BALANCE:",
            "  Are some sub-agents given much harder tasks than others?",
            "  Is there risk one sub-agent will dominate synthesis?",
            "",
            "PART E - SPECIFIC ISSUES:",
            "  List specific problems with individual sub-agent definitions.",
            "  For each issue, be specific about what's wrong.",
            "",
            "Be genuinely critical. Goal is to improve, not approve.",
            "",
            "OUTPUT FORMAT:",
            "```",
            "COVERAGE:",
            "- Gaps: [list or 'none']",
            "",
            "OVERLAP:",
            "- Issues: [list or 'none']",
            "",
            "APPROPRIATENESS:",
            "- Assessment: [evaluation]",
            "",
            "BALANCE:",
            "- Assessment: [evaluation]",
            "",
            "SPECIFIC ISSUES:",
            "- [issue 1]",
            "- [issue 2]",
            "```",
        ],
    },
    8: {
        "title": "Design Revision",
        "brief": "Revise sub-agent definitions based on critique",
        "actions": [
            "Revise sub-agent design based on critique from Step 7.",
            "",
            "For each issue identified, either:",
            "  1. Revise the design to address it, OR",
            "  2. Explain why the issue should not be addressed",
            "",
            "OUTPUT FORMAT:",
            "```",
            "REVISIONS MADE:",
            "- [change]: [which critique point it addresses]",
            "",
            "ISSUES NOT ADDRESSED:",
            "- [critique point]: [why not addressing]",
            "",
            "FINAL SUB-AGENT DEFINITIONS:",
            "",
            "SUB-AGENT 1:",
            "- Name: [name]",
            "- Strategy: [strategy]",
            "- Task: [description]",
            "- Sub-Questions: [list]",
            "- Unique Value: [why this matters]",
            "",
            "[etc.]",
            "```",
            "",
            "These definitions will be used to dispatch sub-agents in Step 9.",
        ],
    },
    9: {
        "title": "Dispatch",
        "brief": "Launch sub-agents in parallel",
        "needs_dispatch": True,
    },
    10: {
        "title": "Quality Gate",
        "brief": "Filter sub-agent outputs before aggregation",
        "actions": [
            "Review each sub-agent's output. Assess whether to include in aggregation.",
            "",
            "For each sub-agent output, assess:",
            "  1. COHERENCE: Is reasoning internally consistent?",
            "  2. RELEVANCE: Does it actually address its assigned task?",
            "  3. SUBSTANTIVENESS: Genuine insights, not just surface observations?",
            "  4. FAILURE MODE COMPLETENESS: Did it identify meaningful weaknesses?",
            "",
            "RATING SCALE:",
            "  - PASS: Include fully in aggregation",
            "  - PARTIAL: Include with noted reservations",
            "  - FAIL: Exclude from aggregation (with explanation)",
            "",
            "OUTPUT FORMAT:",
            "```",
            "SUB-AGENT 1 ([name]):",
            "- Coherence: [assessment]",
            "- Relevance: [assessment]",
            "- Substantiveness: [assessment]",
            "- Failure Modes: [assessment]",
            "- RATING: [PASS/PARTIAL/FAIL]",
            "- Notes: [observations]",
            "",
            "[repeat for each]",
            "",
            "SUMMARY:",
            "- Passing: [list]",
            "- Partial: [list]",
            "- Failed: [list]",
            "- Coverage assessment: [are critical angles missing due to failures?]",
            "```",
        ],
    },
    11: {
        "title": "Aggregation",
        "brief": "Collect findings, extract intermediate insights",
        "actions": [
            "Organize findings from all sub-agents that passed quality gate.",
            "",
            "PART A - AGREEMENT MAP:",
            "  What do multiple sub-agents agree on?",
            "  List points of convergence with which sub-agents support each.",
            "",
            "PART B - DISAGREEMENT MAP:",
            "  Where do sub-agents disagree?",
            "  For each: point of contention, competing positions, reasoning.",
            "",
            "PART B2 - CONFLICT RESOLUTION (for synthesis):",
            "  For each disagreement, note which position has:",
            "  - More sub-agent support (majority)",
            "  - Stronger evidence grounding",
            "  - Better alignment with first principles from Step 2",
            "  Flag unresolvable conflicts explicitly.",
            "",
            "PART C - UNIQUE CONTRIBUTIONS:",
            "  What valuable insights appeared in only ONE sub-agent?",
            "  Why might others have missed this?",
            "",
            "PART D - INTERMEDIATE INSIGHTS:",
            "  Review reasoning chains of ALL sub-agents (including PARTIAL).",
            "  Extract intermediate observations valuable independent of conclusions.",
            "  These inform synthesis even if overall analysis not adopted.",
            "",
            "PART E - FAILURE MODE CATALOG:",
            "  Aggregate all anticipated failure modes identified by sub-agents.",
            "  Group by theme.",
            "",
            "PART F - SUB-QUESTION COVERAGE:",
            "  For each sub-question from Step 5, summarize responses.",
            "  Flag any with weak or no coverage.",
            "",
            "Preserve all disagreements exactly as found. Record positions without evaluation.",
            "This step is purely organizational.",
            "",
            "OUTPUT FORMAT:",
            "```",
            "AGREEMENT MAP:",
            "- [point]: supported by [sub-agents]",
            "",
            "DISAGREEMENT MAP:",
            "- [contention]: [position A] vs [position B]",
            "",
            "UNIQUE CONTRIBUTIONS:",
            "- [sub-agent]: [insight]",
            "",
            "INTERMEDIATE INSIGHTS:",
            "- [insight from reasoning, not conclusion]",
            "",
            "FAILURE MODE CATALOG:",
            "- [theme]: [modes]",
            "",
            "SUB-QUESTION COVERAGE:",
            "- Q1: [coverage summary]",
            "```",
        ],
    },
    12: {
        "title": "Initial Synthesis",
        "brief": "First-pass integration into coherent response",
        "has_mode_variants": True,
    },
    13: {
        "title": "Iterative Refinement",
        "brief": "Evaluate and refine until confident",
        "has_iteration": True,
    },
    14: {
        "title": "Formatting & Output",
        "brief": "Format and present final answer to user",
    },
}


def get_dispatch_actions() -> list[str]:
    """Generate dispatch actions for Step 9."""
    invoke_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {SUBAGENT_MODULE_PATH} --step 1 --total-steps 8" />'

    # Build parallel dispatch manually
    dispatch_lines = [
        '<parallel_dispatch agent="general-purpose">',
        '  <instruction>',
        '    Launch ALL sub-agents from FINAL SUB-AGENT DEFINITIONS (Step 8).',
        '    Use a SINGLE message with multiple Task tool calls.',
        '  </instruction>',
        '',
        '  <model_selection>',
        '    Use SONNET (default) for all agents.',
        '    These require nuanced reasoning - do not downgrade to haiku.',
        '  </model_selection>',
        '',
        '  <shared_context>',
        '    Each sub-agent receives:',
        '    - CLARIFIED QUESTION from Step 1',
        '    - DOMAIN and FIRST PRINCIPLES from Step 2',
        '    - QUESTION TYPE and EVALUATION CRITERIA from Step 3',
        '    - KEY ANALOGIES from Step 4',
        '    - Their specific task definition from Step 8',
        '  </shared_context>',
        '',
        '  <template>',
        '    Explore this question from the assigned perspective.',
        '',
        '    CLARIFIED QUESTION: [from Step 1]',
        '    DOMAIN: [from Step 2]',
        '    FIRST PRINCIPLES: [from Step 2]',
        '    QUESTION TYPE: [from Step 3]',
        '    EVALUATION CRITERIA: [from Step 3]',
        '    KEY ANALOGIES: [from Step 4]',
        '',
        '    YOUR TASK:',
        '    - Name: $SUBAGENT_NAME',
        '    - Strategy: $SUBAGENT_STRATEGY',
        '    - Task: $SUBAGENT_TASK',
        '    - Sub-Questions: $SUBAGENT_QUESTIONS',
        '',
        f'    Start: {invoke_cmd}',
        '  </template>',
        '</parallel_dispatch>',
    ]
    return dispatch_lines


def get_synthesis_actions_full() -> list[str]:
    """Generate synthesis actions for Full mode."""
    return [
        "Integrate aggregated findings into a coherent response.",
        "Hint: Prioritize aspects matching the EVALUATION CRITERIA from Step 3.",
        "Work through thoroughly. Avoid shortcuts. Show reasoning step by step.",
        "",
        "SYNTHESIS GUIDELINES:",
        "  1. Use evaluation criteria from Step 3 to guide integration",
        "  2. Resolve disagreements using synthesis criteria from Step 5",
        "  3. Draw on intermediate insights from Step 11, not just conclusions",
        "  4. Acknowledge where genuine uncertainty remains",
        "  5. Do not artificially harmonize positions that genuinely conflict",
        "",
        "PART A - CORE ANSWER:",
        "  What is your integrated response to the original question?",
        "  Structure appropriately for the question type from Step 3.",
        "",
        "PART B - KEY TRADE-OFFS:",
        "  What trade-offs are inherent in this answer?",
        "  What did you prioritize, and what did you deprioritize?",
        "",
        "PART C - DISSENTING VIEWS:",
        "  Where did you override a sub-agent's position?",
        "  Why not adopted, and what would change your mind?",
        "",
        "PART D - EVIDENCE GROUNDING:",
        "  For each major claim, cite the evidence source:",
        "  - From Step 2 (first principles)",
        "  - From Step 4 (analogies)",
        "  - From Step 11 (sub-agent findings or intermediate insights)",
        "  Claims without grounding: flag as UNGROUNDED.",
        "",
        "PART E - ACKNOWLEDGED LIMITATIONS:",
        "  What aspects does this synthesis NOT address well?",
        "  What additional information would strengthen the analysis?",
        "",
        "PART F - CONFIDENCE MARKERS:",
        "  Mark claims as:",
        "  - HIGH: Strong agreement, multiple sources",
        "  - MEDIUM: Reasonable but contested or single source",
        "  - LOW: Speculative or limited evidence",
        "",
        "OUTPUT FORMAT:",
        "```",
        "CORE ANSWER:",
        "[structured response]",
        "",
        "KEY TRADE-OFFS:",
        "- Prioritized: [X] over [Y] because [reason]",
        "",
        "DISSENTING VIEWS:",
        "- [sub-agent]: [position not adopted]: [why]",
        "",
        "EVIDENCE GROUNDING:",
        "- [claim]: [source]",
        "- UNGROUNDED: [list any ungrounded claims]",
        "",
        "LIMITATIONS:",
        "- [limitation]",
        "",
        "CONFIDENCE: [overall assessment]",
        "```",
        "",
        "This synthesis will be evaluated in Step 13. Expect to refine it.",
    ]


def get_synthesis_actions_quick() -> list[str]:
    """Generate synthesis actions for Quick mode."""
    return [
        "Based on abstraction (Step 2) and analogies (Step 4), synthesize response.",
        "Hint: Prioritize aspects matching the EVALUATION CRITERIA from Step 3.",
        "Work through thoroughly. Avoid shortcuts. Show reasoning step by step.",
        "",
        "PART A - CORE ANSWER:",
        "  What is your response to the original question?",
        "  Ground in first principles from Step 2 and analogies from Step 4.",
        "",
        "PART B - EVIDENCE GROUNDING:",
        "  For each major claim, cite source:",
        "  - First principles (Step 2)",
        "  - Analogical reasoning (Step 4)",
        "  - Domain knowledge",
        "  Claims without grounding: flag as UNGROUNDED.",
        "",
        "PART C - ACKNOWLEDGED LIMITATIONS:",
        "  What aspects does this NOT address well?",
        "  Where might alternative perspectives yield different conclusions?",
        "",
        "PART D - CONFIDENCE MARKERS:",
        "  Mark claims as HIGH, MEDIUM, or LOW confidence with brief justification.",
        "",
        "OUTPUT FORMAT:",
        "```",
        "CORE ANSWER:",
        "[structured response]",
        "",
        "EVIDENCE GROUNDING:",
        "- [claim]: [source]",
        "- UNGROUNDED: [list any]",
        "",
        "LIMITATIONS:",
        "- [limitation]",
        "",
        "CONFIDENCE: [overall assessment]",
        "```",
        "",
        "This synthesis will be evaluated in Step 13.",
    ]


def get_refinement_actions(iteration: int) -> list[str]:
    """Generate refinement actions for Step 13."""
    return [
        f"ITERATION {iteration} OF {MAX_ITERATIONS}",
        "",
        "RULE 0 (MANDATORY): Follow the invoke_after command. Do NOT skip",
        "to step 14 unless confidence is CERTAIN or this is iteration 5.",
        "",
        "Critically evaluate the current synthesis.",
        "Work through thoroughly -- avoid quick 'looks good' assessments.",
        "",
        "PART A - VERIFICATION QUESTION GENERATION:",
        "  Generate 3-5 verification questions that would test correctness.",
        "  Use OPEN questions ('What is X?', 'Where does Y occur?'), not yes/no.",
        "  Yes/no questions bias toward agreement regardless of correctness.",
        "  Focus on:",
        "  - Claims marked LOW or MEDIUM confidence",
        "  - Any UNGROUNDED claims from Step 12",
        "  - Potential blind spots",
        "  - Failure modes that could invalidate key proposals",
        "  - Edge cases the synthesis might not handle",
        "",
        "PART B - INDEPENDENT VERIFICATION:",
        "  For each verification question, answer based ONLY on:",
        "  - First principles from Step 2",
        "  - Analogies from Step 4",
        "  - Aggregated evidence from Step 11 (if Full mode)",
        "",
        "  CRITICAL: Do NOT look at the synthesis while answering.",
        "  Answer based on evidence, not what the synthesis claims.",
        "",
        "  EXPLORATION OPTION:",
        "  If a verification question cannot be answered with existing evidence:",
        "  - Use Read/Glob/Grep to find concrete evidence in the codebase",
        "  - This is especially valuable for UNGROUNDED claims from Step 12",
        "  - Keep exploration bounded -- answer the specific question, then stop",
        "  - Update answer with exploration findings and cite sources",
        "",
        "PART C - DISCREPANCY IDENTIFICATION:",
        "  Compare verification answers against current synthesis.",
        "  Where do they differ?",
        "  List each discrepancy.",
        "",
        "PART D - ACTIONABLE FEEDBACK:",
        "  For each discrepancy or issue, provide feedback.",
        "",
        "  Each piece of feedback MUST include all three elements:",
        "    1. ELEMENT: Name the specific claim, section, or aspect",
        "    2. PROBLEM: State precisely what is wrong or unsupported",
        "    3. ACTION: Propose a concrete fix or revision",
        "",
        "  Feedback missing any element should be discarded as too vague.",
        "",
        "  GOOD: 'ELEMENT: claim X. PROBLEM: contradicts evidence Y. ACTION: qualify with Z.'",
        "  BAD: 'The analysis could be stronger.' (no specific element/problem/action)",
        "",
        "PART E - SYNTHESIS UPDATE:",
        "  Review feedback from ALL previous iterations (if any).",
        "  Based on actionable feedback, revise the synthesis.",
        "  Avoid repeating mistakes identified in prior iterations.",
        "  For each revision, note which feedback item it addresses.",
        "",
        "PART F - CONFIDENCE ASSESSMENT:",
        "  After revisions, assess confidence:",
        "  - EXPLORING: Still developing understanding",
        "  - LOW: Significant gaps or unresolved issues",
        "  - MEDIUM: Reasonable answer but some uncertainty",
        "  - HIGH: Strong answer, minor refinements possible",
        "  - CERTAIN: As good as it can get with available information",
        "",
        "  Provide specific justification for confidence level.",
        "",
        "<iteration_gate>",
        "CRITICAL: You MUST follow the invoke_after command exactly.",
        "",
        "EXIT CONDITIONS (both required to proceed to step 14):",
        "  1. Confidence = CERTAIN, OR",
        "  2. This is iteration 5 (final iteration)",
        "",
        "If NEITHER condition is met, STOP.",
        "Do NOT proceed to step 14. Continue to the next iteration.",
        "</iteration_gate>",
        "",
        "OUTPUT FORMAT:",
        "```",
        "VERIFICATION QUESTIONS:",
        "1. [question]",
        "",
        "INDEPENDENT ANSWERS:",
        "1. [answer without looking at synthesis]",
        "",
        "DISCREPANCIES:",
        "- [where synthesis differs from verification]",
        "",
        "ACTIONABLE FEEDBACK:",
        "- ELEMENT: [what]. PROBLEM: [why wrong]. ACTION: [fix]",
        "",
        "REVISED SYNTHESIS:",
        "[updated synthesis]",
        "",
        "CONFIDENCE: [level]",
        "JUSTIFICATION: [why this level]",
        "```",
    ]


def get_completion_message(confidence: str) -> list[str]:
    """Generate formatting instructions for Step 14."""
    base_actions = [
        f"Refinement complete. Confidence: {confidence.upper()}.",
        "",
        "Present the final answer to the user.",
        "",
        "FORMATTING REQUIREMENTS:",
        "  - Lead with the direct answer to the original question",
        "  - Use the answer structure determined in Step 3",
        "  - Integrate key trade-offs naturally into the explanation",
        "  - Note limitations only where they materially affect the answer",
        "  - Omit workflow artifacts (step references, sub-agent names, etc.)",
        "",
    ]

    if confidence == "certain":
        base_actions.extend([
            "CONFIDENCE: HIGH",
            "  Present with authority. Hedging language unnecessary.",
        ])
    else:
        base_actions.extend([
            f"CONFIDENCE: {confidence.upper()}",
            "  Flag specific claims with lower confidence.",
            "  Indicate what additional information would strengthen the analysis.",
        ])

    base_actions.extend([
        "",
        "OUTPUT: Clean prose response directly addressing the user's question.",
        "        No meta-commentary about the analysis process.",
    ])

    return base_actions


# Workflow handlers
def step_handler_simple(ctx: StepContext) -> tuple[Outcome, dict]:
    """Generic handler for output-only steps."""
    return Outcome.OK, {}


def step_planning(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for planning step that branches based on mode."""
    mode = ctx.workflow_params.get("mode", "full")
    if mode == "quick":
        return Outcome.SKIP, {"mode": mode}
    return Outcome.OK, {"mode": mode}


def step_full_only(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for steps that should be skipped in quick mode."""
    mode = ctx.workflow_params.get("mode", "full")
    if mode == "quick":
        return Outcome.SKIP, {}
    return Outcome.OK, {}


def step_initial_synthesis(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for initial synthesis step."""
    return Outcome.OK, {}


def step_iterative_refinement(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for iterative refinement step with confidence loop."""
    iteration = ctx.step_state.get("iteration", 1)
    confidence = ctx.workflow_params.get("confidence", "exploring")

    if confidence == "certain" or iteration >= MAX_ITERATIONS:
        return Outcome.OK, {"iteration": iteration, "confidence": confidence}
    else:
        return Outcome.ITERATE, {"iteration": iteration + 1, "confidence": confidence}


def step_formatting_output(ctx: StepContext) -> tuple[Outcome, dict]:
    """Handler for final formatting step."""
    return Outcome.OK, {}


# Workflow definition
WORKFLOW = Workflow(
    "deepthink",
    StepDef(
        id="context_clarification",
        title="Context Clarification",
        actions=STEPS[1]["actions"],
        handler=step_handler_simple,
        next={Outcome.OK: "abstraction"},
    ),
    StepDef(
        id="abstraction",
        title="Abstraction",
        actions=STEPS[2]["actions"],
        handler=step_handler_simple,
        next={Outcome.OK: "characterization"},
    ),
    StepDef(
        id="characterization",
        title="Characterization",
        actions=STEPS[3]["actions"],
        handler=step_handler_simple,
        next={Outcome.OK: "analogical_recall"},
    ),
    StepDef(
        id="analogical_recall",
        title="Analogical Recall",
        actions=STEPS[4]["actions"],
        handler=step_handler_simple,
        next={Outcome.OK: "planning"},
    ),
    StepDef(
        id="planning",
        title="Planning",
        actions=STEPS[5]["actions"],
        handler=step_planning,
        next={
            Outcome.OK: "subagent_design",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="subagent_design",
        title="Sub-Agent Design",
        actions=STEPS[6]["actions"],
        handler=step_full_only,
        next={
            Outcome.OK: "design_critique",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="design_critique",
        title="Design Critique",
        actions=STEPS[7]["actions"],
        handler=step_full_only,
        next={
            Outcome.OK: "design_revision",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="design_revision",
        title="Design Revision",
        actions=STEPS[8]["actions"],
        handler=step_full_only,
        next={
            Outcome.OK: "dispatch",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="dispatch",
        title="Dispatch",
        actions=[],
        handler=step_full_only,
        next={
            Outcome.OK: "quality_gate",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="quality_gate",
        title="Quality Gate",
        actions=STEPS[10]["actions"],
        handler=step_full_only,
        next={
            Outcome.OK: "aggregation",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="aggregation",
        title="Aggregation",
        actions=STEPS[11]["actions"],
        handler=step_full_only,
        next={
            Outcome.OK: "initial_synthesis",
            Outcome.SKIP: "initial_synthesis",
        },
    ),
    StepDef(
        id="initial_synthesis",
        title="Initial Synthesis",
        actions=[],
        handler=step_initial_synthesis,
        next={Outcome.OK: "iterative_refinement"},
    ),
    StepDef(
        id="iterative_refinement",
        title="Iterative Refinement",
        actions=[],
        handler=step_iterative_refinement,
        next={
            Outcome.OK: "formatting_output",
            Outcome.ITERATE: "iterative_refinement",
        },
    ),
    StepDef(
        id="formatting_output",
        title="Formatting & Output",
        actions=[],
        handler=step_formatting_output,
        next={Outcome.OK: None},
    ),
    description="Structured reasoning for open-ended analytical questions",
)


def get_step_1_output(args, step_info):
    """Handle Step 1: Context Clarification."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 2 --total-steps {args.total_steps}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
        is_step_zero=True,
    )


def get_step_2_output(args, step_info):
    """Handle Step 2: Abstraction."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 3 --total-steps {args.total_steps}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_3_output(args, step_info):
    """Handle Step 3: Characterization."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 4 --total-steps {args.total_steps}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_4_output(args, step_info):
    """Handle Step 4: Analogical Recall."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 5 --total-steps {args.total_steps}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_5_output(args, step_info):
    """Handle Step 5: Planning (branches based on mode)."""
    actions = list(step_info["actions"]) + [
        "",
        "<mode_branch>",
        "  <if_full>Proceed to Step 6 (Sub-Agent Design)</if_full>",
        "  <if_quick>Skip to Step 12 (Initial Synthesis)</if_quick>",
        "</mode_branch>",
    ]

    next_cmd_full = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 6 --total-steps {args.total_steps} --mode full" />'
    next_cmd_quick = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 12 --total-steps {args.total_steps} --mode quick" />'

    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=f"If FULL: {next_cmd_full}\nIf QUICK: {next_cmd_quick}",
    )


def get_step_6_output(args, step_info):
    """Handle Step 6: Sub-Agent Design."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 7 --total-steps {args.total_steps} --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_7_output(args, step_info):
    """Handle Step 7: Design Critique."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 8 --total-steps {args.total_steps} --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_8_output(args, step_info):
    """Handle Step 8: Design Revision."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 9 --total-steps {args.total_steps} --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_9_output(args, step_info):
    """Handle Step 9: Dispatch."""
    actions = get_dispatch_actions()
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 10 --total-steps {args.total_steps} --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_10_output(args, step_info):
    """Handle Step 10: Quality Gate."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 11 --total-steps {args.total_steps} --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_11_output(args, step_info):
    """Handle Step 11: Aggregation."""
    actions = list(step_info.get("actions", []))
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 12 --total-steps {args.total_steps} --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_12_output(args, step_info):
    """Handle Step 12: Initial Synthesis (mode-dependent)."""
    if args.mode == "quick":
        actions = get_synthesis_actions_quick()
    else:
        actions = get_synthesis_actions_full()

    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 13 --total-steps {args.total_steps} --confidence <your_confidence> --iteration 1 --mode {args.mode}" />'
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=next_cmd,
    )


def get_step_13_output(args, step_info):
    """Handle Step 13: Iterative Refinement with loop logic."""
    actions = get_refinement_actions(args.iteration)

    if args.confidence == "certain" or args.iteration >= MAX_ITERATIONS:
        next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 14 --total-steps {args.total_steps} --confidence {args.confidence} --mode {args.mode}" />'
        title = f"DEEPTHINK - {step_info['title']} (Iteration {args.iteration}) -> Complete"
    else:
        next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step 13 --total-steps {args.total_steps} --confidence <your_confidence> --iteration {args.iteration + 1} --mode {args.mode}" />'
        title = f"DEEPTHINK - {step_info['title']} (Iteration {args.iteration})"

    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=title,
        actions=actions,
        next_command=next_cmd,
    )


def get_step_14_output(args, step_info):
    """Handle Step 14: Formatting & Output (terminal step)."""
    actions = get_completion_message(args.confidence)
    return format_step_output(
        step=args.step,
        total=args.total_steps,
        title=f"DEEPTHINK - {step_info['title']}",
        actions=actions,
        next_command=None,
    )


STEP_HANDLERS = {
    1: get_step_1_output,
    2: get_step_2_output,
    3: get_step_3_output,
    4: get_step_4_output,
    5: get_step_5_output,
    6: get_step_6_output,
    7: get_step_7_output,
    8: get_step_8_output,
    9: get_step_9_output,
    10: get_step_10_output,
    11: get_step_11_output,
    12: get_step_12_output,
    13: get_step_13_output,
    14: get_step_14_output,
}


def main(
    step: int = None,
    total_steps: int = None,
    confidence: str | None = None,
    iteration: int | None = None,
    mode: str | None = None,
):
    """Entry point with parameter annotations for testing framework.

    Note: Parameters have defaults because actual values come from argparse.
    The annotations are metadata for the testing framework.
    """
    parser = argparse.ArgumentParser(
        description="DeepThink - Structured reasoning for open-ended analytical questions",
        epilog="Steps: 1-14 (Full mode) or 1-5,12-14 (Quick mode)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument(
        "--confidence",
        type=str,
        choices=["exploring", "low", "medium", "high", "certain"],
        default="exploring",
        help="Confidence level (for Step 13)",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=1,
        help="Current iteration within Step 13 (1-5)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["quick", "full"],
        default="full",
        help="Analysis mode (set in Step 3)",
    )
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps != 14:
        sys.exit("ERROR: --total-steps must be 14 (steps 1-14)")
    if args.step > 14:
        sys.exit("ERROR: --step cannot exceed 14")

    step_info = STEPS.get(args.step)
    if not step_info:
        sys.exit(f"ERROR: Invalid step {args.step}")

    handler = STEP_HANDLERS.get(args.step)
    if not handler:
        sys.exit(f"ERROR: No handler for step {args.step}")

    output = handler(args, step_info)
    print(output)


if __name__ == "__main__":
    main()
