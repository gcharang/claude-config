#!/usr/bin/env python3
"""
ThinkDeep Skill - Structured deep reasoning workflow.

Guides problem analysis through six phases:
  1. Decompose  - understand problem space, constraints, assumptions
  2. Generate   - create distinct solution approaches
  3. Critique   - Self-Refine feedback on solutions (NEW)
  4. Verify     - factored verification of assumptions (improved)
  5. Cross-check - reconcile verified facts with claims (NEW)
  6. Synthesize - structured trade-off analysis

Extra steps beyond 6 go to verification (where accuracy improves most).

Usage:
    python3 thinkdeep.py --step 1 --total-steps 6 --thoughts "Problem: Redis vs Memcached"

Research grounding:
  - ToT (Yao 2023): decompose into thoughts "small enough for diverse samples,
    big enough to evaluate"
  - CoVe (Dhuliawala 2023): factored verification improves accuracy 17%->70%.
    Use OPEN questions, not yes/no ("model tends to agree whether right or wrong")
  - Self-Refine (Madaan 2023): feedback must be "actionable and specific";
    separate feedback from refinement for 5-40% improvement
"""

import argparse
import sys


def get_step_1_guidance():
    """Step 1: Problem Decomposition - understand the problem space."""
    return (
        "Problem Decomposition",
        [
            "State the CORE PROBLEM in one sentence: 'I need to decide X'",
            "",
            "List HARD CONSTRAINTS (non-negotiable):",
            "  - Technical: latency < X, throughput > Y, compatibility with Z",
            "  - Business: budget, timeline, team skills, compliance",
            "  - Operational: maintenance burden, failure modes, observability",
            "",
            "List SOFT CONSTRAINTS (preferences, can trade off)",
            "",
            "List VARIABLES (what you control):",
            "  technology choice, architecture, deployment model, data model, API design",
            "",
            "Surface HIDDEN ASSUMPTIONS by asking:",
            "  'What am I assuming about scale/load patterns?'",
            "  'What am I assuming about the team's capabilities?'",
            "  'What am I assuming will NOT change?'",
            "",
            "If unclear, use AskUserQuestion to clarify",
        ],
        [
            "PROBLEM (one sentence)",
            "HARD CONSTRAINTS (non-negotiable)",
            "SOFT CONSTRAINTS (preferences)",
            "VARIABLES (what you control)",
            "ASSUMPTIONS (surfaced via questions)",
        ],
    )


def get_step_2_guidance():
    """Step 2: Solution Generation - create distinct approaches."""
    return (
        "Solution Generation",
        [
            "Generate 2-4 DISTINCT solution approaches",
            "",
            "Solutions must differ on a FUNDAMENTAL AXIS:",
            "  - Architecture: monolith vs microservices vs serverless",
            "  - Data model: normalized vs denormalized vs event-sourced",
            "  - Trade-off: optimize for latency vs throughput vs cost",
            "  - Complexity: simple-but-limited vs complex-but-flexible",
            "",
            "For EACH solution, document:",
            "  - Name: short label (e.g., 'Redis Cluster', 'Postgres Advisory Locks')",
            "  - Core mechanism: HOW it solves the problem (1-2 sentences)",
            "  - Key assumptions: what must be true for this to work",
            "  - Claimed benefits: what this approach provides",
            "",
            "AVOID premature convergence - do not favor one solution yet",
        ],
        [
            "PROBLEM (from step 1)",
            "CONSTRAINTS (from step 1)",
            "SOLUTIONS (each with: name, mechanism, assumptions, claimed benefits)",
        ],
    )


def get_step_3_guidance():
    """Step 3: Solution Critique - Self-Refine feedback phase."""
    return (
        "Solution Critique",
        [
            "For EACH solution, identify weaknesses:",
            "  - What could go wrong? (failure modes)",
            "  - What does this solution assume that might be false?",
            "  - Where is the complexity hiding?",
            "  - What operational burden does this create?",
            "",
            "Generate SPECIFIC, ACTIONABLE feedback:",
            "  BAD:  'This might have scaling issues'",
            "  GOOD: 'Single-node Redis fails at >100K ops/sec; Solution A",
            "         assumes <50K ops/sec but requirements say 200K'",
            "",
            "Identify which solutions should be:",
            "  - ELIMINATED: fatal flaw, violates hard constraint",
            "  - REFINED: fixable weakness, needs modification",
            "  - ADVANCED: no obvious flaws, proceed to verification",
            "",
            "For REFINED solutions, state the specific modification needed",
        ],
        [
            "SOLUTIONS (from step 2)",
            "CRITIQUE for each (specific weaknesses, failure modes)",
            "DISPOSITION: ELIMINATED / REFINED / ADVANCED for each",
            "MODIFICATIONS needed for REFINED solutions",
        ],
    )


def get_verification_guidance():
    """
    Steps 4 to N-2: Factored Assumption Verification.

    Key insight from CoVe: answer verification questions WITHOUT attending
    to the original solutions. Models that see their own hallucinations
    tend to repeat them.
    """
    return (
        "Factored Verification",
        [
            "FACTORED VERIFICATION (answer WITHOUT looking at solutions):",
            "",
            "Step A - List assumptions as OPEN questions:",
            "  BAD:  'Is Redis faster?' (yes/no triggers agreement bias)",
            "  GOOD: 'What are the latency characteristics of Redis vs",
            "         Memcached under write-heavy workloads?'",
            "",
            "Step B - Answer each question INDEPENDENTLY:",
            "  - Pretend you have NOT seen the solutions",
            "  - Answer from first principles or domain knowledge",
            "  - Do NOT defend any solution; seek truth",
            "  - Cite sources or reasoning for each answer",
            "",
            "Step C - Categorize each assumption:",
            "  VERIFIED:  evidence confirms the assumption",
            "  FALSIFIED: evidence contradicts (note: 'claimed X, actually Y')",
            "  UNCERTAIN: insufficient evidence; note what would resolve it",
        ],
        [
            "SOLUTIONS still under consideration",
            "VERIFICATION QUESTIONS (open, not yes/no)",
            "ANSWERS (independent, from first principles)",
            "CATEGORIZED: VERIFIED / FALSIFIED / UNCERTAIN for each",
        ],
    )


