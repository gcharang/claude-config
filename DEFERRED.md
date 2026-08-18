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

## Persist the executor's reduced `plan.json` at plan approval (audit finding S4)

**Status:** SCHEDULED -- next checkpoint of the state-dir durability work. ·
**Surfaced:** 2026-08-18 (prompt audit of the planner skill)

The state-dir placement half has landed: `shared/resources.py::resolve_state_dir` puts
state under `<project>/.agent-state/_runs/{planner,executor}/`, anchored on
`$CLAUDE_PROJECT_DIR` then cwd, with a per-session temp fallback and its own retention.
The contract is documented in `skills/planner/INTENT.md` ("State directory location").

**What remains.** Executor step 1 asks the model to hand-retype the reduced `plan.json`
(overview, milestones with `code_intents`/`is_documentation_only`, waves, referenced
decision-log entries) out of the `plan.md` rendering. The cost is a schema-mismatch risk
on every run, and a fresh session that has lost the state-dir path having nothing
structured to resume from.

Note the motivation is narrower than it was before the state-dir placement work. "An interrupted run
leaves nothing behind" was true against `/tmp`; a project-local state dir now keeps
`plan.json` and the whole QR state. What is left is the transcription risk plus
discoverability across sessions.

Fix: reduce the approved plan in Python (`shared/schema.py::reduce_plan_for_executor`),
give the executor `--plan-json`, and shrink step 1's LLM job to reading the plan for
context plus the optional reconciliation check. Keep the hand-authoring path for plans
approved before the change. The on-disk key is `planning_context.decision_log` (the input
alias), not `.decisions` -- reading the wrong one yields a false unresolvable-refs report.
The reduced log is filtered to the entries some `code_intent.decision_refs` references --
stricter than, and therefore always compatible with, the executor's own guard
(`executor.py::main`'s `has_decision_refs` check, beside the
`validate_structural_executability` call), which rejects only decisions present with no
referencing intent at all.

**Decisions (2026-08-18, user):**

- The reduced artifact lives in the STATE DIR, not `docs/plans/`. Machine state is created
  only where git proves it ignored, deliverables unconditionally (`INTENT.md`, "Two rules
  that govern every write"); `docs/plans/` is the ungated path, and routing a machine
  artifact through it contradicts the rule the rest of the checkpoint follows.
  `docs/plans/` is also git-ignored in this repo (root `.gitignore` is `*` plus an
  allowlist that omits `docs/`), so its "browsable" benefit was partly illusory. Rejected:
  `docs/plans/<date>-<slug>.plan.json` -- it would also have required extracting
  `_save_plan_to_docs`'s stem/collision-suffix logic and solving a two-file publish under
  one suffix with no atomicity (the suffix loop probes `.md` existence alone).
- `--plan-json` is DATA, never a project anchor. Identity stays recorded marker >
  `$CLAUDE_PROJECT_DIR` > cwd. Rejected: letting a supplied plan's origin outrank the live
  shell -- a third input multiplies the disagreement cases with no arbitration rule.
- Identity fails closed ONLY when `--plan-json` is passed. Without it, best-effort as today
  (warn, proceed), so every existing invocation -- including the fresh-`git init` shape
  that degrades to temp -- is unchanged. With it, an unresolvable or contradictory project
  aborts step 1, because identity then decides what gets built, not only where the plan is
  archived. Rejected: fail closed always (turns today's soft warning into a hard stop for
  existing invocations); best-effort everywhere (an execution input the run cannot vouch
  for is the exact case the marker mechanism exists to refuse).
- Cross-kind reaping is AVOIDED, not managed: the executor reads the planner's artifact
  once at step 1 and copies it into its own run dir. Retention stays per-kind. Rejected:
  bumping the planner run's mtime on read (a read that mutates); an explicit
  back-reference (cross-run state that itself needs retention).

**Consequences.** The executor's `project_root` marker stays write-only
(`load_project_root` keeps its single caller, `planner.py::_save_plan_to_docs`) -- a
deliberate choice for symmetry and human discoverability. The `.agent-state`-vs-
`docs/plans` write-gating asymmetry is deliberate and stated in `INTENT.md`.

**Still open, decide at implementation:** the artifact's file NAME. `plan.json` in the
planner's run dir is already the FULL plan and `plan.json` in the executor's run dir is
step 1's own target, so the reduced artifact needs a distinct name (e.g.
`executor-plan.json`) -- chosen when the reducer is written, not before.
`ensure_project_root_recorded()` returns `None` today; the fail-closed branch needs the
classification it discards, so it should return the marker kind (or the resolved root)
when `--plan-json` lands rather than a third `resolve_project_root()` call in one step 1.

## Make a truncated `project_root` marker decidable

**Status:** DEFERRED -- low value. · **Surfaced:** 2026-08-18 (architecture review)

