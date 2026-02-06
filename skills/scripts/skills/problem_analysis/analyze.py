#!/usr/bin/env python3
"""
Problem Analysis Skill - Root cause identification workflow.

Five-step workflow:
  1. Gate        - Validate input, establish single testable problem
  2. Hypothesize - Generate testable candidate explanations
  3. Investigate - Iterative evidence gathering (up to 5 iterations)
  4. Formulate   - Synthesize findings into validated root cause
  5. Output      - Produce structured report for downstream consumption

This skill identifies root causes, NOT solutions. It ends when the root cause
is identified with supporting evidence. Solution discovery is downstream.
"""

import argparse
import sys

from skills.lib.workflow.prompts import format_step


# ============================================================================
# CONFIGURATION
# ============================================================================

MODULE_PATH = "skills.problem_analysis.analyze"
MAX_ITERATIONS = 5
TOTAL_STEPS = 5


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: GATE -----------------------------------------------------------

GATE_INSTRUCTIONS = """\
CHECK FOR MULTIPLE PROBLEMS:
  Scan input for signs of multiple distinct issues:
  - Multiple symptoms described ('X AND Y')
  - Problems in unrelated components
  - Symptoms with independent causes

  If multiple problems -> STOP. Use AskUserQuestion to ask user
  to isolate ONE problem. Do not proceed until single problem.

CHECK FOR SUFFICIENT INFORMATION:
  A problem statement must include:
  - What component or behavior is affected
  - What the expected behavior is
  - What the actual observed behavior is

  If missing or vague -> Use AskUserQuestion to clarify.

RESTATE THE PROBLEM:
  Reframe in observable terms:
  'When [conditions], [component] exhibits [observed behavior]
   instead of [expected behavior]'

SEPARATE KNOWN FROM ASSUMED:
  KNOWN: From user report or visible context
  ASSUMED: Things investigation must verify

OUTPUT FORMAT:
```
VALIDATION: [PASS / BLOCKED: reason]

REFINED PROBLEM STATEMENT:
When [conditions], [component] exhibits [observed behavior]
instead of [expected behavior]

KNOWN FACTS:
- [fact 1]
- [fact 2]

ASSUMPTIONS TO VERIFY:
- [assumption 1]
- [assumption 2]
```"""

# --- STEP 2: HYPOTHESIZE ----------------------------------------------------

HYPOTHESIZE_INSTRUCTIONS = """\
GENERATE 2-4 DISTINCT HYPOTHESES:
  Each hypothesis must:
  - Differ on mechanism or location (not just phrasing)
  - Be framed as a CONDITION THAT EXISTS, not an absence
  - Predict something examinable (where to look, what to find)

FRAMING RULES (critical):
  WRONG: 'The validation is missing'
  RIGHT: 'User input reaches the database query without sanitization'

  WRONG: 'There's no error handling'
  RIGHT: 'Exceptions in the payment callback propagate uncaught,
          terminating the request without rollback'

RANK BY PLAUSIBILITY:
  Order hypotheses by likelihood given available context.
  This guides investigation order but doesn't preclude alternatives.

OUTPUT FORMAT:
```
HYPOTHESES:

H1 (highest priority): [name]
    Mechanism: [how this would cause the symptom]
    Testable by: [what to examine, what you'd expect to find]

H2: [name]
    Mechanism: [how this would cause the symptom]
    Testable by: [what to examine, what you'd expect to find]

[H3, H4 if generated]

INVESTIGATION PLAN:
Will examine H1 first because [reason], then H2 if H1 doesn't hold.
```"""

# --- STEP 3: INVESTIGATE ----------------------------------------------------

