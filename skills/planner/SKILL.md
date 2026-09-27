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

Each command is self-contained: run one whole line, since shell state does not persist between invocations. `<scripts>` is a literal absolute path you write in: `<project>/.claude/skills/scripts` when that directory exists, the user-global `~/.claude/skills/scripts` otherwise.

**planning**

```bash
uv run --project <scripts> python -m skills.planner.orchestrator.planner --step 1
```

**execution**

```bash
uv run --project <scripts> python -m skills.planner.orchestrator.executor --step 1
```

**Run these with the shell sitting inside the project.** The Bash working directory
persists between calls, so it may still be in a sibling repo or a vendored checkout from
earlier work -- check it, and `cd` into the project first if it is not already there. Do
not `cd` into the skills directory: `--project` already locates the scripts, and step 1
needs the project's own working directory left intact.

`<scripts>` picks the install layout from that same project, so a project-local install wins when it exists. Write the path out rather than computing it in the command: Claude Code asks for approval outside bypass mode before it runs a command whose arguments carry a `$( … )` substitution. A bare `${CLAUDE_PROJECT_DIR:-$HOME}` cannot pick the layout either -- Claude Code does not populate `CLAUDE_PROJECT_DIR` for Bash-tool subprocesses, so unless the user exports it themselves it takes the `$HOME` arm, which fails outright on a project-local-only install and silently runs the global scripts when both exist.

Step 1 is the only step that can see which project the run belongs to. It reads
`$CLAUDE_PROJECT_DIR`, then falls back to the working directory, and records the answer in
the state directory; every later step runs under `uv run --directory <SKILLS_DIR> ...`
and reads it back rather than looking again. That is why these entry points use
`--project` instead of the `<invoke working-dir=...>` form other skills use: `working-dir`
resolves the install layout by `cd`-ing into it, discarding the working directory -- the
one signal Claude Code supplies for these subprocesses. See
`skills/scripts/skills/lib/workflow/prompts/README.md` ("Invocation Forms") and
`skills/planner/INTENT.md` ("State directory location").
