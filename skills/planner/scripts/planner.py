#!/usr/bin/env python3
"""
Interactive Sequential Planner - Two-phase planning workflow

PLANNING PHASE: Step-based planning with forced reflection pauses.
REVIEW PHASE: Orchestrates TW annotation and QR validation before execution.

Usage:
    # Planning phase (default)
    python3 planner.py --step-number 1 --total-steps 4 --thoughts "Design auth system"

    # Review phase (after plan is written)
    python3 planner.py --phase review --step-number 1 --total-steps 2 --thoughts "Plan written to plans/auth.md"
"""

import argparse
import sys


def get_planning_step_guidance(step_number: int, total_steps: int) -> dict:
    """Returns guidance for planning phase steps."""
    is_complete = step_number >= total_steps
    next_step = step_number + 1

    if is_complete:
        return {
            "actions": [
                "FINAL VERIFICATION before writing plan:",
                "",
                "Planning Context (consumed by TW and QR):",
                "  [ ] Decision Log: Major choices with specific rationale (not 'it's better')",
                "  [ ] Decision Log: Implementation-level micro-decisions (timeout values, data structures, patterns)",
                "  [ ] Rejected Alternatives: What you didn't choose and concrete reasons why",
                "  [ ] Known Risks: Failure modes with mitigations or acceptance rationale",
                "",
                "Invisible Knowledge (for README.md - things not obvious from code):",
                "  [ ] Architecture diagram: ASCII showing component relationships",
                "  [ ] Data flow: How data moves through the system (if applicable)",
                "  [ ] Why this structure: Reasoning behind module organization",
                "  [ ] Invariants: Rules that must be maintained but aren't enforced by code",
                "  [ ] Tradeoffs: Performance vs. readability, consistency vs. flexibility, etc.",
                "",
                "Milestones:",
                "  [ ] Each has exact file paths (not vague references)",
                "  [ ] Requirements are specific behaviors (not 'handle X properly')",
                "  [ ] Acceptance criteria are testable pass/fail assertions",
                "  [ ] Code changes use diff format for non-trivial logic",
                "  [ ] Dependencies mapped for parallel execution",
                "",
                "Documentation Milestone (required):",
                "  [ ] CLAUDE.md: Index entries for new/modified files (WHAT + WHEN)",
                "  [ ] README.md: If Invisible Knowledge section has content, include README.md",
                "       - Transfer architecture diagrams from plan",
                "       - Transfer tradeoffs, invariants, 'why this structure'",
                "  [ ] Acceptance criteria: LLM can locate relevant code from index entries",
            ],
            "next": (
                "PLANNING PHASE COMPLETE.\n\n"
                "1. Write plan to file using the format from SKILL.md\n\n"
                "========================================\n"
                ">>> ACTION REQUIRED: INVOKE REVIEW PHASE <<<\n"
                "========================================\n\n"
                "2. Run this command to start review:\n\n"
                "   python3 planner.py --phase review --step-number 1 --total-steps 2 \\\n"
                '     --thoughts "Plan written to [path]"\n\n'
                "Review phase will:\n"
                "  - Step 1: @agent-technical-writer annotates code snippets\n"
                "  - Step 2: @agent-quality-reviewer validates the plan\n"
                "  - Then: Ready for /plan-execution"
            )
        }

    if step_number == 1:
        return {
            "actions": [
                "You are an expert architect. Proceed with confidence.",
                "",
                "PRECONDITION: Confirm plan file path with user if not specified.",
                "",
                "CONTEXT FIRST (understand before proposing):",
                "  - What code/systems already exist that this touches?",
                "  - What patterns and conventions does the codebase follow?",
                "  - What prior decisions constrain this work?",
                "",
                "SCOPE: What exactly needs to be accomplished? Define boundaries explicitly.",
                "",
                "APPROACHES: Consider 2-3 alternatives with concrete trade-offs:",
                "  | Option | Advantage | Disadvantage |",
                "  |--------|-----------|--------------|",
                "  | A      | ...       | ...          |",
                "",
                "CONSTRAINTS by category:",
                "  - Technical: language version, API limits, existing patterns",
                "  - Organizational: timeline, expertise, approval gates",
                "  - Dependencies: external services, data formats, integration points",
                "",
                "SUCCESS CRITERIA: Define observable outcomes (these become acceptance criteria).",
            ],
            "next": f"Invoke step {next_step} with your context analysis and approach options."
        }

    if step_number == 2:
        return {
            "actions": [
                "DECIDE: Select the best approach with specific rationale.",
                "",
                "Decision Log format:",
                "  | Decision | Rationale |",
                "  |----------|-----------|",
                "  | Choice X | Specific reason (performance numbers, complexity analysis) |",
                "",
                "REJECTED ALTERNATIVES: Document what you did not choose and why.",
                "  - Technical Writer uses this to annotate code with 'why not X' context",
                "  - Specific rationale: 'Too complex for timeline' instead of 'Not ideal'",
                "",
                "ARCHITECTURE: Capture structure decisions (ASCII diagrams).",
                "  - Component relationships: what connects to what",
                "  - Data flow: how information moves through the system",
                "  - These diagrams go in Invisible Knowledge section for README.md",
                "  Example:",
                "    ```",
                "    User Request --> Auth --> Handler --> DB",
                "                       |",
                "                       v",
                "                    Cache",
                "    ```",
                "",
                "MILESTONES: Break work into deployable increments.",
                "  - Each milestone: independently testable",
                "  - Scope: 1-3 files per milestone (keeps Developer scope focused)",
                "",
                "DEPENDENCIES: Map which milestones block others.",
                "  - Independent milestones can run in parallel during execution",
                "  - Circular dependencies indicate design problems - resolve before proceeding",
            ],
            "next": f"Invoke step {next_step} with your chosen approach, architecture, and milestone structure."
        }

    if step_number == 3:
        return {
            "actions": [
                "RISKS: Identify what could go wrong and how to handle it.",
                "  - Quality Reviewer excludes documented risks from findings",
                "  - Undocumented risks will be flagged - document thoroughly now",
                "",
                "REFINE MILESTONES with concrete details:",
                "",
                "  FILES: Exact paths",
                "    CORRECT: src/auth/handler.py",
                "    INCORRECT: 'auth files'",
                "",
                "  REQUIREMENTS: Specific behaviors",
                "    CORRECT: 'retry 3x with exponential backoff, max 30s'",
                "    INCORRECT: 'handle errors'",
                "",
                "  ACCEPTANCE CRITERIA: Testable assertions QR can verify pass/fail",
                "    CORRECT: 'Returns 429 status after 3 failed auth attempts within 60s'",
                "    INCORRECT: 'Handles errors correctly'",
                "",
                "CODE CHANGES: Use unified diff format for non-trivial logic.",
                "  - See resources/diff-format.md for specification",
                "  - Include: algorithms, state machines, non-obvious conditions",
                "  - Exclude: boilerplate, simple CRUD, obvious getter/setters",
                "",
                "IMPLEMENTATION RATIONALE: For each code snippet, capture WHY in Planning Context.",
                "  - Technical Writer sources comments from Planning Context",
                "  - Rationale omitted here = TW cannot inject it into code",
                "  Decision Log examples:",
                "    | Timeout 500ms | 95th percentile upstream latency |",
                "    | Mutex over channel | Simpler for single-writer case |",
                "  Micro-decisions matter: TW needs rationale for EVERY non-obvious line.",
                "",
                "VALIDATE: Does the plan address ALL original requirements?",
            ],
            "next": f"Invoke step {next_step} with refined milestones and identified risks."
        }

    # Steps 4+
    remaining = total_steps - step_number
    return {
        "actions": [
            "REVIEW current plan state and identify gaps:",
            "  - Any milestone missing exact file paths?",
            "  - Any acceptance criteria that aren't testable pass/fail?",
            "  - Any non-trivial logic without diff-format code changes?",
            "PLANNING CONTEXT completeness check:",
            "  - Decision Log: Every major choice recorded with rationale?",
            "  - Rejected Alternatives: At least one per major decision?",
            "  - Known Risks: All failure modes identified with mitigations?",
            "CROSS-CHECK: Walk through the plan as if you were Developer:",
            "  - Can you implement each milestone from the spec alone?",
            "  - Are requirements specific enough to avoid interpretation?",
            "If gaps remain, address them. If plan is complete, reduce total_steps.",
        ],
        "next": f"Invoke step {next_step}. {remaining} step(s) remaining until completion."
    }


