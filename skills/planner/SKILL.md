---
name: planner
description: Interactive planning and execution for complex tasks. IMMEDIATELY invoke when user asks to use planner.
---

## Activation

When this skill activates, IMMEDIATELY invoke the corresponding script. The
script IS the workflow.

| Mode      | Intent                             | Entry point                                 |
| --------- | ---------------------------------- | ------------------------------------------- |
| planning  | "plan", "design", "architect"      | `skills.planner.orchestrator.planner` step 1 |
| execution | "execute", "implement", "run plan" | `skills.planner.orchestrator.executor` step 1 |

Each command is self-contained -- the `--project` expression prefers a project-local
install and falls back to the user-global one. Run one whole line; shell state does not
persist between invocations.

**planning**

```bash
uv run --project "$(d="${CLAUDE_PROJECT_DIR:-$PWD}"; [ -d "$d/.claude/skills/scripts" ] && echo "$d/.claude/skills/scripts" || echo "$HOME/.claude/skills/scripts")" python -m skills.planner.orchestrator.planner --step 1
```

**execution**

```bash
uv run --project "$(d="${CLAUDE_PROJECT_DIR:-$PWD}"; [ -d "$d/.claude/skills/scripts" ] && echo "$d/.claude/skills/scripts" || echo "$HOME/.claude/skills/scripts")" python -m skills.planner.orchestrator.executor --step 1
```

**Run these with the shell sitting inside the project.** The Bash working directory
persists between calls, so it may still be in a sibling repo or a vendored checkout from
earlier work -- check it, and `cd` into the project first if it is not already there. Do
not `cd` into the skills directory: `--project` already locates the scripts, and step 1
needs the project's own working directory left intact.

The `--project` expression picks the install layout from that same working directory: a
project-local `<project>/.claude/skills/scripts` wins when it exists, the user-global
`~/.claude/skills/scripts` otherwise. A bare `${CLAUDE_PROJECT_DIR:-$HOME}` cannot do
this -- Claude Code does not populate `CLAUDE_PROJECT_DIR` for Bash-tool subprocesses, so
unless the user exports it themselves it takes the `$HOME` arm, which fails outright on a
project-local-only install and silently runs the global scripts when both exist.

Step 1 is the only step that can see which project the run belongs to. It reads
`$CLAUDE_PROJECT_DIR`, then falls back to the working directory, and records the answer in
the state directory; every later step arrives through a `cd <SKILLS_DIR> && ...` wrapper
and reads it back rather than looking again. That is why these two entry points use
`--project` instead of the `<invoke working-dir=...>` form other skills use -- `working-dir`
resolves the install layout by `cd`-ing into it, discarding the one signal step 1 has. See
`skills/scripts/skills/lib/workflow/prompts/README.md` ("Three Invocation Forms") and
`skills/planner/INTENT.md` ("State directory location").