def get_crosscheck_guidance():
    """
    Step N-1: Cross-check - reconcile verified facts with original claims.

    From CoVe Factor+Revise: explicit cross-check achieves +7.7 FACTSCORE
    points over factored verification alone.
    """
    return (
        "Cross-Check",
        [
            "Reconcile verified facts with solution claims:",
            "",
            "For EACH surviving solution:",
            "  - Which claims are now SUPPORTED by verification?",
            "  - Which claims are CONTRADICTED? (list specific contradictions)",
            "  - Which claims remain UNTESTED?",
            "",
            "Update solution viability:",
            "  - Mark solutions with falsified CORE assumptions as ELIMINATED",
            "  - Note which solutions gained credibility (verified strengths)",
            "  - Note which solutions lost credibility (falsified claims)",
            "",
            "Check for EMERGENT solutions:",
            "  - Do verified facts suggest an approach not previously considered?",
            "  - Can surviving solutions be combined based on verified strengths?",
        ],
        [
            "SOLUTIONS with updated status",
            "SUPPORTED claims (with evidence)",
            "CONTRADICTED claims (with specific contradictions)",
            "UNTESTED claims",
            "ELIMINATED solutions (if any, with reason)",
            "EMERGENT solutions (if any)",
        ],
    )


def get_final_step_guidance():
    """Final step: Structured Trade-off Synthesis."""
    return (
        "Trade-off Synthesis",
        [
            "STRUCTURED SYNTHESIS:",
            "",
            "1. SURVIVING SOLUTIONS:",
            "   List solutions NOT eliminated by falsified assumptions",
            "",
            "2. TRADE-OFF MATRIX (verified facts only):",
            "   For each dimension that matters to the decision:",
            "   - Performance: 'A achieves X; B achieves Y (verified)'",
            "   - Complexity: 'A requires N components; B requires M'",
            "   - Risk: 'A fails when...; B fails when...'",
            "   - Cost: 'A costs X; B costs Y'",
            "",
            "3. DECISION FRAMEWORK:",
            "   'If [hard constraint] is paramount -> choose A because...'",
            "   'If [other priority] matters more -> choose B because...'",
            "   'If uncertain about [X] -> gather [specific data] first'",
            "",
            "4. RECOMMENDATION (if one solution dominates):",
            "   State which solution and the single strongest reason",
            "   Acknowledge what you're giving up by choosing it",
        ],
        [],  # No next step
    )


def get_guidance(step: int, total_steps: int):
    """
    Dispatch to appropriate guidance based on step number.

    New 6-phase structure:
      Step 1:      Decomposition
      Step 2:      Generation
      Step 3:      Critique (Self-Refine feedback)
      Steps 4-N-2: Verification (factored, extra steps go here)
      Step N-1:    Cross-check
      Step N:      Synthesis
    """
    if step == 1:
        return get_step_1_guidance()
    if step == 2:
        return get_step_2_guidance()
    if step == 3:
        return get_step_3_guidance()
    if step == total_steps:
        return get_final_step_guidance()
    if step == total_steps - 1:
        return get_crosscheck_guidance()
    # Steps 4 to N-2 are verification
    return get_verification_guidance()


def format_output(step: int, total_steps: int, thoughts: str) -> str:
    """Format output for display."""
    title, actions, next_state = get_guidance(step, total_steps)
    is_complete = step >= total_steps

    lines = [
        "=" * 70,
        f"THINKDEEP - Step {step}/{total_steps}: {title}",
        "=" * 70,
        "",
        "ACCUMULATED STATE:",
        thoughts[:1200] + "..." if len(thoughts) > 1200 else thoughts,
        "",
        "ACTIONS:",
    ]
    lines.extend(f"  {action}" for action in actions)

    if not is_complete and next_state:
        lines.append("")
        lines.append("NEXT STEP STATE MUST INCLUDE:")
        lines.extend(f"  - {item}" for item in next_state)

    lines.append("")

    if is_complete:
        lines.extend([
            "COMPLETE - Present to user:",
            "  1. Problem and constraints (from decomposition)",
            "  2. Solutions considered (including eliminated ones and why)",
            "  3. Verified facts (from factored verification)",
            "  4. Trade-off matrix with decision framework",
            "  5. Recommendation (if one dominates) or decision criteria",
        ])
    else:
        next_title, _, _ = get_guidance(step + 1, total_steps)
        lines.extend([
            f"NEXT: Step {step + 1} - {next_title}",
            f"REMAINING: {total_steps - step} step(s)",
            "",
            "ADJUST: increase --total-steps if more verification needed (min 6)",
        ])

    lines.extend(["", "=" * 70])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ThinkDeep - Structured deep reasoning",
        epilog=(
            "Phases: decompose (1) -> generate (2) -> critique (3) -> "
            "verify (4 to N-2) -> cross-check (N-1) -> synthesize (N)"
        ),
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--thoughts", type=str, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 6:
        sys.exit("ERROR: --total-steps must be >= 6 (was 4, now requires 6 phases)")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps, args.thoughts))


if __name__ == "__main__":
    main()