`ensure_project_root_recorded` replaces a marker this planner could not have written
(after a lossy decode: empty, relative, or carrying a non-blank remainder after its first
line) but reports-and-keeps a well-formed absolute path whose project no longer resolves.
A trailing blank line or NUL tail is explicitly NOT foreign -- our own single-line write
survives intact ahead of such padding, and treating it as foreign re-points the run. A truncated write lands in the second case and is
byte-for-byte what a deleted project looks like, so it is never repaired.

Making the two separable needs a format change -- a trailing sentinel line, or
path-plus-length -- not a smarter heuristic; every shape-based rule fails on this input.

Low value because `_save_project_root` is atomic, so nothing here can originate a
truncated marker. What remains is markers already on disk from another writer, and
hardware faults.

## Extract the repo/run-state helpers out of the planner package

**Status:** DEFERRED -- decided 2026-08-18 to keep them in `resources.py` for now, so the
state-dir checkpoint stayed reviewable. · **Surfaced:** 2026-08-18 (architecture review)

`shared/resources.py` is chartered as a resource loader plus the `state_dir` argument
contract. It now also runs `git` in a subprocess, reads the environment, mutates a user's
`.gitignore`, and mints directories. None of `_is_git_dir`, `find_repo_root`,
`resolve_project_root`, `_check_ignored`, `ensure_agent_state_ignored`, `_session_token`,
`_temp_state_dir`, or `resolve_state_dir` is planner-specific -- only the two `StateDirKind`
values are. A sibling skill wanting a durable run dir would have to import from
`skills.planner.shared`, which inverts the layering.

Proposed split: `skills/lib/gitrepo.py` (`is_git_dir`, `find_repo_root`, `is_ignored`,
`ensure_ignored`, `_tracks_anything`, `_run_git`, plus the `_has_rule` /
`_append_gitignore_rule` helpers and `GITIGNORE_RULE`) and
`skills/lib/runstate.py` (`AGENT_STATE_DIRNAME` -- which `ensure_ignored` probes, so
`gitrepo` takes it as an argument rather than importing it -- `RUNS_NAMESPACE`,
`_RUN_DIR_RE`, `StateDirKind`, the `_MARKER_*` kinds, `resolve_state_dir`,
`require_usable_state_dir`,
`ensure_project_root_recorded`, `_save_project_root`, `load_project_root`, `_read_marker`,
`_fallback`,
`PROJECT_ROOT_FILE`, `_reap_old_runs`, `_last_activity`, `_created_ancestors`,
`_prune_empty`, `_session_parent`, `_is_our_private_dir`, `_mkdtemp_usable`, the retention
constants, the session token and the temp fallback), with `resources.py` back to its
charter. `_mkdtemp_usable` has three callers (`_session_parent`, `_temp_state_dir`,
`resolve_state_dir`) so the move-it-with-its-owner rule has no single answer -- all three
are `runstate`-bound, which settles it. `resolve_project_root` and `_resolved_home` go with `runstate`, NOT with
`gitrepo`: they read `$CLAUDE_PROJECT_DIR` -- a Claude Code harness variable -- and
encode a product policy (refuse a `$HOME` reached by stumbling, honour one named
explicitly). Filing them under `gitrepo` would split "which project does this run belong
to" across both modules and make a module named for git plumbing harness-aware and
policy-bearing, which is the same charter creep the move exists to cure. Move each
function's private helpers with it -- leaving `_reap_old_runs`/`_last_activity` behind is
the easy mistake. Keep the project-root
persistence with `runstate`, not `gitrepo`: `resolve_state_dir` and both orchestrators use
it, so splitting it the other way recreates the inverted import the move exists to remove.
Do this when a second skill needs a run dir, or alongside the next substantial change to
these functions -- whichever comes first.

Two shape changes belong to the same pass, both deliberately not done now because they
churn a module that is about to move:

- `resolve_state_dir` is named for a computation and has three side effects, sitting
  beside the pure `resolve_project_root` under a shared `resolve_` prefix. Split it into
  anchor resolution plus a `_mint_project_local(repo_root, kind)` owning the whole
  create -> gate -> verify -> undo transaction, and rename it (`mint_state_dir`) so the
  prefix stops implying it is a query. The `decline()` closure is that transaction's
  current shape; a function boundary makes "no decline leaves anything behind" readable
  in one place rather than provable by inspection.
- `ensure_ignored` should keep taking the probe path from its caller, as
  `ensure_agent_state_ignored` now does. A hardcoded `<dirname>/probe` asks about a file
  nothing creates, which a rule matching that basename satisfies while the real directory
  stays visible to git. It must ALSO take the dirname and the rule as parameters in the
  same pass: today only the probe is a parameter, while `GITIGNORE_RULE` and the
  tracked-files question stay hardcoded to `.agent-state`. Left that way the move produces
  a generic-looking `ensure_ignored(repo_root, probe)` in a shared module that silently
  works for one directory only -- worse there than here, where the pairing is local and
  stated as a precondition. Target `ensure_ignored(repo_root, dirname, rule, probe)`, and
  drop that precondition note when it lands.
- `_created_ancestors` gained a `stop in leaf.parents` guard so containment is structural
  rather than a property of its single call site; keep it when the helper moves.
