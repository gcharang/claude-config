---
name: problem-analysis
description: Invoke IMMEDIATELY via python script when user requests problem analysis or root cause investigation. Do NOT explore first - the script orchestrates the investigation.
---

# Problem Analysis

Root cause identification skill. Identifies WHY a problem occurs, NOT how to fix
it. Solution discovery is a separate downstream concern.

## Pipeline Context

```
codebase-analysis (gathers relevant context)
    |
    v
problem-analysis (THIS SKILL - identifies root cause)
    |
    v
solution-discovery (proposes remediations)
```

Can also be invoked standalone when problem is narrowly scoped.

## Invocation

```bash
python3 scripts/analyze.py --step 1 --total-steps 5
```

| Argument        | Required | Description               |
| --------------- | -------- | ------------------------- |
| `--step`        | Yes      | Current phase (1-5)       |
| `--total-steps` | Yes      | Must be >= 5              |
| `--confidence`  | Phase 3  | exploring/low/medium/high |
| `--iteration`   | Phase 3  | Current iteration (1-5)   |

## Phases

| Phase | Name        | Purpose                                       |
| ----- | ----------- | --------------------------------------------- |
| 1     | Gate        | Validate input, establish single problem      |
| 2     | Hypothesize | Generate 2-4 testable candidate explanations  |
| 3     | Investigate | Iterative evidence gathering (up to 5 rounds) |
| 4     | Formulate   | Synthesize findings into validated root cause |
| 5     | Output      | Structured report for downstream consumption  |

## Operating Constraints

This skill runs inside Claude Code. It can:

- Read files and examine code
- Search codebase with Grep/Glob
- Ask user clarifying questions via AskUserQuestion

It cannot:

- Execute tests or observe runtime behavior
- Access production logs directly
- Verify fixes (that confirms root cause post-implementation)

Evidence is primarily static analysis of code, configuration, and documentation.

## Key Principle

Root causes must be framed as CONDITIONS THAT EXIST, not as absences:

| Wrong (Absence)            | Correct (Condition)                             |
| -------------------------- | ----------------------------------------------- |
| "We don't have validation" | "User input reaches SQL query unsanitized"      |
| "Missing retry logic"      | "Failed requests terminate without retry"       |
| "No rate limiting"         | "API accepts unbounded requests per client"     |
| "Lack of monitoring"       | "Failures propagate silently until user impact" |

Do NOT analyze or explore first. Run the script and follow its output.
