# skills/

Script-based agent workflows with shared orchestration framework.

## Files

| File        | What                                                      | When to read                                    |
| ----------- | --------------------------------------------------------- | ----------------------------------------------- |
| `README.md` | File organization, prompt patterns, naming, anti-patterns | Before editing any Python file under `scripts/` |

## Subdirectories

| Directory             | What                                      | When to read                             |
| --------------------- | ----------------------------------------- | ---------------------------------------- |
| `scripts/`            | Python package root for all skill code    | Executing skills, debugging behavior     |
| `planner/`            | Planning and execution workflows          | Creating implementation plans            |
| `refactor/`           | Refactoring analysis across dimensions    | Technical debt review, code quality      |
| `problem-analysis/`   | Structured problem decomposition          | Understanding complex issues             |
| `decision-critic/`    | Decision stress-testing and critique      | Validating architectural choices         |
| `deepthink/`          | Structured reasoning for open questions   | Analytical questions without frameworks  |
| `codebase-analysis/`  | Systematic codebase exploration           | Repository architecture review           |
| `prompt-engineer/`    | Prompt optimization and engineering       | Improving agent prompts                  |
| `incoherence/`        | Consistency detection                     | Finding spec/implementation mismatches   |
| `doc-sync/`           | Documentation synchronization             | Syncing a repository's CLAUDE.md/README.md docs |
| `arxiv-to-md/`        | arXiv paper to markdown conversion        | Converting papers for LLM consumption    |
| `cc-history/`         | Claude Code conversation history analysis | Querying past conversations, token usage |

## Script Invocation

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.<skill_name>.<module> --step 1" />

Example:

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.problem_analysis.analyze --step 1" />

Invocation forms and the working-directory invariant: `scripts/skills/lib/workflow/prompts/README.md` (`## Invocation Forms`).
