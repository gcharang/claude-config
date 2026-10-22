---
name: incoherence
description: Detect and resolve incoherence across documentation, code and specs. Use when the user asks to find or fix places where docs, specs, comments or configs contradict the implementation or each other.
---

# Incoherence Detector

Run the script before exploring and follow its output; it runs detection,
resolution and application.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.incoherence.incoherence --step-number 1" />

| Argument        | Required | Description                               |
| --------------- | -------- | ----------------------------------------- |
| `--step-number` | Yes      | Current step (starts at 1)                |
| `--thoughts`    | No       | Set only by commands the script prints    |

## Workflow Phases

1. **Detection**: Survey codebase, explore dimensions, verify
   candidates
2. **Resolution**: Present issues via AskUserQuestion, collect
   user decisions
3. **Application**: Apply resolutions, present final report

Resolution is interactive - user answers structured questions inline. No manual
file editing required.