INVESTIGATE_INSTRUCTIONS = """\
SELECT what to examine:
  - Highest-priority OPEN hypothesis, OR
  - Deepen a SUPPORTED hypothesis (ask 'why does this exist?'), OR
  - Examine an unexplored aspect of the problem

EXAMINE specific code, configuration, or documentation.
  Note exact files and line numbers. This creates an audit trail.

ASSESS findings:
  Does evidence SUPPORT, CONTRADICT, or NEITHER?
  Be specific: 'Line 47 of auth.py contains X which would cause Y'
  Not: 'This looks problematic'

UPDATE hypothesis status:
  - SUPPORTED: Evidence confirms this hypothesis
  - CONTRADICTED: Evidence rules this out
  - OPEN: Not yet examined or inconclusive

ANSWER READINESS QUESTIONS:

Q1 EVIDENCE: Can you cite specific code/config/docs supporting root cause?
   [YES / PARTIAL / NO]

Q2 ALTERNATIVES: Did you examine evidence for at least one alternative?
   [YES / PARTIAL / NO]

Q3 EXPLANATION: Does root cause fully explain the symptom?
   [YES / PARTIAL / NO]

Q4 FRAMING: Is root cause a positive condition (not absence)?
   [YES / NO]

COMPUTE CONFIDENCE:
  - 4 points = HIGH (ready to proceed)
  - 3-3.5 = MEDIUM
  - 2-2.5 = LOW
  - <2 = INSUFFICIENT (keep investigating)

OUTPUT FORMAT:
```
ITERATION FINDINGS:

Examined: [which hypothesis or aspect]
Evidence sought: [what you looked for]
Evidence found: [what you found, with file:line references]
Assessment: [SUPPORTS / CONTRADICTS / INCONCLUSIVE] because [reason]

HYPOTHESIS STATUS:
- H1: [SUPPORTED / CONTRADICTED / OPEN] - [brief reason]
- H2: [SUPPORTED / CONTRADICTED / OPEN] - [brief reason]

READINESS CHECK:
- Q1 Evidence: [YES/PARTIAL/NO]
- Q2 Alternatives: [YES/PARTIAL/NO]
- Q3 Explanation: [YES/PARTIAL/NO]
- Q4 Framing: [YES/NO]

CONFIDENCE: [exploring/low/medium/high/certain]
```"""

# --- STEP 4: FORMULATE ------------------------------------------------------

FORMULATE_INSTRUCTIONS = """\
STATE THE ROOT CAUSE:
  Template: 'The system exhibits [symptom] because [condition exists]'

  The condition must be:
  - Specific enough to locate (points to code/config)
  - General enough to allow multiple remediation approaches

TRACE THE CAUSAL CHAIN:
  [root cause] -> [intermediate] -> [intermediate] -> [symptom]
  Each link should follow logically. Note any gaps as uncertainties.

VALIDATE FRAMING (critical):

  CHECK 1 - Positive framing:
  Does root cause contain 'lack of', 'missing', 'no X', 'doesn't have'?
  If YES -> REFRAME before proceeding.

  WRONG: 'The system lacks input validation'
  RIGHT: 'User input flows directly to SQL query without sanitization'

  CHECK 2 - Solution independence:
  Does root cause implicitly prescribe exactly one solution?
  If YES -> REFRAME to be more general.

  WRONG: 'The retry count is set to 0' (prescribes: set it higher)
  RIGHT: 'Failed API calls terminate immediately without retry,
          causing transient failures to surface as errors'

DOCUMENT UNCERTAINTIES:
  What wasn't verified? What would require runtime info to confirm?

OUTPUT FORMAT:
```
ROOT CAUSE:
[validated statement - must pass both framing checks]

CAUSAL CHAIN:
[root cause]
  -> [intermediate 1]
  -> [intermediate 2]
  -> [observed symptom]

FRAMING VALIDATION:
- Positive framing (no absences): [PASS/FAIL - if fail, show reframed]
- Solution independence: [PASS/FAIL - if fail, show reframed]

REMAINING UNCERTAINTIES:
- [what wasn't verified]
- [what assumptions remain]
```"""

# --- STEP 5: OUTPUT ----------------------------------------------------------

