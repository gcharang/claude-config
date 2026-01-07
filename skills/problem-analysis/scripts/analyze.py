#!/usr/bin/env python3
"""
Problem Analysis Skill - Compact structured reasoning workflow.

Four-phase workflow:
  1. Define   - Problem decomposition + initial solution generation
  2. Explore  - Solution expansion + critique
  3. Verify   - Factored verification (OPEN questions, cross-check)
  4. Synthesize - Trade-off analysis + recommendation

Research grounding:
  - ToT (Yao 2023): decompose into evaluable thoughts
  - CoVe (Dhuliawala 2023): OPEN questions, factored verification (17%->70%)
  - Self-Refine (Madaan 2023): actionable feedback
  - Analogical Prompting (Yasunaga 2024): recall distinct problems

Usage:
    python3 analyze.py --step 1 --total-steps 4
"""

import argparse
import sys
from pathlib import Path

# Add skills/ to path for lib.workflow imports
skills_dir = Path(__file__).parent.parent.parent
if str(skills_dir) not in sys.path:
    sys.path.insert(0, str(skills_dir))

from lib.workflow.formatters.text import format_text_output


STEPS = {
    1: {
        "title": "Define",
        "brief": "Problem decomposition + initial solutions",
        "actions": [
            "STATE the problem in one sentence: 'I need to decide X'",
            "",
            "LIST CONSTRAINTS:",
            "  HARD: non-negotiable (latency, accuracy, compatibility)",
            "  SOFT: preferences (can trade off)",
            "",
            "SURFACE ASSUMPTIONS (ask yourself):",
            "  'What am I assuming about scale/load?'",
            "  'What am I assuming will NOT change?'",
            "",
            "GENERATE 2-4 DISTINCT solutions:",
            "  Each must differ on a fundamental axis:",
            "    scope, complexity, control, approach",
            "  For each: name, mechanism, key assumptions, claimed benefits",
            "",
            "Do NOT favor any solution yet.",
        ],
    },
    2: {
        "title": "Explore",
        "brief": "Expand solution space + critique",
        "actions": [
            "EXPAND - Push beyond initial solutions:",
            "  - What axes were NOT represented?",
            "  - What's the OPPOSITE of each solution?",
            "  - What would a different domain do?",
            "  - What's the 80/20 'good enough' option?",
            "  - What if we did NOTHING?",
            "",
            "ADD 1-2 more solutions covering unexplored axes.",
            "",
            "CRITIQUE each solution:",
            "  - What could go wrong? (failure modes)",
            "  - What assumption might be false?",
            "  - Where is complexity hiding?",
            "",
            "SPECIFIC feedback (not vague):",
            "  BAD:  'might have scaling issues'",
            "  GOOD: 'Redis fails at >100K ops/sec; Solution A assumes <50K'",
            "",
            "Mark each: ELIMINATE (fatal flaw) / REFINE (fixable) / ADVANCE",
        ],
    },
    3: {
        "title": "Verify",
        "brief": "Factored verification + cross-check",
        "actions": [
            "FACTORED VERIFICATION (answer WITHOUT looking at solutions):",
            "",
            "Step A - Convert assumptions to OPEN questions:",
            "  BAD:  'Is option A better?' (yes/no = agreement bias)",
            "  GOOD: 'What throughput does option A achieve under load?'",
            "",
            "Step B - Answer each INDEPENDENTLY:",
            "  - Pretend you haven't seen the solutions",
            "  - Answer from first principles",
            "  - Cite reasoning for each answer",
            "",
            "Step C - Categorize:",
            "  VERIFIED / FALSIFIED / UNCERTAIN",
            "",
            "CROSS-CHECK against claims:",
            "  - Which claims SUPPORTED?",
            "  - Which claims CONTRADICTED?",
            "  - Which claims UNTESTED?",
            "",
            "Mark solutions with falsified CORE assumptions as ELIMINATED.",
        ],
    },
    4: {
        "title": "Synthesize",
        "brief": "Trade-off analysis + recommendation",
        "actions": [
            "SURVIVING SOLUTIONS (not eliminated by verification)",
            "",
            "TRADE-OFF MATRIX (verified facts only):",
            "  For each dimension that matters:",
            "    'A achieves X; B achieves Y (verified)'",
            "",
            "DECISION FRAMEWORK:",
            "  'If [constraint] paramount -> A because...'",
            "  'If [priority] matters more -> B because...'",
            "  'If uncertain about [X] -> gather [data] first'",
            "",
            "RECOMMENDATION (if one dominates):",
            "  State which + single strongest reason",
            "  Acknowledge what you're giving up",
        ],
    },
}


def main():
    parser = argparse.ArgumentParser(
        description="Problem Analysis - Compact reasoning workflow",
        epilog="Phases: define (1) -> explore (2) -> verify (3) -> synthesize (4)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 4:
        sys.exit("ERROR: --total-steps must be >= 4")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    # Use shared text formatter
    info = STEPS.get(args.step if args.step <= 4 else (3 if args.step < args.total_steps else 4))
    next_info = STEPS.get(args.step + 1 if args.step + 1 <= 4 else 4) if args.step < args.total_steps else None
    print(format_text_output(
        step=args.step,
        total=args.total_steps,
        title=f"PROBLEM ANALYSIS - {info['title']}",
        actions=info["actions"],
        brief=info["brief"],
        next_title=next_info["title"] if next_info else None,
    ))


if __name__ == "__main__":
    main()
