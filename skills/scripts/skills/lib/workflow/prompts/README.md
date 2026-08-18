# prompts/

## Overview

`format_step()` is the sole assembler of step output. Every skill's `format_output()` funnels through it, so the cd-prefix wrapper it emits is a repository-wide invariant: skill authors can write `next_cmd = "uv run python -m skills.X"` without tracking cwd or project path themselves, because the wrapper prepends `cd '<SKILLS_DIR>' && …` to both the simple and the branching-invoke forms.

## The cd-Prefix Invariant

`format_step()` emits `NEXT STEP` blocks shaped like:

```
NEXT STEP:
    Working directory: <SKILLS_DIR>
    Command: cd '<SKILLS_DIR>' && <next_cmd>

Execute this command now.
```

Two consequences follow:

1. **Any `next_cmd` string built outside `format_step()` must replicate the cd prefix itself.** The orchestrator (`step.py`) is the only place where the invariant is guaranteed. A new dispatch path or a custom formatter that skips `format_step()` inherits responsibility for cwd.
2. **Do not double-wrap.** Adding `cd …` or `uv run --project <path>` inside the Python string produces commands like `cd X && cd X && uv run --project Y …` that either no-op or override the wrapper unexpectedly. The bare `uv run python -m skills.X` form is deliberate.

## SKILLS_DIR Resolution

`SKILLS_DIR` is computed at import time as `Path(__file__).resolve().parent.parent.parent.parent.parent`. The five-level traversal walks `prompts/ -> workflow/ -> lib/ -> skills/ -> scripts/` to land at the pyproject root. The path is `shlex.quote`d before emission so spaces or shell metacharacters in user home paths survive the `cd`.

This traversal count is brittle: moving `step.py` (or any intermediate package) up or down one level silently changes the resolved dir, and skills will `cd` into the wrong place at runtime. `subagent.py` uses the same count for the same reason — both files must move together, and the count must be re-verified after any restructure.

## Three Invocation Forms

The repository uses three distinct forms because three different callers evaluate the command string:

| Form                                                                                              | Used in                                                     | Why                                                                                                                                 |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.X" />`                 | `SKILL.md` entry points, EXCEPT any that need the caller's cwd | Claude Code resolves `working-dir` against the active `.claude/` dir — user-global (`~/.claude/`) or project-local (`<repo>/.claude/`). `uv run` auto-discovers the pyproject from that cwd. One form covers both install layouts. The cost of that resolution is the cwd: the script starts in the skill tree, so a script that must know which PROJECT invoked it cannot use this form (see below). |
| `uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.X`       | Raw bash blocks in `INTENT.md`, SKIP-invoked `## Run` blocks that are NOT project-anchored | Plain bash doesn't get `working-dir` resolution. The env-var arm selects a project-local install where `CLAUDE_PROJECT_DIR` is set — which Claude Code does not do for a Bash-tool subprocess, so only a user's own export reaches it; see form 2b. |
| `uv run --project "$(d="${CLAUDE_PROJECT_DIR:-$PWD}"; [ -d "$d/.claude/skills/scripts" ] && echo "$d/.claude/skills/scripts" \|\| echo "$HOME/.claude/skills/scripts")" python -m skills.X` (**2b**) | `skills/planner/SKILL.md` — entry points that must locate the caller's project | Same as form 2, but the install layout is probed from the working directory rather than from an env var Claude Code does not set for these subprocesses. Covers both layouts with no per-project configuration. |
| `uv run python -m skills.X`                                                                       | Python `next_cmd` strings fed to `format_step()`            | The `cd '<SKILLS_DIR>' && …` wrapper handles cwd; the command just needs uv's env activation. Adding `--project` here would hardcode the install path the wrapper already resolved. |

When constructing commands for a new caller context, pick the form whose caller evaluates the string — if the caller gets Claude Code `<invoke>` resolution, use form 1; if it runs in plain bash with no wrapper, form 2 — or 2b when the script must locate the caller's project; if it passes through `format_step()`, form 3.

**Exception — entry points that must locate the user's project.** `skills/planner/SKILL.md`
invokes planner and executor step 1 with form 2b, not form 1. Step 1 mints the run's state
directory under `<project>/.agent-state/`, and the only in-process signals naming the
project are `$CLAUDE_PROJECT_DIR` and the cwd. Form 1's `working-dir` `cd`s into the skill tree before
Python starts, which discards the cwd -- the one of the two Claude Code actually supplies
for these subprocesses -- and, with `CLAUDE_PROJECT_DIR` unset, anchors the state dir on
whichever repo holds the scripts. A `cd` cannot unset an exported variable, so a user who
exports it is unaffected. Form 2b keeps the cwd.

The trade-off is concrete and worth stating plainly: Claude Code populates
`CLAUDE_PROJECT_DIR` for **hook** subprocesses but not for Bash-tool ones, so unless the
user has exported it themselves `${CLAUDE_PROJECT_DIR:-$HOME}` takes the `$HOME` arm and
resolves to the user-global install — a project-local `<repo>/.claude/` install is then
never reached, and where both exist the global scripts run silently against the project's
cwd.

`skills/planner/SKILL.md` therefore does not use the bare env-var form. It falls back to
`$PWD` rather than `$HOME` and probes for `<dir>/.claude/skills/scripts`, so the layout is
selected from the working directory the entry point already depends on, with no per-project
configuration. Prefer that shape for any new launcher that must work under both layouts.

Where the bare form is still used, setting `CLAUDE_PROJECT_DIR` is what selects a
project-local install — but only when the skills really are at
`<project>/.claude/skills/scripts`. Pointed at a path with no install, `uv` emits
`warning: Project directory … does not exist. This will become an error in a future
release` and proceeds, and the run then dies on `ModuleNotFoundError: No module named
'skills'` — so the failure surfaces from Python, not from `uv`, and that will change when
`uv` promotes the warning. Do **not** set it in user-scope `~/.claude/settings.json`: that pins one
absolute path for every project, which breaks this launcher wherever that path has no
install, and — because `resolve_project_root` reads the same variable to choose the
project — sends state, the `.gitignore` append, and approved plans into that one repo from
everywhere else. Form 1 covers both layouts transparently; these two entry points give that up in
exchange for an anchor that names the user's project rather than the scripts' own repo.

Steps 2+ are unaffected — they receive `--state-dir` and read the project root recorded
there.

Rendered sub-agent dispatch XML (`render_subagent_dispatch`, `sub_agent_invoke`,
`refactor._invoke_tag`) does **not** use Form 1: it embeds the absolute
`cd '<SKILLS_DIR>' && …` form inside the `cmd` attribute, because the spawned agent
copies the command into Bash, where `working-dir` resolution does not apply.