OUTPUT_INSTRUCTIONS = """\
Compile final analysis report using all findings from previous steps.

OUTPUT FORMAT:
```
================================================================================
                         PROBLEM ANALYSIS REPORT
================================================================================

ORIGINAL PROBLEM:
[verbatim from user]

REFINED PROBLEM:
[observable-framed version from Step 1]

--------------------------------------------------------------------------------

ROOT CAUSE:
[validated statement from Step 4]

CAUSAL CHAIN:
[root cause]
  -> [intermediate cause 1]
  -> [intermediate cause 2]
  -> [observed symptom]

--------------------------------------------------------------------------------

SUPPORTING EVIDENCE:
- [file:line] -- [what it shows]
- [file:line] -- [what it shows]

--------------------------------------------------------------------------------

CONFIDENCE: [HIGH / MEDIUM / LOW / INSUFFICIENT]

  Evidence (specific citations exist):      [YES / PARTIAL / NO]
  Alternatives (others considered):         [YES / PARTIAL / NO]
  Explanation (fully accounts for symptom): [YES / PARTIAL / NO]
  Framing (positive, solution-independent): [YES / NO]

--------------------------------------------------------------------------------

REMAINING UNCERTAINTIES:
- [what wasn't verified]
- [what assumptions remain]

--------------------------------------------------------------------------------

INVESTIGATION LOG:
[Include key findings from each Step 3 iteration]

================================================================================
```

This completes the problem analysis. The root cause and supporting
evidence can now be used as input for solution discovery."""


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def _format_step_3(confidence: str, iteration: int) -> tuple[str, str]:
    """Dynamic formatter for step 3 (Investigate) -- handles iteration/exit logic."""
    if confidence in ("high", "certain"):
        return (
            "Investigate Complete",
            "Investigation reached HIGH confidence. Proceeding to root cause formulation.\n\n"
            "Review accumulated findings from iterations above, then proceed.",
        )
    if iteration >= MAX_ITERATIONS:
        return (
            "Investigate Complete",
            f"Investigation reached iteration cap ({MAX_ITERATIONS}). "
            f"Proceeding with current findings. Final confidence: {confidence}\n\n"
            "Review accumulated findings from iterations above, then proceed.",
        )
    return (f"Investigate (Iteration {iteration} of {MAX_ITERATIONS})", INVESTIGATE_INSTRUCTIONS)


def build_next_command(step: int, confidence: str, iteration: int) -> str | None:
    """Build invoke command for next step."""
    base = f'python3 -m {MODULE_PATH}'
    if step == 1:
        return f'{base} --step 2'
    if step == 2:
        return f'{base} --step 3 --confidence exploring --iteration 1'
    if step == 3:
        if confidence in ("high", "certain") or iteration >= MAX_ITERATIONS:
            return f'{base} --step 4'
        return f'{base} --step 3 --confidence {{exploring|low|medium|high|certain}} --iteration {iteration + 1}'
    if step == 4:
        return f'{base} --step 5'
    return None


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

STATIC_STEPS = {
    1: ("Gate", GATE_INSTRUCTIONS),
    2: ("Hypothesize", HYPOTHESIZE_INSTRUCTIONS),
    4: ("Formulate", FORMULATE_INSTRUCTIONS),
    5: ("Output", OUTPUT_INSTRUCTIONS),
}

DYNAMIC_STEPS = {
    3: _format_step_3,
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_output(step: int, confidence: str, iteration: int) -> str:
    """Format output for the given step."""
    if step in STATIC_STEPS:
        title, instructions = STATIC_STEPS[step]
    elif step in DYNAMIC_STEPS:
        title, instructions = DYNAMIC_STEPS[step](confidence, iteration)
    else:
        return f"ERROR: Invalid step {step}"

    next_cmd = build_next_command(step, confidence, iteration)
    return format_step(instructions, next_cmd or "", title=f"PROBLEM ANALYSIS - {title}")


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Problem Analysis - Root cause identification workflow",
        epilog="Steps: gate (1) -> hypothesize (2) -> investigate (3) -> formulate (4) -> output (5)",
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument(
        "--confidence",
        type=str,
        choices=["exploring", "low", "medium", "high", "certain"],
        default="exploring",
        help="Confidence level from previous iteration (Step 3 only)",
    )
    parser.add_argument(
        "--iteration",
        type=int,
        default=1,
        help="Current iteration within Step 3 (1-5)",
    )
    args = parser.parse_args()

    if args.step < 1 or args.step > TOTAL_STEPS:
        sys.exit(f"ERROR: --step must be 1-{TOTAL_STEPS}")

    print(format_output(args.step, args.confidence, args.iteration))


if __name__ == "__main__":
    main()
