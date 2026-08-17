# Deferred

Intentionally deferred work — not scheduled. Each entry is self-contained so a
fresh session can act on it from the repo alone.

## Make `<file working-dir=".claude" uri="…">` references executor-proof

**Status:** deferred · **Surfaced:** 2026-07-06 (during a `/doc-sync` run in a foreign repo)

**Problem.** At runtime the skill/agent executor (the LLM) misresolves the
`<file working-dir=".claude" uri="…">` convention. `working-dir=".claude"` is
ambiguous — it can mean the user-global `~/.claude/` or a project-local
`<repo>/.claude/` — and in a foreign project the executor guessed the wrong root,
looked in the current repo / skill dir, and wrongly reported the target missing.
The reference was *valid* (`~/.claude/conventions/documentation.md` existed); the
failure was runtime path resolution, not a broken reference.

**Why it happens.** Nothing resolves the tag — `grep -rn 'working-dir'
skills/scripts --include='*.py'` finds no parser; it is a convention the LLM must
interpret by hand. doc-sync compounds it: `skills/scripts/skills/doc_sync/` is an
empty package (only `__init__.py`), so no script reads and injects the file, yet
`skills/doc-sync/SKILL.md` claims the skill is "self-contained" while depending on
this external reference.

**Not covered by CI.** The reference-resolution guard
(`skills/scripts/tests/test_reference_resolution.py`) is a *static* check that the
target exists in the repo. It correctly passes here (the target exists) and cannot
catch a runtime misresolution of an already-valid reference.

**Fix (when scheduled).** Make the reference unmissable rather than conventional:
- In `skills/doc-sync/SKILL.md` (the `<file working-dir=".claude"
  uri="conventions/documentation.md" />` line), replace/augment the bare tag with an
  explicit instruction, e.g. *"Read the format spec from
  `~/.claude/conventions/documentation.md` (or
  `$CLAUDE_PROJECT_DIR/.claude/conventions/documentation.md` for a project-local
  install)."* — or inline the spec so the skill is genuinely self-contained as it
  claims.
- Apply the same disambiguation to the agents that use the identical tag:
  `agents/technical-writer.md`, `agents/architect.md`, `agents/developer.md`,
  `agents/quality-reviewer.md` (all reference `conventions/…` and root `CLAUDE.md`
  via `<file working-dir=".claude" uri="…" />`). Line numbers drift — locate each by
  the tag string.

