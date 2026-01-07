# planner/

Planning and execution skill with quality review gates.

## Files

| File        | What                               | When to read                 |
| ----------- | ---------------------------------- | ---------------------------- |
| `SKILL.md`  | Skill activation and invocation    | Using the planner skill      |
| `README.md` | Architecture, workflows, rationale | Understanding planner design |

## Subdirectories

| Directory    | What                   | When to read                        |
| ------------ | ---------------------- | ----------------------------------- |
| `scripts/`   | Workflow orchestration | Debugging planner/executor behavior |
| `resources/` | Plan format, diff spec | Editing plan structure, diff format |

## Universal Conventions

Scripts reference these conventions from `.claude/conventions/`:

| Convention          | When to read                                 |
| ------------------- | -------------------------------------------- |
| `documentation.md`  | Understanding CLAUDE.md/README.md format     |
| `structural.md`     | Updating QR RULE 2 or planner decision audit |
| `temporal.md`       | Updating TW/QR temporal contamination logic  |
| `severity.md`       | Understanding QR severity levels             |
| `intent-markers.md` | Understanding :PERF:/:UNSAFE: markers        |
