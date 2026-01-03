#!/usr/bin/env python3
"""
Interactive Sequential Planner - Two-phase planning workflow

PLANNING PHASE: Step-based planning with forced reflection pauses.
REVIEW PHASE: Orchestrates TW scrub and QR validation before execution.

Three Pillars Pattern for QR Verification Loops:
  1. STATE BANNER: Visual header showing loop iteration
  2. STOP CONDITION: Explicit blocker preventing progression
  3. RE-VERIFICATION MODE: Different prompts for first-run vs retry

Usage:
    # Planning phase (default)
    python3 planner.py --step-number 1 --total-steps 4 --thoughts "Design auth system"

    # Review phase (after plan is written)
    python3 planner.py --phase review --step-number 1 --total-steps 3 --thoughts "Plan written to plans/auth.md"

    # Review phase - re-verification after fixing QR issues
    python3 planner.py --phase review --step-number 1 --total-steps 3 \\
      --qr-iteration 2 --fixing-issues --thoughts "Fixed issues, re-verifying..."
"""

import argparse
import sys
from pathlib import Path

from utils import get_qr_state_banner, get_qr_stop_condition


def get_plan_format() -> str:
    """Read the plan format template from resources."""
    format_path = Path(__file__).parent.parent / "resources" / "plan-format.md"
    return format_path.read_text()