**Decision to make first.** Whether to (a) keep the `<file>` convention but document
its resolution rule once where every executor reads it, (b) switch to explicit
absolute-path instructions per reference, or (c) give doc-sync a real script that
reads + injects the convention (like the Python skills' `format_file_content`).

## Normalize the duplicated parallel-dispatch instruction

**Status:** deferred · **Surfaced:** 2026-08-18 (prompt audit of the planner workflow;
flagged independently by the architecture and clean-code review lanes)

**Problem.** One instruction ("dispatch all N agents in a single message; do not wait for
one before dispatching the next") has three owners, and the audit rewrote only the one in
the planner's path, so they now differ in force:

- `skills/scripts/skills/lib/workflow/prompts/subagent.py` `PARALLEL_CONSTRAINT` — rewritten
  to normal register. Consumers: the planner's QR fan-out (`planner/shared/builders.py`),
  `arxiv_to_md/main.py`, `codebase_analysis/analyze.py`, `deepthink/think.py`.
- `skills/scripts/skills/lib/workflow/ast/dispatch_renderer.py` `_build_execution_constraint`
  — still `You MUST dispatch ALL {count} agents`, CORRECT/WRONG blocks, `FORBIDDEN: Waiting`.
  Consumer: `refactor` (via `TemplateDispatchNode`).
- `skills/scripts/skills/refactor/refactor.py` (~L1427) — a third, hand-rolled copy of the
  same wording inside a literal `<parallel_dispatch>` block.

**Why it was not fixed.** The audit's scope was narrowed by the user to the planner
workflow; the other two copies are reached only by `refactor` / `incoherence`. Both review
lanes recommended recording the divergence rather than widening scope, because the risk is
that the next reader treats the shouty XML copy as the intended phrasing.

**Fix (when scheduled).** Decide one owner for the instruction text, then either have
`_build_execution_constraint` render from `PARALLEL_CONSTRAINT` (XML-wrapping it) or accept
two renderings with identical wording. Delete the hand-rolled copy in `refactor.py` in the
same pass. Re-run the refactor skill's step 2 before/after to confirm the rendered dispatch
is still well-formed XML.

## Give planner and executor state dirs a collision-proof location

**Status:** SCHEDULED -- implementation starts in the checkpoint after this audit lands;
this entry stays until then as the spec. · **Surfaced:** 2026-08-18 (a review subagent's `rm -rf /tmp/planner-*`
destroyed another session's planner state dir; confirmed by that session to affect
`/tmp/executor-*` identically)

**Problem.** Both orchestrators mint their state directory with a bare temp prefix:

- `skills/scripts/skills/planner/orchestrator/planner.py:213` — `tempfile.mkdtemp(prefix="planner-")`
- `skills/scripts/skills/planner/orchestrator/executor.py:693` — `tempfile.mkdtemp(prefix="executor-")`

Every session on a machine therefore shares one flat `/tmp/planner-*` + `/tmp/executor-*`
namespace, with no session or repo identity in the path. Consequences:

1. A cleanup glob in any session (`rm -rf /tmp/planner-*`) destroys every other session's
   planning and execution state. This happened: a planner state dir belonging to a
   concurrent session in another repo was deleted mid-effort.
2. State that outlives a session (`plan.json` is authoritative until approval renders
   `plan.md`; the executor's copy plus its `qr-*.json` live for the whole run) sits in a
   directory whose name carries no clue about which repo or session owns it, so it cannot
   be attributed, backed up, or safely reaped.
3. `/tmp` reapers and reboots discard in-flight plans with no warning.

**Not covered by anything.** `docs/plans/` receives `plan.md` only at approval
(`planner.py::_save_plan_to_docs`), and the executor's reduced `plan.json` is never
persisted anywhere. A run interrupted before approval leaves nothing behind.

**Fix (when scheduled).** Default the state dir to a repo-local, git-ignored path — e.g.
`<repo>/.agent-state/planner/<slug>/` and `.../executor/<slug>/`, resolved through the same
`_find_repo_root()` the plan-saving path already uses — and fall back to a per-session temp
path (session id in the prefix) when no repo root is found. `--state-dir` already exists on
every entry point, so the change is the default plus the docs that name `/tmp` paths.

**Decisions taken (2026-08-18).** Repo-local is the **default**: state goes under
`<repo>/.agent-state/` in a subtree that cannot collide with the task-tracking convention's
`.agent-state/<task-slug>/` (a task slugged `planner` would otherwise clash). Detect whether
that path is ignored with `git check-ignore -v --no-index` run with `cwd` set to the repo
root -- never by grepping `.gitignore`, which misreports the negative-whitelist model this
repo itself uses (`*` plus an anchored allowlist already ignores `.agent-state/`). When it is
genuinely unignored, append `/.agent-state/` per the git-ignore policy: anchored, after the
allowlist, existing model untouched. When no repo root is found, or the repo has no
`.gitignore` to append to, fall back to a per-session temp path
(`<tmpdir>/cc-<session>/{planner,executor}-<rand>/`) -- the load-bearing property is that
nothing lands at `/tmp/{planner,executor}-*` top level.

The executor **does** persist its reduced `plan.json` beside the approved `plan.md`, and loads
it instead of having the model re-type it -- closing, in the same work, the finding that an
interrupted executor run leaves nothing resumable behind (numbered S4 in the prompt-audit
report, which is not tracked in this repo; the in-repo mentions of "S4" in
`tests/test_batch_roundtrip_fixes.py` and `tests/test_audit_s4_cleanup.py` are unrelated).

Still open: whether to reap old state dirs on init.