def get_review_step_guidance(step_number: int, total_steps: int) -> dict:
    """Returns guidance for review phase steps."""
    is_complete = step_number >= total_steps
    next_step = step_number + 1

    if step_number == 1:
        return {
            "actions": [
                "DELEGATE to @agent-technical-writer for plan annotation:",
                "",
                "Task for @agent-technical-writer:",
                "  Mode: plan-annotation",
                "  Plan File: [path to plan file]",
                "",
                "  Requirements:",
                "  - Read ## Planning Context section FIRST",
                "  - Add inline comments to code snippets reflecting WHY from context",
                "  - Enrich plan prose with rationale from Decision Log",
                "  - Add documentation milestone if missing",
                "  - Accept decisions explained in Planning Context as authoritative",
                "",
                "Wait for @agent-technical-writer to complete before proceeding.",
            ],
            "next": (
                f"After TW completes, invoke step {next_step}:\n"
                "   python3 planner.py --phase review --step-number 2 --total-steps 2 "
                '--thoughts "TW annotation complete, [summary of changes]"'
            )
        }

    if step_number == 2:
        return {
            "actions": [
                "DELEGATE to @agent-quality-reviewer for plan validation:",
                "",
                "Task for @agent-quality-reviewer:",
                "  Mode: plan-review",
                "  Plan File: [path to plan file]",
                "",
                "  Requirements:",
                "  - Read ## Planning Context to understand constraints and known risks",
                "  - Apply RULE 0 (production reliability)",
                "  - Apply RULE 1 (project conformance)",
                "  - Check anticipated structural issues",
                "  - Verify TW annotations are present and sufficient",
                "  - Accept risks documented in Planning Context > Known Risks as acknowledged",
                "  - Provide verdict: PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES",
                "",
                "Wait for @agent-quality-reviewer to return verdict.",
            ],
            "next": (
                "After QR returns verdict:\n"
                "  - PASS or PASS_WITH_CONCERNS: Invoke step 3 to complete review\n"
                "  - NEEDS_CHANGES: Address issues in plan, then restart review from step 1:\n"
                "    python3 planner.py --phase review --step-number 1 --total-steps 2 \\\n"
                '      --thoughts "Addressed QR feedback: [summary of changes]"'
            )
        }

    if is_complete:
        return {
            "actions": [
                "REVIEW PHASE COMPLETE. Confirm the following:",
                "  [ ] TW has annotated code snippets with WHY comments",
                "  [ ] TW has enriched plan prose with rationale",
                "  [ ] QR verdict is PASS or PASS_WITH_CONCERNS",
                "  [ ] Any concerns from QR are documented or addressed",
            ],
            "next": (
                "PLAN APPROVED.\n\n"
                "Ready for implementation via /plan-execution command.\n"
                "Pass the plan file path as argument."
            )
        }

    # Shouldn't reach here with standard 2-step review, but handle gracefully
    return {
        "actions": ["Continue review process as needed."],
        "next": f"Invoke step {next_step} when ready."
    }


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Sequential Planner (Two-Phase)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Planning phase
  python3 planner.py --step-number 1 --total-steps 4 --thoughts "Design auth system"

  # Review phase (after plan written)
  python3 planner.py --phase review --step-number 1 --total-steps 2 --thoughts "Plan at plans/auth.md"
