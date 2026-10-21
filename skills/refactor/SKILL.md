---
name: refactor
description: Invoke IMMEDIATELY via script when user requests refactoring analysis, technical debt review, or code quality improvement. Do NOT explore first - the script orchestrates exploration.
---

# Refactor

Run the script before exploring and follow its output; it orchestrates the exploration.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.refactor.refactor --step 1 --n 10" />

| Argument | Required | Description                                   |
| -------- | -------- | --------------------------------------------- |
| `--step` | Yes      | Current step (starts at 1)                    |
| `--n`    | No       | Number of categories to explore (default: 10) |

## Determining N (category count)

Default: N = 10

Adjust based on user request scope:

- SMALL (single file, specific concern, "quick look"): N = 5
- MEDIUM (directory, module, standard analysis): N = 10
- LARGE (entire codebase, "thorough", "comprehensive"): N = 25

Step 1 picks a mode from the request. In design, code, or both mode the script samples N targets at random from the categories in conventions/code-quality/; in custom mode it selects categories from the problem statement and ignores N.
