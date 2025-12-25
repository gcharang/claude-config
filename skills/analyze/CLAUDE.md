# skills/analyze/

## Overview

Systematic codebase analysis skill with six-phase workflow: exploration, focus selection, investigation planning, deep analysis, verification, and synthesis.

## Index

| File/Directory       | Contents                                    | Read When                   |
| -------------------- | ------------------------------------------- | --------------------------- |
| `SKILL.md`           | Workflow, phases, invocation, arguments     | Using the analyze skill     |
| `scripts/analyze.py` | Step-by-step analysis with prompt injection | Debugging analyzer behavior |

## Workflow Summary

```
Step 1: EXPLORATION         - Process Explore sub-agent results
Step 2: FOCUS SELECTION     - Classify areas, assign priorities (P1/P2/P3)
Step 3: INVESTIGATION PLAN  - Commit to specific files and questions
Step 4+: DEEP ANALYSIS      - Progressive investigation with evidence
Step N-1: VERIFICATION      - Validate completeness before synthesis
Step N: SYNTHESIS           - Consolidate verified findings
```

## Key Patterns

- Uses `--thoughts` for accumulated state (same as decision-critic, planner)
- Dynamic `--total-steps` (minimum 6, adjust as understanding grows)
- Leverages Explore sub-agent (Haiku) for fast initial discovery
- Investigation planning creates accountability contract
- Verification gate prevents premature synthesis
- Evidence format: `[SEVERITY] description (file:line) > quoted code`

## State Requirements

From step 2 onward, --thoughts must include:

1. FOCUS AREAS with priorities
2. INVESTIGATION PLAN with files and questions
3. FILES EXAMINED with observations
4. ISSUES BY SEVERITY
5. PATTERNS identified
6. HYPOTHESES and evidence
7. REMAINING investigation items
