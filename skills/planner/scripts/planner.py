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
                "FINAL VERIFICATION — complete each section before writing.",
                "",
                "<planning_context_verification>",
                "TW and QR consume this section VERBATIM. Quality here =",
                "quality of annotations and risk detection downstream.",
                "",
                "Decision Log:",
                "  - What major architectural choice did you make?",
                "  - What is the multi-step reasoning chain for that choice?",
                "  - What micro-decisions (timeouts, data structures) need",
                "    rationale for TW to document?",
                "",
                "Rejected Alternatives:",
                "  - What approach did you NOT take?",
                "  - What concrete reason ruled it out?",
                "",
                "Known Risks:",
                "  - What failure modes exist?",
                "  - What mitigation or acceptance rationale exists for each?",
                "</planning_context_verification>",
                "",
                "<invisible_knowledge_verification>",
                "This section sources README.md content. Skip if trivial.",
                "",
                "  - What is the component relationship diagram?",
                "  - What is the data flow through the system?",
                "  - Why is the module organization structured this way?",
                "  - What invariants must be maintained?",
                "  - What tradeoffs were made (and their costs/benefits)?",
                "</invisible_knowledge_verification>",
                "",
                "<milestone_verification>",
                "For EACH milestone, verify:",
                "  - File paths: exact (src/auth/handler.py) not vague?",
                "  - Requirements: specific behaviors, not 'handle X'?",
                "  - Acceptance criteria: testable pass/fail assertions?",
                "  - Code changes: diff format for non-trivial logic?",
                "  - Uncertainty flags: added where applicable?",
                "</milestone_verification>",
                "",
                "<documentation_milestone_verification>",
                "  - Does a Documentation milestone exist?",
                "  - Does CLAUDE.md use TABULAR INDEX format (not prose)?",
                "  - Is README.md included only if Invisible Knowledge has",
                "    content?",
                "</documentation_milestone_verification>",
            ],
            "next": (
                "PLANNING PHASE COMPLETE.\n\n"
                "1. Write plan to file using the format from SKILL.md\n\n"
                "============================================\n"
                ">>> ACTION REQUIRED: INVOKE REVIEW PHASE <<<\n"
                "============================================\n\n"
                "SKIPPING REVIEW MEANS:\n"
                "  - Developer has NO prepared comments to transcribe\n"
                "  - Code ships without WHY documentation\n"
                "  - QR findings surface during execution, not before\n\n"
                "2. Run this command to start review:\n\n"
                "   python3 planner.py --phase review --step-number 1 --total-steps 2 \\\n"
                '     --thoughts "Plan written to [path]"\n\n'
                "Review phase:\n"
                "  Step 1: @agent-technical-writer annotates code snippets\n"
                "  Step 2: @agent-quality-reviewer validates the plan\n"
                "  Then: Ready for /plan-execution"
            )
        }

    if step_number == 1:
        return {
            "actions": [
                "You are an expert architect. Proceed with confidence.",
                "",
                "PRECONDITION: Confirm plan file path before proceeding.",
                "",
                "<step_1_checklist>",
                "Complete ALL items before invoking step 2:",
                "",
                "CONTEXT (understand before proposing):",
                "  - [ ] What code/systems does this touch?",
                "  - [ ] What patterns does the codebase follow?",
                "  - [ ] What prior decisions constrain this work?",
                "",
                "SCOPE (define boundaries):",
                "  - [ ] What exactly must be accomplished?",
                "  - [ ] What is OUT of scope?",
                "",
                "APPROACHES (consider alternatives):",
                "  - [ ] 2-3 options with Advantage/Disadvantage for each",
                "",
                "CONSTRAINTS (list by category):",
                "  - [ ] Technical: language, APIs, existing patterns",
                "  - [ ] Organizational: timeline, expertise, approvals",
                "  - [ ] Dependencies: external services, data formats",
                "",
                "SUCCESS (observable outcomes):",
                "  - [ ] Defined testable acceptance criteria",
                "</step_1_checklist>",
            ],
            "next": f"Invoke step {next_step} with your context analysis and approach options."
        }

    if step_number == 2:
        return {
            "actions": [
                "<step_2_evaluate_first>",
                "BEFORE deciding, evaluate each approach from step 1:",
                "  | Approach | P(success) | Failure mode | Backtrack cost |",
                "",
                "STOP CHECK: If ALL approaches show LOW probability or HIGH",
                "backtrack cost, STOP. Request clarification from user.",
                "</step_2_evaluate_first>",
                "",
                "<step_2_decide>",
                "Select approach. Record in Decision Log with MULTI-STEP chain:",
                "",
                "  INSUFFICIENT: 'Polling | Webhooks are unreliable'",
                "  SUFFICIENT:   'Polling | 30% webhook failure in testing",
                "                 -> would need fallback anyway -> simpler primary'",
                "",
                "Include BOTH architectural AND micro-decisions (timeouts, etc).",
                "</step_2_decide>",
                "",
                "<step_2_rejected>",
                "Document rejected alternatives with CONCRETE reasons.",
                "TW uses this for 'why not X' code comments.",
                "</step_2_rejected>",
                "",
                "<step_2_architecture>",
                "Capture in ASCII diagrams:",
                "  - Component relationships",
                "  - Data flow",
                "These go in Invisible Knowledge for README.md.",
                "</step_2_architecture>",
                "",
                "<step_2_milestones>",
                "Break into deployable increments:",
                "  - Each milestone: independently testable",
                "  - Scope: 1-3 files per milestone",
                "  - Map dependencies (circular = design problem)",
                "</step_2_milestones>",
            ],
            "next": f"Invoke step {next_step} with your chosen approach (include state evaluation summary), architecture, and milestone structure."
        }

    if step_number == 3:
        return {
            "actions": [
                "<step_3_risks>",
                "Document risks NOW. QR excludes documented risks from findings.",
                "Undocumented risks WILL be flagged.",
                "",
                "For each risk:",
                "  | Risk | Mitigation or 'Accepted: [reason]' |",
                "</step_3_risks>",
                "",
                "<step_3_uncertainty_flags>",
                "For EACH milestone, check these conditions -> add flag:",
                "",
                "  | Condition                          | Flag                    |",
                "  |------------------------------------|-------------------------|",
                "  | Multiple valid implementations     | needs TW rationale      |",
                "  | Depends on external system         | needs error review      |",
                "  | First use of pattern in codebase   | needs conformance check |",
                "",
                "Add to milestone: **Flags**: [list]",
                "</step_3_uncertainty_flags>",
                "",
                "<step_3_refine_milestones>",
                "Verify EACH milestone has:",
                "",
                "FILES — exact paths:",
                "  CORRECT: src/auth/handler.py",
                "  WRONG:   'auth files'",
                "",
                "REQUIREMENTS — specific behaviors:",
                "  CORRECT: 'retry 3x with exponential backoff, max 30s'",
                "  WRONG:   'handle errors'",
                "",
                "ACCEPTANCE CRITERIA — testable pass/fail:",
                "  CORRECT: 'Returns 429 after 3 failed attempts within 60s'",
                "  WRONG:   'Handles errors correctly'",
                "",
                "CODE CHANGES — diff format for non-trivial logic.",
                "</step_3_refine_milestones>",
                "",
                "<step_3_validate>",
                "Cross-check: Does the plan address ALL original requirements?",
                "</step_3_validate>",
            ],
            "next": f"Invoke step {next_step} with refined milestones, risks, and uncertainty flags."
        }

    # Steps 4+
    remaining = total_steps - step_number
    return {
        "actions": [
            "<backtrack_check>",
            "BEFORE proceeding, verify no dead ends:",
            "  - Has new information invalidated a prior decision?",
            "  - Is a milestone now impossible given discovered constraints?",
            "  - Are you adding complexity to work around a fundamental issue?",
            "",
            "If YES to any: invoke earlier step with --thoughts explaining change.",
            "</backtrack_check>",
            "",
            "<gap_analysis>",
            "Review current plan state. What's missing?",
            "  - Any milestone without exact file paths?",
            "  - Any acceptance criteria not testable pass/fail?",
            "  - Any non-trivial logic without diff-format code?",
            "  - Any milestone missing uncertainty flags where applicable?",
            "</gap_analysis>",
            "",
            "<planning_context_check>",
            "  - Decision Log: Every major choice has multi-step reasoning?",
            "  - Rejected Alternatives: At least one per major decision?",
            "  - Known Risks: All failure modes identified with mitigations?",
            "</planning_context_check>",
            "",
            "<developer_walkthrough>",
            "Walk through the plan as if you were Developer:",
            "  - Can you implement each milestone from the spec alone?",
            "  - Are requirements specific enough to avoid interpretation?",
            "",
            "If gaps remain, address them. If complete, reduce total_steps.",
            "</developer_walkthrough>",
        ],
        "next": f"Invoke step {next_step}. {remaining} step(s) remaining until completion. (Or invoke earlier step if backtracking.)"
    }