- The "our directories are exactly 0o700" invariant has one reader (`_is_our_private_dir`)
  and two writers (`_mkdtemp_usable`, and `_session_parent`'s create branch), each
  restating the same umask fact. Give them a shared `_force_private(path)` tail so the
  rationale is stated once -- deleting either chmod is the exact misconception the fix
  exists to correct, and under a hostile umask it silently scatters a session's runs
  across fresh unguessable parents rather than failing.
- `_check_ignored`'s `None` contract records that "beyond a symbolic link" is one of its
  cases. That refusal is git's, not a check in this module, and it is what keeps a
  symlinked `.agent-state` from being written through -- do not lose the note.
- The test module splits with the source: `tests/test_state_dir_placement.py` (~3100
  lines) divides along the same `gitrepo` / `runstate` seam (`test_gitrepo.py` /
  `test_runstate.py`), so the split does not leave a monolithic test file behind.

Two helpers resist that rule. `_read_all` and `_close_quietly` are each shared by
`_read_marker` (bound for `runstate`) and `ensure_agent_state_ignored` (bound for
`gitrepo`), so "move each function's private helpers with it" has two answers and no
tiebreak; duplicating them into both modules is worse still, since the next fix to one
descriptor path silently leaves the other behind. Put both in `skills/lib/io.py` beside
`atomic_write_text`: they are descriptor plumbing with nothing repo- or run-specific in
them, and that module is already where this codebase keeps its I/O idioms.

Do NOT unify the two `os.open` sites while moving them. Their flag sets differ for
reasons local to each: the marker opens `O_RDONLY | O_NONBLOCK | O_NOFOLLOW`, where
`O_NONBLOCK` exists solely so a FIFO planted at the marker path opens instead of blocking
step 1 forever with nothing on stderr; the `.gitignore` opens
`O_RDWR | O_APPEND | O_NOFOLLOW`, where `O_APPEND` is what keeps a concurrent editor's
write from being clobbered. Only `O_NOFOLLOW` is genuinely common to both. A shared opener
would hand `O_NONBLOCK` to a site that has no use for it and strand the comment explaining
why it is there -- and that rationale is the entire reason the flag survives review.

Fold in one more thing when this moves: step 1's three-call sequence
(`supplied or resolve_state_dir(kind)` -> `require_usable_state_dir` ->
`ensure_project_root_recorded`) is duplicated across both orchestrators, and its order
is load-bearing -- validation must precede recording, or an unusable state dir draws a
soft project-marker warning ("not recording a project" when no anchor resolves, "could
not record project root" when one does) immediately before the real error. Today that
invariant lives in `planner.py::_begin_run` (which names the order and is the planner's
local precursor to this helper) and a cross-reference comment in `executor.py`. Nothing
else enforces it: `test_step_1_rejects_an_unusable_state_dir` constrains which INPUTS both
orchestrators refuse, not the SEQUENCE -- both orders exit with a byte-identical message,
differing only by a stderr warning. `test_step_1_validates_before_it_records` pins the
order for both, so this fold-in is a simplification rather than a repair.

The steps-2+ preamble is duplicated too, and more literally: both orchestrators run
`validate_state_dir_requirement` then `require_usable_state_dir` in the same order, under a
byte-identical four-line comment, and wrap the first in the same `try/except ValueError ->
sys.exit` because the two validators report through different protocols (one raises, one
exits). Fold both branches into one `resolve_run_state_dir(kind, step, supplied)` and settle
the protocol split in the same pass; duplicated RATIONALE is the reliable signal.
The fold-in's clean exit should reach all six call sites of
`validate_state_dir_requirement`, not just the two orchestrators -- the four sub-agent
scripts (`quality_reviewer/prompts/fix.py`, `architect/plan_design_execute.py`,
`developer/exec_implement_execute.py`, `technical_writer/exec_docs_execute.py`) let the
`ValueError` escape as a raw traceback today.

A single `begin_run(kind, supplied) -> str` would own the step-1 order and let both helpers
become private. It is NOT a straight lift on either side: the executor interleaves
`verify_path(state_dir).unlink()` between validation and recording, and the planner appends
`_write_plan_skeleton` after recording. Settled here so it is not re-litigated at
implementation time: the executor's clear moves to after the recording -- nothing between
them reads `verify.json` -- rather than the helper growing a callback for one call site.
It would also fold away the redundant `resolve_project_root()` call -- `resolve_state_dir`
and `ensure_project_root_recorded` each make one, and while they cannot disagree inside a
single process, only one of them needs to. Two review lanes split on whether this is worth
doing on its own (one proposed it, then withdrew it as stylistic; the other re-raised it)
-- do it as part of the move, not before, and note that the executor's `--plan-json` work
would otherwise be the third site to re-derive the order.

The visible symptom meanwhile: `planner.py` imports `load_project_root` and
`ensure_project_root_recorded` from a module named `resources`, purely so step 1 and
`_save_plan_to_docs` can ask "which project is this".