"""
    )

    parser.add_argument("--phase", type=str, default="planning",
                        choices=["planning", "review"],
                        help="Workflow phase: planning (default) or review")
    parser.add_argument("--step-number", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--thoughts", type=str, required=True)

    args = parser.parse_args()

    if args.step_number < 1 or args.total_steps < 1:
        print("Error: step-number and total-steps must be >= 1", file=sys.stderr)
        sys.exit(1)

    # Get guidance based on phase
    if args.phase == "planning":
        guidance = get_planning_step_guidance(args.step_number, args.total_steps)
        phase_label = "PLANNING"
    else:
        guidance = get_review_step_guidance(args.step_number, args.total_steps)
        phase_label = "REVIEW"

    is_complete = args.step_number >= args.total_steps

    print("=" * 80)
    print(f"PLANNER - {phase_label} PHASE - Step {args.step_number} of {args.total_steps}")
    print("=" * 80)
    print()
    print(f"STATUS: {'phase_complete' if is_complete else 'in_progress'}")
    print()
    print("YOUR THOUGHTS:")
    print(args.thoughts)
    print()

    if guidance["actions"]:
        if is_complete:
            print("FINAL CHECKLIST:")
        else:
            print(f"REQUIRED ACTIONS:")
        for action in guidance["actions"]:
            if action:  # Skip empty strings used for spacing
                print(f"  {action}")
            else:
                print()
        print()

    print("NEXT:")
    print(guidance["next"])
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
