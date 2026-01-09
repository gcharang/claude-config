#!/usr/bin/env python3
"""
Prompt Engineer Skill - Compact multi-turn prompt optimization workflow.

Five-phase workflow:
  1. Assess    - Triage complexity + blind problem identification
  2. Plan      - Match techniques, propose changes with evidence
  3. Refine    - Self-Refine loop (verify -> feedback -> update)
  4. Approve   - Present to human, HARD GATE
  5. Execute   - Apply changes + integration check

Research grounding:
  - Self-Refine (Madaan 2023): Separate feedback from refinement
  - CoVe (Dhuliawala 2023): Factored verification with OPEN questions
  - Technique matching requires quoted trigger conditions from references
"""

import argparse
import sys


STEPS = {
    1: {
        "title": "Assess",
        "brief": "Triage + blind identification (NO references yet)",
        "actions": [
            "READ the prompt file. Classify complexity:",
            "  SIMPLE: <20 lines, single purpose, no conditionals",
            "  COMPLEX: multiple sections, conditionals, tool orchestration",
            "",
            "Document OPERATING CONTEXT:",
            "  - Interaction: single-shot or conversational?",
            "  - Agent type: tool-use, coding, analysis, general?",
            "  - Failure modes: what goes wrong when this fails?",
            "",
            "BLIND identification at THREE LEVELS (quote line evidence):",
            "",
            "  STRUCTURAL: workflow patterns, multi-turn, orchestration",
            "  BEHAVIORAL: identity, confidence, emphasis hierarchy",
            "  STYLISTIC: hedging, missing examples, format clarity",
            "",
            "List ALL opportunities with 'Lines X-Y: [issue]' format.",
            "Do NOT read references yet - prevents pattern-shopping.",
        ],
    },
    2: {
        "title": "Plan",
        "brief": "Match techniques to opportunities",
        "read": [
            "references/prompt-engineering-single-turn.md (always)",
            "references/prompt-engineering-multi-turn.md (if STRUCTURAL)",
            "references/prompt-engineering-subagents.md (if orchestration)",
        ],
        "actions": [
            "For EACH opportunity from step 1:",
            "  1. Find matching technique in references",
            "  2. QUOTE the trigger condition",
            "  3. QUOTE the expected effect",
            "  4. Note stacking compatibility",
            "",
            "PROACTIVE SCAN (even if no opportunity identified):",
            "  - No examples? -> Contrastive Examples, Few-Shot",
            "  - Reasoning needed? -> Plan-and-Solve, RE2",
            "  - Long prompt? -> Document Positioning",
            "",
            "Format each change:",
            "  === CHANGE N: [title] ===",
            "  Level: STRUCTURAL/BEHAVIORAL/STYLISTIC",
            "  Line: [numbers]",
            "  Technique: [name] | Trigger: \"[quoted]\" | Effect: [quoted]",
            "  BEFORE: [original]",
            "  AFTER: [modified]",
            "  TRADEOFF: [downside or None]",
        ],
    },
    3: {
        "title": "Refine",
        "brief": "Self-Refine: verify -> feedback -> update",
        "actions": [
            "VERIFY each proposed technique (factored, OPEN questions):",
            "",
            "  For each technique, answer WITHOUT looking at your proposal:",
            "    'What is the trigger condition for [technique]?' (not yes/no)",
            "    'What text appears at lines X-Y?' (not 'does it have...')",
            "",
            "  Cross-check: CLAIMED vs VERIFIED",
            "    CONSISTENT -> keep",
            "    INCONSISTENT -> revise or remove",
            "",
            "FEEDBACK (specific, actionable):",
            "  BAD:  'Could be improved'",
            "  GOOD: 'Change 3 claims hedging but line 15 is already affirmative'",
            "",
            "UPDATE proposals based on feedback.",
            "Remove changes with mismatched triggers.",
            "Verify no stacking conflicts remain.",
        ],
    },
    4: {
        "title": "Approve",
        "brief": "Present refined plan to user - HARD GATE",
        "actions": [
            "Present using this format:",
            "",
            "PROPOSED CHANGES",
            "================",
            "",
            "| # | Line | Opportunity | Technique | Risk |",
            "|---|------|-------------|-----------|------|",
            "",
            "Then each change in detail (=== CHANGE N ===)",
            "",
            "VERIFICATION SUMMARY:",
            "  - Changes verified: N",
            "  - Changes revised: M",
            "  - Changes removed: K",
            "",
            "ANTI-PATTERNS CHECKED:",
            "  - Hedging Spiral: [OK/FOUND]",
            "  - Everything-Is-Critical: [OK/FOUND]",
            "  - Negative Instruction: [OK/FOUND]",
            "",
            "HARD GATE: Do NOT proceed without explicit user approval.",
        ],
    },
    5: {
        "title": "Execute",
        "brief": "Apply approved changes + integration check",
        "actions": [
            "Apply each approved change to the prompt file.",
            "",
            "INTEGRATION CHECKS after all changes:",
            "  - Cross-section references correct?",
            "  - Terminology consistent throughout?",
            "  - Priority markers not overused? (max 2-3 CRITICAL/NEVER)",
            "",
            "ANTI-PATTERN FINAL AUDIT:",
            "  - Hedging Spiral: accumulated uncertainty?",
            "  - Everything-Is-Critical: emphasis overuse?",
            "  - Negative Instruction: 'don't' instead of 'do'?",
            "",
            "Present final optimized prompt with change summary.",
        ],
    },
}


def format_output(step: int, total_steps: int) -> str:
    """Format compact output for display."""
    info = STEPS.get(step, STEPS[5])  # Default to Execute for extra steps
    is_complete = step >= total_steps

    lines = [
        f"PROMPT ENGINEER - Step {step}/{total_steps}: {info['title']}",
        f"  {info['brief']}",
        "",
    ]

    if "read" in info:
        lines.append("READ:")
        lines.extend(f"  - {r}" for r in info["read"])
        lines.append("")

    lines.append("DO:")
    for action in info["actions"]:
        if action:
            lines.append(f"  {action}")
        else:
            lines.append("")

    lines.append("")

    if is_complete:
        lines.append("COMPLETE - Present optimized prompt to user.")
    else:
        next_info = STEPS.get(step + 1, STEPS[5])
        lines.append(f"NEXT: Step {step + 1} - {next_info['title']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Prompt Engineer - Compact optimization workflow",
        epilog="Phases: assess (1) -> plan (2) -> refine (3) -> approve (4) -> execute (5)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    args = parser.parse_args()

    if args.step < 1:
        sys.exit("ERROR: --step must be >= 1")
    if args.total_steps < 5:
        sys.exit("ERROR: --total-steps must be >= 5")
    if args.step > args.total_steps:
        sys.exit("ERROR: --step cannot exceed --total-steps")

    print(format_output(args.step, args.total_steps))


if __name__ == "__main__":
    main()