def get_planning_step_guidance(step_number: int, total_steps: int) -> dict:
    """Returns guidance for planning phase steps."""
    is_complete = step_number >= total_steps
    next_step = step_number + 1

    if is_complete:
        return {
            "actions": [
                "FINAL VERIFICATION — complete in priority order before writing.",
                "",
                "Work through these verifications in order. Earlier items are",
                "more critical; do not skip ahead.",
                "",
                "---",
                "",
                "VERIFY 1 (CRITICAL): Decision Log Completeness",
                "",
                "TW sources ALL code comments from Decision Log. Missing entries",
                "mean undocumented code.",
                "",
                "  - Every architectural choice has multi-step reasoning?",
                "    INSUFFICIENT: 'Polling | Webhooks are unreliable'",
                "    SUFFICIENT: 'Polling | 30% webhook failure -> need fallback",
                "                 anyway -> simpler as primary'",
                "  - Every micro-decision documented? (timeouts, thresholds,",
                "    concurrency choices, data structure selections)",
                "  - Rejected alternatives listed with concrete reasons?",
                "  - Known risks have mitigations with file:line anchors",
                "    for any behavioral claims?",
                "",
                "---",
                "",
                "VERIFY 2 (CRITICAL): Code Changes Presence",
                "",
                "STOP CHECK: For EACH implementation milestone:",
                "  - Does it contain diff blocks or code snippets?",
                "  - If NO and milestone creates/modifies source files: STOP.",
                "    Add code changes before proceeding.",
                "",
                "Implementation milestones WITHOUT code cannot be approved.",
                "Only documentation milestones (100% .md/.rst files) may skip code.",
                "",
                "---",
                "",
                "VERIFY 3: Diff Format Compliance",
                "",
                "Re-read resources/diff-format.md before writing any code changes.",
                "",
                "  For EACH diff block:",
                "  - File path exact (src/auth/handler.py not 'auth files')?",
                "  - Context lines: 2-3 lines copied VERBATIM from actual file?",
                "  - WHY comments explain rationale, not WHAT code does?",
                "  - No location directives in comments?",
                "  - No hidden baselines ('[adjective] compared to what?')?",
                "",
                "  FORBIDDEN: '...', '[existing code]', summaries, placeholders.",
                "  If you haven't read the target file, read it now.",
                "",
                "---",
                "",
                "VERIFY 4: Milestone Specification",
                "",
                "  For EACH milestone:",
                "  - File paths exact?",
                "  - Requirements are specific behaviors, not 'handle X'?",
                "  - Acceptance criteria are testable pass/fail assertions?",
                "  - Tests section with type, backing, scenarios?",
                "    (or explicit skip reason)",
                "  - Uncertainty flags added where applicable?",
                "",
                "---",
                "",
                "VERIFY 5: Documentation Milestone",
                "",
                "  - Documentation milestone exists?",
                "  - CLAUDE.md uses TABULAR INDEX format?",
                "  - README.md included only if Invisible Knowledge has content?",
                "",
                "---",
                "",
                "VERIFY 6: Comment Hygiene",
                "",
                "Comments will be transcribed VERBATIM. Write in TIMELESS PRESENT.",
                "",
                "  CONTAMINATED: '// Added mutex to fix race condition'",
                "  CLEAN: '// Mutex serializes cache access from concurrent requests'",
                "",
                "  CONTAMINATED: '// After the retry loop'",
                "  CLEAN: (delete -- diff context encodes location)",
                "",
                "---",
                "",
                "VERIFY 7: Assumption Audit Complete",
                "",
                "  - Step 2 assumption audit completed (all categories)?",
                "  - Step 3 decision classification table written?",
                "  - Step 4 file classification table written?",
                "  - No 'assumption' rows remain unresolved?",
                "  - User responses recorded with 'user-specified' backing?",
                "",
                "If any step was skipped: STOP. Go back and complete it.",
            ],
            "next": (
                "PLANNING PHASE COMPLETE.\n\n"
                "1. Write plan to file using this format:\n\n"
                "--- BEGIN PLAN FORMAT ---\n"
                f"{get_plan_format()}\n"
                "--- END PLAN FORMAT ---\n\n"
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
                "  Step 1: @agent-technical-writer scrubs code snippets\n"
                "  Step 2: @agent-quality-reviewer validates the plan\n"
                "  Then: Ready for /plan-execution"
            )
        }

    if step_number == 1:
        return {
            "actions": [
                "STEP 1: Context & Scope Discovery",
                "",
                "You are an expert architect. Proceed with confidence.",
                "",
                "<resource_loading>",
                "BEFORE any planning work, read these resources:",
                "",
                "  1. resources/default-conventions.md",
                "     - Priority hierarchy: user-specified > doc-derived > default-derived > assumption",
                "     - Structural conventions (god objects, file organization)",
                "     - Testing conventions (coverage principles)",
                "",
                "  2. resources/diff-format.md (if code changes anticipated)",
                "     - Unified diff anatomy and components",
                "     - Context line requirements (2-3 VERBATIM lines)",
                "     - WHY comment placement and validation",
                "",
                "  3. resources/temporal-contamination.md",
                "     - Timeless Present Rule for comments",
                "     - Detection heuristics (change-relative, baseline reference, location directive)",
                "",
                "These resources inform decision classification in later steps.",
                "</resource_loading>",
                "",
                "PRECONDITION: Confirm plan file path before proceeding.",
                "",
                "<step_1_focus>",
                "This step focuses on UNDERSTANDING, not deciding.",
                "",
                "CONTEXT (understand before proposing):",
                "  - What code/systems does this touch?",
                "  - What patterns does the codebase follow?",
                "  - What prior decisions constrain this work?",
                "",
                "SCOPE (define boundaries):",
                "  - What exactly must be accomplished?",
                "  - What is OUT of scope?",
                "",
                "CONSTRAINTS (discover blockers):",
                "  - Locate project configuration files (build files, manifests, lock files)",
                "  - Extract ALL version and compatibility constraints",
                "  - Note organizational constraints: timeline, expertise, approvals",
                "  - Note external constraints: services, APIs, data formats",
                "",
                "SUCCESS CRITERIA:",
                "  - Define testable acceptance criteria for the task",
                "</step_1_focus>",
            ],
            "next": f"Invoke step {next_step} with your context analysis and scope definition."
        }

    if step_number == 2:
        return {
            "actions": [
                "STEP 2: Approach Generation",
                "",
                "<step_2_focus>",
                "This step focuses on GENERATING OPTIONS, not selecting.",
                "",
                "APPROACHES (consider alternatives):",
                "  - Generate 2-3 options with Advantage/Disadvantage for each",
                "  - Include at least one 'minimal change' option if applicable",
                "  - Include at least one 'idiomatic/modern' option if applicable",
                "",
                "TARGET TECH RESEARCH (if task involves new tech/migration):",
                "  - What is canonical/idiomatic usage of target tech?",
                "  - Does target tech have different abstractions than source?",
                "    (e.g., per-class loggers vs centralized, hooks vs classes)",
                "  - Document findings for assumption audit in next step.",
                "",
                "  Skip if task doesn't involve adopting new technology/patterns.",
                "",
                "TEST REQUIREMENTS DISCOVERY:",
                "  - Check project docs for test requirements (CLAUDE.md,",
                "    CONTRIBUTING.md, existing test patterns)",
                "  - What test types does the project use/prefer?",
                "  - What testing philosophy? (behavior vs implementation)",
                "",
                "  If project docs silent, default-conventions domain='testing' applies.",
                "  If task is documentation-only, skip test requirements.",
                "</step_2_focus>",
            ],
            "next": f"Invoke step {next_step} with your approach options and tech research findings."
        }

    if step_number == 3:
        return {
            "actions": [
                "STEP 3: Assumption Surfacing & User Confirmation",
                "",
                "<assumption_surfacing_purpose>",
                "This step exists because architectural assumptions feel like",
                "reasonable inference but often aren't. Pattern preservation,",
                "migration strategy, and abstraction boundaries are decisions",
                "that require explicit user confirmation.",
                "",
                "You CANNOT proceed to step 4 without completing this step.",
                "</assumption_surfacing_purpose>",
                "",
                "<assumption_taxonomy>",
                "Six categories of assumptions requiring user confirmation:",
                "",
                "1. PATTERN PRESERVATION",
                "   Assuming new implementation should mirror old structure.",
                "   Example: 'Replace Log() calls with NLog calls' vs",
                "   'Eliminate central Log(); use per-class loggers'",
                "",
                "2. MIGRATION STRATEGY",
                "   Assuming incremental replacement vs paradigm shift.",
                "   Example: 'Wrap old API with new facade' vs",
                "   'Replace API entirely with new patterns'",
                "",
                "3. IDIOMATIC USAGE",
                "   Not aligning with canonical usage of target technology.",
                "   Example: Using class components in React 2024 when",
                "   hooks are the idiomatic pattern.",
                "",
                "4. ABSTRACTION BOUNDARY",
                "   Assuming existing abstractions should persist when",
                "   target technology is designed to eliminate them.",
                "   Example: Keeping a logging facade when the logging",
                "   framework provides per-class loggers.",
                "",
                "5. TEST STRATEGY",
                "   Assuming test approach without checking project requirements.",
                "   Example: 'Write unit tests for each function' when project",
                "   mandates 'integration tests only, no mocks'.",
                "   Priority: user-specified > doc-derived > default-conventions.",
                "",
                "6. POLICY DEFAULTS",
                "   Choosing configuration values where the user/organization",
                "   bears the operational consequence and no objectively correct",
                "   answer exists.",
                "",
                "   The distinguishing test: IF THIS VALUE WERE WRONG, WHO SUFFERS?",
                "   - Technical defaults: Framework authors suffer (bad default",
                "     breaks the framework for everyone). Safe to inherit.",
                "   - Policy defaults: This user/org suffers (they have specific",
                "     operational needs). Must confirm.",
                "",
                "   Common patterns (not exhaustive -- apply the principle):",
                "   - Lifecycle policies (how long, when to expire/clean up)",
                "   - Capacity constraints (limits and behavior at limits)",
                "   - Failure handling (what to do when resources exhausted)",
                "   - Output choices affecting downstream systems or operations",
                "",
                "   When choosing ANY value where the user/org bears consequence,",
                "   present alternatives and confirm before proceeding.",
                "</assumption_taxonomy>",
                "",
                "<assumption_audit_table>",
                "WRITE this table using OPEN questions (not yes/no):",
                "",
                "  | Category | Question | Finding | Needs Confirm? |",
                "  |----------|----------|---------|----------------|",
                "  | Pattern  | What abstraction am I preserving |",
                "  |          | that might not belong in target? | [answer] | [Y/N] |",
                "  |----------|----------|---------|----------------|",
                "  | Migration| Am I doing incremental replacement |",
                "  |          | when paradigm shift is canonical? | [answer] | [Y/N] |",
                "  |----------|----------|---------|----------------|",
                "  | Idiomatic| What is the canonical usage pattern? |",
                "  |          | Does my approach align with it? | [answer] | [Y/N] |",
                "  |----------|----------|---------|----------------|",
                "  | Boundary | What abstraction in source does |",
                "  |          | target tech typically eliminate? | [answer] | [Y/N] |",
                "  |----------|----------|---------|----------------|",
                "  | Test     | What test approach does the project require? |",
                "  |          | Do default-conventions apply, or does project |",
                "  |          | override them? | [answer] | [Y/N] |",
                "  |----------|----------|---------|----------------|",
                "  | Policy   | What values am I choosing where, if wrong, |",
                "  |          | this user/org suffers (not the framework)? |",
                "  |          | Are there meaningful alternatives? | [answer] | [Y/N] |",
                "",
                "For each row, answer the open question first, then determine",
                "if the finding reveals an assumption needing user confirmation.",
                "</assumption_audit_table>",
                "",
                "<user_confirmation_gate>",
                "RULE 0 (ABSOLUTE): User confirms architectural approach.",
                "",
                "If ANY row has 'Y' in Needs Confirm column, you MUST:",
                "  1. Use AskUserQuestion BEFORE proceeding to step 3",
                "  2. Frame as architectural choice, not implementation detail",
                "  3. Present idiomatic approach first with '(Recommended)'",
                "",
                "AskUserQuestion format:",
                "",
                "  questions:",
                "    - question: '[Concise architectural choice framing]'",
                "      header: 'Approach'",
                "      multiSelect: false",
                "      options:",
                "        - label: '[Idiomatic approach] (Recommended)'",
                "          description: '[What this means concretely]'",
                "        - label: '[Pattern-preserving approach]'",
                "          description: '[What this means concretely]'",
                "",
                "Example for NLog migration:",
                "",
                "  question: 'How should logging be structured after migration?'",
                "  options:",
                "    - label: 'Per-class loggers (Recommended)'",
                "      description: 'Each class uses LogManager.GetCurrentClassLogger().",
                "                    Standard NLog pattern. Removes central Log() method.'",
                "    - label: 'Central logging facade'",
                "      description: 'Keep Service1.Log() as wrapper over NLog.",
                "                    Preserves current API but non-idiomatic.'",
                "",
                "DO NOT proceed to step 4 until user responds.",
                "Record user's choice in Decision Log:",
                "  | [choice] | user-specified | User selected: [response] |",
                "",
                "If ALL rows have 'N' (no assumptions needing confirmation):",
                "  State 'No architectural assumptions requiring confirmation.'",
                "  Proceed to step 4 without AskUserQuestion.",
                "</user_confirmation_gate>",
                "",
                "<test_strategy_gate>",
                "Test strategy requires explicit backing (same as other decisions).",
                "",
                "Backing hierarchy:",
                "  1. user-specified: User explicitly stated test requirements",
                "  2. doc-derived: Project CLAUDE.md or docs specify test approach",
                "  3. default-derived: default-conventions domain='testing' applies",
                "",
                "If test strategy 'Needs Confirm' = Y:",
                "",
                "  Triggers for Y:",
                "    - Project docs contradict default-conventions",
                "    - Project docs are ambiguous about test types",
                "    - Task scope makes test applicability unclear",
                "    - User mentioned tests but didn't specify type",
                "",
                "  Use AskUserQuestion:",
                "",
                "    questions:",
                "      - question: 'What testing approach should this implementation use?'",
                "        header: 'Testing'",
                "        multiSelect: false",
                "        options:",
                "          - label: 'Integration tests (Recommended)'",
                "            description: 'Test end-user behavior with real dependencies.",
                "                          Highest value per default conventions.'",
                "          - label: 'Property-based tests'",
                "            description: 'Generative tests for invariant-rich functions.",
                "                          Good input coverage.'",
                "          - label: 'Unit tests'",
                "            description: 'Isolated tests for complex logic.",
                "                          Use sparingly per default conventions.'",
                "          - label: 'No tests'",
                "            description: 'Skip test implementation for this plan.'",
                "",
                "  Record user's choice in Decision Log with 'user-specified' backing.",
                "",
                "If project docs clearly specify test approach:",
                "  Record as 'doc-derived' backing. No AskUserQuestion needed.",
                "",
                "If project docs silent and default-conventions apply cleanly:",
                "  Record as 'default-derived' backing. No AskUserQuestion needed.",
                "</test_strategy_gate>",
            ],
            "next": (
                f"After user confirms approach (or no assumptions found), invoke step {next_step}:\n\n"
                f"   python3 planner.py --step-number {next_step} --total-steps N \\\n"
                '     --thoughts "User confirmed [approach]. Proceeding to evaluate..."'
            )
        }

    if step_number == 4:
        return {
            "actions": [
                "STEP 4: Approach Evaluation & Selection",
                "",
                "<step_4_evaluate_first>",
                "BEFORE deciding, evaluate each approach from step 2:",
                "  | Approach | P(success) | Failure mode | Backtrack cost |",
                "",
                "STOP CHECK: If ALL approaches show LOW probability or HIGH",
                "backtrack cost, STOP. Request clarification from user.",
                "</step_4_evaluate_first>",
                "",
                "<step_4_decide>",
                "Select approach. Record in Decision Log with MULTI-STEP chain:",
                "",
                "  INSUFFICIENT: 'Polling | Webhooks are unreliable'",
                "  SUFFICIENT:   'Polling | 30% webhook failure in testing",
                "                 -> would need fallback anyway -> simpler primary'",
                "",
                "Include BOTH architectural AND micro-decisions (timeouts, etc).",
                "</step_4_decide>",
                "",
                "<step_4_decision_classification>",
                "WRITE this table before proceeding (forces explicit backing):",
                "",
                "  | Decision | Backing | Citation |",
                "  |----------|---------|----------|",
                "  | [choice] | user-specified / doc-derived / default-derived / assumption | [source] |",
                "",
                "Backing tiers (higher overrides lower):",
                "  1. user-specified: 'User said X' -> cite the instruction",
                "  2. doc-derived: 'CLAUDE.md says Y' -> cite file:section",
                "  3. default-derived: 'Convention Z' -> cite <default-conventions domain>",
                "  4. assumption: 'No backing' -> STOP, use AskUserQuestion NOW",
                "",
                "For EACH 'assumption' row: use AskUserQuestion immediately.",
                "Do not proceed to step 5 with unresolved assumptions.",
                "</step_4_decision_classification>",
                "",
                "<step_4_rejected>",
                "Document rejected alternatives with CONCRETE reasons.",
                "TW uses this for 'why not X' code comments.",
                "</step_4_rejected>",
                "",
                "<step_4_architecture>",
                "Capture in ASCII diagrams:",
                "  - Component relationships",
                "  - Data flow",
                "These go in Invisible Knowledge for README.md.",
                "</step_4_architecture>",
                "",
                "<step_4_milestones>",
                "Break into deployable increments:",
                "  - Each milestone: independently testable",
                "  - Scope: 1-3 files per milestone",
                "  - Map dependencies (circular = design problem)",
                "</step_4_milestones>",
            ],
            "next": f"Invoke step {next_step} with your chosen approach (include state evaluation summary), architecture, and milestone structure."
        }

    if step_number == 5:
        return {
            "actions": [
                "STEP 5: Risks, Milestones & Verification",
                "",
                "<step_5_risks>",
                "Document risks NOW. QR excludes documented risks from findings.",
                "",
                "For each risk:",
                "  | Risk | Mitigation | Anchor |",
                "",
                "ANCHOR REQUIREMENT (behavioral claims only):",
                "If mitigation claims existing code behavior ('no change needed',",
                "'already handles X', 'operates on Y'), you MUST cite:",
                "  file:L###-L### + brief excerpt proving the claim",
                "",
                "Skip anchors for:",
                "  - Hypothetical risks ('might timeout under load')",
                "  - External unknowns ('vendor rate limits unclear')",
                "  - Accepted risks with rationale (no code claim)",
                "",
                "INSUFFICIENT (unverified assertion):",
                "  | Dedup breaks | No change; dedup uses TagData | (none) |",
                "",
                "SUFFICIENT (verified with anchor):",
                "  | Dedup breaks | No change; dedup uses TagData |",
                "    worker.go:468 `isIdentical := tag.NumericValue == entry.val` |",
                "",
                "Claims without anchors are ASSUMPTIONS. QR will challenge them.",
                "</step_5_risks>",
                "",
                "<step_5_uncertainty_flags>",
                "For EACH milestone, check these conditions -> add flag:",
                "",
                "  | Condition                          | Flag                    |",
                "  |------------------------------------|-------------------------|",
                "  | Multiple valid implementations     | needs TW rationale      |",
                "  | Depends on external system         | needs error review      |",
                "  | First use of pattern in codebase   | needs conformance check |",
                "",
                "Add to milestone: **Flags**: [list]",
                "</step_5_uncertainty_flags>",
                "",
                "<step_5_refine_milestones>",
                "Verify EACH milestone has:",
                "",
                "FILES -- exact paths:",
                "  CORRECT: src/auth/handler.py",
                "  WRONG:   'auth files'",
                "",
                "REQUIREMENTS -- specific behaviors:",
                "  CORRECT: 'retry 3x with exponential backoff, max 30s'",
                "  WRONG:   'handle errors'",
                "",
                "ACCEPTANCE CRITERIA -- testable pass/fail:",
                "  CORRECT: 'Returns 429 after 3 failed attempts within 60s'",
                "  WRONG:   'Handles errors correctly'",
                "",
                "CODE CHANGES -- diff format for non-trivial logic.",
                "</step_5_refine_milestones>",
                "",
                "<step_5_test_verification>",
                "For EACH implementation milestone, verify test specification:",
                "",
                "  - Tests section present? (or explicit skip reason)",
                "  - Test type backed by: user-specified, doc-derived, or",
                "    default-derived?",
                "  - Scenarios cover: normal path, edge cases, error conditions?",
                "  - Test files specified with exact paths?",
                "",
                "For integration tests spanning multiple milestones:",
                "  - Placed in last milestone that provides required component?",
                "  - Dependencies listed explicitly?",
                "",
                "Test type selection (from default-conventions if no override):",
                "  - Integration tests: end-user behavior, real dependencies (preferred)",
                "  - Property-based tests: invariant-rich functions, wide input coverage",
                "  - Unit tests: complex/critical logic only (use sparingly)",
                "",
                "Remember: Milestone is NOT complete until its tests pass.",
                "Tests provide fast feedback during implementation.",
                "</step_5_test_verification>",
                "",
                "<step_5_file_classification>",
                "For EACH new file in milestones, WRITE this table:",
                "",
                "  | New File | Backing | Citation |",
                "  |----------|---------|----------|",
                "  | path/to/new.go | [tier] | [source] |",
                "",
                "Valid backings for new files:",
                "  - user-specified: User explicitly requested separate file",
                "  - doc-derived: Project convention requires it",
                "  - default-derived: Meets separation trigger (>500 lines, distinct module)",
                "  - assumption: None of the above -> use AskUserQuestion NOW",
                "",
                "Default convention (domain: file-creation, test-organization):",
                "  Extend existing files unless separation trigger applies.",
                "",
                "For EACH 'assumption' row: ask user before finalizing milestones.",
                "</step_5_file_classification>",
                "",
                "<step_5_validate>",
                "Cross-check: Does the plan address ALL original requirements?",
                "</step_5_validate>",
            ],
            "next": f"Invoke step {next_step} with refined milestones, risks, and uncertainty flags."
        }

    # Steps 6+
    remaining = total_steps - step_number
    return {
        "actions": [
            "<backtrack_check>",
            "BEFORE proceeding, check for backtrack signals.",
            "",
            "Common patterns (not exhaustive -- apply the principle):",
            "",
            "  CONSTRAINT_VIOLATION: discovered incompatibility with project constraints",
            "    e.g., feature requires Python 3.10 but project targets 3.8",
            "",
            "  APPROACH_FAILURE: repeated attempts at same problem failing",
            "    e.g., third attempted solution for the same error",
            "",
            "  SCOPE_CREEP: adding complexity to work around fundamental issue",
            "    e.g., milestone growing beyond original file scope",
            "",
            "The principle: if continuing requires undoing earlier decisions,",
            "backtrack to where those decisions were made.",
            "",
            "If backtracking: invoke earlier step with --thoughts explaining change.",
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


def get_review_step_guidance(step_number: int, total_steps: int,
                              plan_file: str,
                              qr_iteration: int = 1, fixing_issues: bool = False) -> dict:
    """Returns guidance for review phase steps.

    Review flow (3 steps):
      Step 1: Parallel QR (Completeness + Code) - MUST spawn both agents
      Step 2: TW Scrub (documentation enrichment)
      Step 3: QR-Docs (documentation quality validation)

    Step 1 spawns BOTH QR agents in parallel. Both restart to planning on failure.
    Step 3 restarts to step 2 on failure (doc issues only).

    Three Pillars Pattern applied at steps 1 and 3 (QR checkpoints):
      1. STATE BANNER: Shows iteration count and mode
      2. STOP CONDITION: Explicit blocker
      3. RE-VERIFICATION MODE: Different prompts when fixing issues

    Args:
        step_number: Current step (1-3)
        total_steps: Total steps (typically 3)
        plan_file: Path to the plan file being reviewed
        qr_iteration: Loop iteration for QR verification (1=initial, 2+=re-verify)
        fixing_issues: Whether this is a re-run after fixing QR issues
    """
    is_complete = step_number >= total_steps
    next_step = step_number + 1

    # Common rule for all steps
    rule_0_block = [
        "<review_rule_0>",
        "RULE 0 (ABSOLUTE): You MUST spawn sub-agents. Self-review is PROHIBITED.",
        "",
        "This rule applies to ALL review steps. Violations include:",
        "  - Doing the review yourself instead of spawning the agent",
        "  - Deciding the plan is 'thorough enough' to skip review",
        "  - Using a smaller/faster model 'for quick validation'",
        "",
        "Your assessment of plan quality is NOT a valid reason to skip.",
        "The agents exist to catch issues YOU cannot see in your own work.",
        "</review_rule_0>",
        "",
        "<delegation_template_guidance>",
        "Delegation blocks below are SUGGESTED STRUCTURE, not enforced schema.",
        "",
        "The template helps agents understand the task. Adapt fields as needed:",
        "  - <mode>: identifies the review type",
        "  - <plan_source>: path to the plan file",
        "  - <task>: specific work to perform",
        "  - <expected_output>: how to know when done",
        "",
        "The structure reduces interpretation errors without rigid enforcement.",
        "</delegation_template_guidance>",
    ]

    if step_number == 1:
        # Three Pillars: STATE BANNER for QR checkpoint
        state_banner = get_qr_state_banner("PLAN QR", qr_iteration, fixing_issues)
        stop_condition = get_qr_stop_condition("BOTH QR agents (Completeness AND Code) return PASS")

        return {
            "actions": state_banner + rule_0_block + [
                "",
                "<review_step_1_parallel_qr>",
                "STEP 1: Parallel Quality Review (Completeness + Code)",
                "",
                "You MUST spawn BOTH quality-reviewer agents in parallel using two",
                "Task tool calls in a single message. Sequential execution is PROHIBITED.",
                "",
                "Both reviews run BEFORE TW to catch issues early:",
                "  - QR-Completeness: Validates Decision Log, policy defaults, plan structure",
                "  - QR-Code: Validates proposed code against actual codebase",
                "",
                "---",
                "",
                "DELEGATION 1: QR-Completeness",
                "",
                "Use the Task tool with these parameters:",
                "  subagent_type: 'quality-reviewer'",
                "  prompt: The delegation block below",
                "",
                "  <delegation>",
                "    <mode>plan-completeness</mode>",
                f"    <plan_source>{plan_file}</plan_source>",
                "    <task>",
                "      1. Read ## Planning Context section",
                "      2. Write CONTEXT FILTER (decisions, rejected alts, risks)",
                "      3. Check Decision Log completeness for all code elements",
                "      4. Verify policy defaults have user-specified backing",
                "      5. Check architectural assumptions are validated",
                "      6. Verify plan structure (milestones have acceptance criteria)",
                "    </task>",
                "    <expected_output>",
                "      Verdict: PASS | ISSUES",
                "    </expected_output>",
                "  </delegation>",
                "",
                "---",
                "",
                "DELEGATION 2: QR-Code",
                "",
                "Use the Task tool with these parameters:",
                "  subagent_type: 'quality-reviewer'",
                "  prompt: The delegation block below",
                "",
                "  <delegation>",
                "    <mode>plan-code</mode>",
                f"    <plan_source>{plan_file}</plan_source>",
                "    <task>",
                "      1. Read ## Planning Context section",
                "      2. Write CONTEXT FILTER (decisions, rejected alts, risks)",
                "      3. READ the actual codebase files referenced in the plan",
                "      4. Verify diff context lines match current file content",
                "      5. Apply RULE 0 (production reliability) to proposed code",
                "      6. Apply RULE 1 (project conformance) to proposed code",
                "      7. Apply RULE 2 (structural quality) to proposed code",
                "      8. Check for anticipated structural issues",
                "    </task>",
                "    <expected_output>",
                "      Verdict: PASS | ISSUES",
                "    </expected_output>",
                "  </delegation>",
                "",
                "---",
                "",
                "Spawn BOTH delegations in the SAME message using two Task tool calls.",
                "</review_step_1_parallel_qr>",
                "",
            ] + stop_condition + [
                "",
                "<pre_tw_gate>",
                "GATE: Both QR-Completeness AND QR-Code must PASS before TW runs.",
                "",
                "If either returns ISSUES:",
                "  1. Fix the specific issues identified in the plan file",
                "  2. Re-invoke this script with --qr-iteration incremented (command in NEXT section)",
                "  3. Both QR agents run again on the fixed plan",
                "  4. REPEAT until both return PASS",
                "",
                "This is a VALIDATION LOOP. You stay in step 1 until both pass.",
                "The --qr-iteration flag tracks loop iterations for visibility.",
                "</pre_tw_gate>",
            ],
            "next": (
                "After BOTH QR agents complete:\n\n"
                "  Both PASS -> Proceed to step 2\n"
                "  Either ISSUES -> Fix issues, then RE-VERIFY (step 1 again)\n\n"
                f"RESTART COMMAND (if either QR returns ISSUES):\n"
                f'  python3 planner.py --phase review --plan-file "{plan_file}" \\\n'
                f"    --step-number 1 --total-steps 3 \\\n"
                f"    --qr-iteration {qr_iteration + 1} --fixing-issues \\\n"
                f'    --thoughts "Fixed: [list issues fixed]. Re-verifying..."\n\n'
                "  CRITICAL: You MUST re-run QR after fixing issues.\n"
                "  Skipping re-verification is PROHIBITED.\n\n"
                "SUCCESS COMMAND (ONLY after both PASS):\n"
                f'  python3 planner.py --phase review --plan-file "{plan_file}" \\\n'
                f'    --step-number 2 --total-steps 3 \\\n'
                f'    --thoughts "QR-Completeness and QR-Code passed, proceeding to TW"'
            )
        }

    if step_number == 2:
        # Three Pillars: STATE BANNER when re-running TW after QR-Docs feedback
        state_banner = get_qr_state_banner("TW SCRUB", qr_iteration, fixing_issues) if qr_iteration > 1 else []

        return {
            "actions": state_banner + rule_0_block + [
                "",
                "<review_step_2_tw_scrub>",
                "STEP 2: Documentation enrichment by Technical Writer.",
                "",
                "This step runs AFTER both QR agents have passed.",
                "TW sources all comments from Decision Log (verified complete in step 1).",
                "",
                "MANDATORY: Spawn the technical-writer agent.",
                "",
                "Use the Task tool with these parameters:",
                "  subagent_type: 'technical-writer'",
                "  prompt: The delegation block below",
                "",
                "  <delegation>",
                "    <mode>plan-scrub</mode>",
                f"    <plan_source>{plan_file}</plan_source>",
                "    <scope>[OPTIONAL: If re-reviewing after QR-Docs feedback, specify",
                "      which milestones/sections to focus on.]</scope>",
                "    <task>",
                "      1. Read ## Planning Context section FIRST",
                "      2. Prioritize scrub by uncertainty (HIGH/MEDIUM/LOW)",
                "      3. Add WHY comments to code snippets from Decision Log",
                "      4. Enrich plan prose with rationale",
                "      5. Add documentation milestone if missing",
                "      6. FLAG any non-obvious logic lacking rationale",
                "    </task>",
                "  </delegation>",
                "",
                "Wait for the technical-writer agent to complete before proceeding.",
                "</review_step_2_tw_scrub>",
            ],
            "next": (
                "After TW completes, invoke step 3:\n"
                f'  python3 planner.py --phase review --plan-file "{plan_file}" \\\n'
                f'    --step-number 3 --total-steps 3 \\\n'
                f"    --qr-iteration {qr_iteration} \\\n"
                f'    --thoughts "TW scrub complete, [summary of changes]"'
            )
        }

    if step_number == 3:
        # Three Pillars: STATE BANNER for QR-Docs checkpoint
        state_banner = get_qr_state_banner("DOC QR", qr_iteration, fixing_issues)
        stop_condition = get_qr_stop_condition("QR-Docs returns PASS")

        return {
            "actions": state_banner + rule_0_block + [
                "",
                "<review_step_3_qr_docs>",
                "STEP 3: Validate documentation quality.",
                "",
                "This step runs AFTER TW to verify documentation was done correctly.",
                "",
                "MANDATORY: Spawn the quality-reviewer agent.",
                "",
                "Use the Task tool with these parameters:",
                "  subagent_type: 'quality-reviewer'",
                "  prompt: The delegation block below",
                "",
                "  <delegation>",
                "    <mode>plan-docs</mode>",
                f"    <plan_source>{plan_file}</plan_source>",
                "    <scope>[OPTIONAL: If re-reviewing, specify changed sections.]</scope>",
                "    <task>",
                "      1. Check all comments for temporal contamination (five questions)",
                "      2. Verify no hidden baselines in comments",
                "      3. Verify comments explain WHY, not WHAT",
                "      4. Verify coverage of non-obvious code elements",
                "    </task>",
                "    <expected_output>",
                "      Verdict: PASS | ISSUES",
                "    </expected_output>",
                "  </delegation>",
                "",
                "Wait for the quality-reviewer agent to complete before proceeding.",
                "</review_step_3_qr_docs>",
                "",
            ] + stop_condition + [
                "",
                "<post_qr_docs_restart>",
                "RESTART BEHAVIOR for QR-Docs:",
                "",
                "Unlike step 1, QR-Docs failures restart to step 2 (TW) only.",
                "This is because doc issues don't require plan restructuring.",
                "",
                "If QR-Docs returns ISSUES:",
                "  1. Note the specific doc issues",
                "  2. Restart from step 2 with <scope> specifying affected sections",
                "  3. TW fixes the documentation issues",
                "  4. Return to step 3 for re-validation with --qr-iteration incremented",
                "",
                "If QR-Docs returns PASS:",
                "  Review phase complete. Plan ready for /plan-execution.",
                "</post_qr_docs_restart>",
            ],
            "next": (
                "After QR-Docs returns verdict:\n\n"
                "  ISSUES -> Restart from step 2 (TW), then re-verify at step 3\n"
                "  PASS -> Review phase complete, plan ready for execution\n\n"
                "Command to restart TW (if ISSUES):\n"
                f'  python3 planner.py --phase review --plan-file "{plan_file}" \\\n'
                f'    --step-number 2 --total-steps 3 \\\n'
                f"    --qr-iteration {qr_iteration + 1} \\\n"
                f'    --thoughts "QR-Docs feedback: [issues]. Restarting TW."\n\n'
                "THEN after TW completes, RE-VERIFY with:\n"
                f'  python3 planner.py --phase review --plan-file "{plan_file}" \\\n'
                f"    --step-number 3 --total-steps 3 \\\n"
                f"    --qr-iteration {qr_iteration + 1} --fixing-issues \\\n"
                f'    --thoughts "TW fixed doc issues. Re-verifying..."\n\n'
                "  CRITICAL: You MUST re-run QR-Docs after TW fixes issues.\n"
                "  Skipping re-verification is PROHIBITED.\n\n"
                "If PASS: REVIEW PHASE COMPLETE.\n"
                "Plan is approved and ready for implementation via /plan-execution."
            )
        }

    if is_complete:
        return {
            "actions": [
                "<review_complete_verification>",
                "Confirm before proceeding to execution:",
                "  - Step 1: Both QR agents passed (Completeness + Code)?",
                "  - Step 2: TW scrubbed code snippets with WHY comments?",
                "  - Step 2: TW enriched plan prose with rationale?",
                "  - Step 3: QR-Docs verified no temporal contamination?",
                "  - Final verdict is PASS?",
                "</review_complete_verification>",
            ],
            "next": (
                "PLAN APPROVED.\n\n"
                "Ready for implementation via /plan-execution command.\n"
                "Pass the plan file path as argument."
            )
        }

    # Shouldn't reach here with standard 3-step review, but handle gracefully
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

  # Start review (after plan written) - 3 steps: QR (Completeness+Code), TW, QR-Docs
  python3 planner.py --phase review --plan-file plans/auth.md \\
    --step-number 1 --total-steps 3 --thoughts "Starting review..."

  # Re-verify after fixing QR issues (Three Pillars Pattern)
  python3 planner.py --phase review --plan-file plans/auth.md \\
    --step-number 1 --total-steps 3 \\
    --qr-iteration 2 --fixing-issues --thoughts "Fixed issues, re-verifying..."
"""
    )

    parser.add_argument("--phase", type=str, default="planning",
                        choices=["planning", "review"],
                        help="Workflow phase: planning (default) or review")
    parser.add_argument("--step-number", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    parser.add_argument("--thoughts", type=str, required=True)
    parser.add_argument("--plan-file", type=str, default=None,
                        help="Path to plan file (required for review phase)")
    # Three Pillars Pattern flags for QR verification loops
    parser.add_argument("--qr-iteration", type=int, default=1,
                        help="QR loop iteration (1=initial, 2+=re-verification)")
    parser.add_argument("--fixing-issues", action="store_true",
                        help="Flag indicating this is re-verification after fixing QR issues")

    args = parser.parse_args()

    if args.step_number < 1 or args.total_steps < 1:
        print("Error: step-number and total-steps must be >= 1", file=sys.stderr)
        sys.exit(1)

    # Get guidance based on phase
    if args.phase == "planning":
        guidance = get_planning_step_guidance(args.step_number, args.total_steps)
        phase_label = "PLANNING"
    else:
        # Review phase requires plan file
        if not args.plan_file:
            print("Error: --plan-file is required for review phase", file=sys.stderr)
            sys.exit(1)
        guidance = get_review_step_guidance(
            args.step_number, args.total_steps,
            plan_file=args.plan_file,
            qr_iteration=args.qr_iteration,
            fixing_issues=args.fixing_issues
        )
        phase_label = "REVIEW"

    is_complete = args.step_number >= args.total_steps

    # Build header with QR iteration info for review phase
    print("=" * 80)
    if args.phase == "review" and (args.qr_iteration > 1 or args.fixing_issues):
        print(f"PLANNER - {phase_label} PHASE - Step {args.step_number} of {args.total_steps} [QR iteration {args.qr_iteration}]")
    else:
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
