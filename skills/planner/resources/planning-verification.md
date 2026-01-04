# Planning Verification Checklist

Complete in priority order before writing the plan.

## PHASE 1: CRITICAL (BLOCKING)

### VERIFY 1: Decision Log Completeness

TW sources ALL code comments from Decision Log. Missing entries mean
undocumented code.

- Every architectural choice has multi-step reasoning? INSUFFICIENT: 'Polling |
  Webhooks are unreliable' SUFFICIENT: 'Polling | 30% webhook failure -> need
  fallback anyway -> simpler as primary'
- Every micro-decision documented? (timeouts, thresholds, concurrency choices,
  data structure selections)
- Rejected alternatives listed with concrete reasons?
- Known risks have mitigations with file:line anchors for any behavioral claims?

### VERIFY 2: Code Changes Presence

STOP CHECK: For EACH implementation milestone:

- Does it contain diff blocks or code snippets?
- If NO and milestone creates/modifies source files: STOP. Add code changes
  before proceeding.

Implementation milestones WITHOUT code cannot be approved. Only documentation
milestones (100% .md/.rst files) may skip code.

### VERIFY 3: Invisible Knowledge Capture (BLOCKING)

ALL architecture decisions, tradeoffs, invariants, and rationale that a future
reader could NOT infer from reading code alone MUST be documented in the plan's
Invisible Knowledge section.

MISSING INVISIBLE KNOWLEDGE IS A BLOCKING ISSUE.

Check for:

- Why was this approach chosen over alternatives?
- What tradeoffs were made and why?
- What invariants must be maintained?
- What assumptions underlie this design?
- What would a future maintainer need to know?

If the plan makes ANY decision that requires explanation beyond what code
comments can convey, it MUST be in Invisible Knowledge.

## PHASE 2: FORMAT

### VERIFY 4: Diff Format Compliance

Re-read resources/diff-format.md before writing any code changes.

For EACH diff block:

- File path exact (src/auth/handler.py not 'auth files')?
- Context lines: 2-3 lines copied VERBATIM from actual file?
- WHY comments explain rationale, not WHAT code does?
- No location directives in comments?
- No hidden baselines ('[adjective] compared to what?')?

FORBIDDEN: '...', '[existing code]', summaries, placeholders. If you haven't
read the target file, read it now.

### VERIFY 5: Milestone Specification

For EACH milestone:

- File paths exact?
- Requirements are specific behaviors, not 'handle X'?
- Acceptance criteria are testable pass/fail assertions?
- Tests section with type, backing, scenarios? (or explicit skip reason)
- Uncertainty flags added where applicable?

## PHASE 3: DOCUMENTATION

### VERIFY 6: Documentation Milestone

- Documentation milestone exists?
- CLAUDE.md format verification:
  - Tabular index format with WHAT/WHEN columns?
  - ~200 token budget (no prose sections)?
  - NO 'Key Invariants', 'Dependencies', 'Constraints' sections?
  - Overview is ONE sentence only?
- README.md included if Invisible Knowledge has content?
- Invisible Knowledge maps to README.md, not CLAUDE.md?
- Stub directories (only .gitkeep) excluded from CLAUDE.md requirement?

### VERIFY 7: Comment Hygiene

Comments will be transcribed VERBATIM. Write in TIMELESS PRESENT.

CONTAMINATED: '// Added mutex to fix race condition' CLEAN: '// Mutex serializes
cache access from concurrent requests'

CONTAMINATED: '// After the retry loop' CLEAN: (delete -- diff context encodes
location)

### VERIFY 8: Assumption Audit Complete

- Step 2 assumption audit completed (all categories)?
- Step 3 decision classification table written?
- Step 4 file classification table written?
- No 'assumption' rows remain unresolved?
- User responses recorded with 'user-specified' backing?

If any step was skipped: STOP. Go back and complete it.
