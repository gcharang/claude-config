#!/usr/bin/env python3
"""
Decision Critic - Structured decision criticism workflow.

Seven-step workflow:
  1-2: DECOMPOSITION - Extract structure, classify verifiability
  3-4: VERIFICATION - Generate questions, factored verification
  5-6: CHALLENGE - Contrarian perspective, alternative framing
  7:   SYNTHESIS - Verdict and recommendation

Research grounding:
  - Chain-of-Verification (Dhuliawala et al., 2023)
  - Self-Consistency (Wang et al., 2023)
"""

import argparse
import sys

from skills.lib.workflow.formatters.text import format_text_output


STEPS = {
    1: {
        "title": "Extract Structure",
        "phase": "DECOMPOSITION",
        "actions": [
            "Extract and assign stable IDs (persist through ALL steps):",
            "",
            "CLAIMS [C1, C2, ...] - Factual assertions (3-7)",
            "  What facts/cause-effect relationships are assumed?",
            "",
            "ASSUMPTIONS [A1, A2, ...] - Unstated beliefs (2-5)",
            "  What is implied but not stated?",
            "",
            "CONSTRAINTS [K1, K2, ...] - Hard boundaries (1-4)",
            "  Technical/organizational limitations?",
            "",
            "JUDGMENTS [J1, J2, ...] - Subjective tradeoffs (1-3)",
            "  Where are values weighed against each other?",
            "",
            "FORMAT: C1: <claim> | A1: <assumption> | K1: <constraint>",
        ],
    },
    2: {
        "title": "Classify Verifiability",
        "phase": "DECOMPOSITION",
        "actions": [
            "Classify each item from Step 1:",
            "",
            "[V] VERIFIABLE - Can be checked against evidence",
            "[J] JUDGMENT - Subjective, no objective answer",
            "[C] CONSTRAINT - Given condition, accepted as fixed",
            "",
            "Edge case: prefer [V] over [J] over [C]",
            "",
            "FORMAT: C1 [V]: <claim> | A1 [J]: <assumption>",
            "COUNT: State how many [V] items need verification.",
        ],
    },
    3: {
        "title": "Generate Verification Questions",
        "phase": "VERIFICATION",
        "actions": [
            "For each [V] item, generate 1-3 verification questions:",
            "",
            "CRITERIA:",
            "  - Specific and independently answerable",
            "  - Designed to FALSIFY (not confirm)",
            "  - Each tests different aspect",
            "",
            "FORMAT:",
            "  C1 [V]: <claim>",
            "    Q1: <question>",
            "    Q2: <question>",
        ],
    },
    4: {
        "title": "Factored Verification",
        "phase": "VERIFICATION",
        "actions": [
            "Answer each question INDEPENDENTLY (most important step).",
            "",
            "EPISTEMIC BOUNDARY:",
            "  Use ONLY: established knowledge, stated constraints, logical inference",
            "  Do NOT: assume decision is correct/incorrect and work backward",
            "",
            "SEPARATE answer from implication:",
            "  Answer: factual response (evidence-based)",
            "  Implication: what this means for claim",
            "",
            "Mark each [V] item:",
            "  VERIFIED - answers consistent with claim",
            "  FAILED - answers reveal inconsistency/error",
            "  UNCERTAIN - insufficient evidence",
        ],
    },
    5: {
        "title": "Contrarian Perspective",
        "phase": "CHALLENGE",
        "actions": [
            "Generate the STRONGEST argument AGAINST the decision.",
            "",
            "Start from verification results:",
            "  FAILED = direct ammunition",
            "  UNCERTAIN = attack vectors",
            "",
            "Steel-man the opposition (best case, not strawman):",
            "  - What could go wrong?",
            "  - What alternatives dismissed too quickly?",
            "  - What second-order effects missed?",
            "",
            "OUTPUT:",
            "  CONTRARIAN POSITION: <one sentence>",
            "  ARGUMENT: <2-3 paragraphs>",
            "  KEY RISKS: <bullet list>",
        ],
    },
    6: {
        "title": "Alternative Framing",
        "phase": "CHALLENGE",
        "actions": [
            "Challenge the PROBLEM STATEMENT (not solution).",
            "",
            "Set aside proposed solution and ask:",
            "  - Is this the right problem or a symptom?",
            "  - What would a different stakeholder prioritize?",
            "  - What if constraints were negotiable?",
            "  - Is there a simpler formulation?",
            "",
            "OUTPUT:",
            "  ALTERNATIVE FRAMING: <one sentence>",
            "  WHAT THIS EMPHASIZES: <paragraph>",
            "  HIDDEN ASSUMPTIONS REVEALED: <list>",
            "  IMPLICATION FOR DECISION: <paragraph>",
        ],
    },
    7: {
        "title": "Synthesis and Verdict",
        "phase": "SYNTHESIS",
        "actions": [
            "VERDICT RUBRIC:",
            "",
            "ESCALATE when:",
            "  - Any FAILED on safety/security/compliance",
            "  - Any critical UNCERTAIN that cannot be cheaply verified",
            "  - Alternative framing reveals problem itself is wrong",
            "",
            "REVISE when:",
            "  - Any FAILED on core claim",
            "  - Multiple UNCERTAIN on feasibility/effort/impact",
            "  - Challenge phase revealed unaddressed gaps",
            "",
            "STAND when:",
            "  - No FAILED on core claims",
            "  - UNCERTAIN items explicitly acknowledged as accepted risks",
            "  - Challenges addressable within current approach",
            "",
            "OUTPUT:",
            "  VERDICT: STAND | REVISE | ESCALATE",
            "  VERIFICATION SUMMARY: (Verified/Failed/Uncertain lists)",
            "  CHALLENGE ASSESSMENT: (strongest challenge, response)",
            "  RECOMMENDATION: (specific next action)",
        ],
    },
}




def main():
    parser = argparse.ArgumentParser(
        description="Decision Critic - Structured criticism workflow",
        epilog="Phases: decompose (1-2) -> verify (3-4) -> challenge (5-6) -> synthesize (7)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--decision", type=str, help="Decision to critique (step 1)")

    args = parser.parse_args()

    if args.step < 1 or args.step > 7:
        sys.exit("Error: step must be 1-7")
    if args.total_steps < 7:
        sys.exit("Error: total-steps must be >= 7")
    if args.step == 1 and not args.decision:
        sys.exit("Error: --decision required for step 1")

    info = STEPS.get(args.step, STEPS[7])
    next_info = STEPS.get(args.step + 1, STEPS[7]) if args.step < args.total_steps else None

    # Add decision context to actions for step 1
    actions = info["actions"]
    if args.step == 1 and args.decision:
        actions = [f"DECISION UNDER REVIEW: {args.decision}", ""] + actions

    print(format_text_output(
        step=args.step,
        total=args.total_steps,
        title=f"DECISION CRITIC - {info['title']}",
        actions=actions,
        brief=f"Phase: {info['phase']}",
        next_title=next_info["title"] if next_info else None,
    ))


if __name__ == "__main__":
    main()