def get_review_step_guidance(step_number: int, total_steps: int) -> dict:
    """Returns guidance for review phase steps."""
    is_complete = step_number >= total_steps
    next_step = step_number + 1

    if step_number == 1:
        return {
            "actions": [
                "<review_step_1_delegate_tw>",
                "DELEGATE to @agent-technical-writer:",
                "",
                "  <delegation>",
                "    <agent>@agent-technical-writer</agent>",
                "    <mode>plan-annotation</mode>",
                "    <plan_source>[path to plan file]</plan_source>",
                "    <task>",
                "      1. Read ## Planning Context section FIRST",
                "      2. Prioritize annotation by uncertainty (HIGH/MEDIUM/LOW)",
                "      3. Add WHY comments to code snippets from Decision Log",
                "      4. Enrich plan prose with rationale",
                "      5. Add documentation milestone if missing",
                "      6. FLAG any non-obvious logic lacking rationale",
                "    </task>",
                "  </delegation>",
                "",
                "Wait for @agent-technical-writer to complete.",
                "</review_step_1_delegate_tw>",
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
                "<review_step_2_delegate_qr>",
                "DELEGATE to @agent-quality-reviewer:",
                "",
                "  <delegation>",
                "    <agent>@agent-quality-reviewer</agent>",
                "    <mode>plan-review</mode>",
                "    <plan_source>[path to plan file]</plan_source>",
                "    <task>",
                "      1. Read ## Planning Context (constraints, known risks)",
                "      2. Write out CONTEXT FILTER before reviewing milestones",
                "      3. Apply RULE 0 (production reliability) with open questions",
                "      4. Apply RULE 1 (project conformance)",
                "      5. Check anticipated structural issues",
                "      6. Verify TW annotations pass actionability test",
                "      7. Accept risks documented in Known Risks as acknowledged",
                "      8. Pay extra attention to milestones with uncertainty flags",
                "    </task>",
                "    <expected_output>",
                "      Verdict: PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES",
                "    </expected_output>",
                "  </delegation>",
                "",
                "Wait for @agent-quality-reviewer verdict.",
                "</review_step_2_delegate_qr>",
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
                "<review_complete_verification>",
                "Confirm before proceeding to execution:",
                "  - TW has annotated code snippets with WHY comments?",
                "  - TW has enriched plan prose with rationale?",
                "  - TW flagged any gaps in Planning Context rationale?",
                "  - QR verdict is PASS or PASS_WITH_CONCERNS?",
                "  - Any concerns from QR are documented or addressed?",
                "</review_complete_verification>",
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

  # Continue planning
  python3 planner.py --step-number 2 --total-steps 4 --thoughts "..."

  # Backtrack to earlier step if needed
  python3 planner.py --step-number 2 --total-steps 4 --thoughts "New constraint invalidates approach, reconsidering..."

  # Start review (after plan written)
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
