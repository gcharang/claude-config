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
