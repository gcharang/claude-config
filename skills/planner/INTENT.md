# Planner Skill Design Intent

Authoritative design specification for the planner skill. This document governs WHY the system works the way it does. Implementation MUST conform to this spec.

## Philosophy

Three principles govern this design:

**RESOLVE AMBIGUITY EARLY**: Business decisions happen in planning phase, BEFORE code is written. Execution is mechanical. Questions about requirements, architecture, or approach get answered during planning, not discovered during implementation.

**CAPTURE INVISIBLE KNOWLEDGE**: Decisions, rationale, and context are captured in state files so any agent can understand WHY, not just WHAT. When a sub-agent picks up work, it reads state files and has full context. No information lives only in conversation history.

**QUALITY OVER SPEED**: LLMs make mistakes. Multiple QR gates with iteration loops catch errors before they propagate. This skill explicitly trades execution time for correctness.

## State Files

All state mutation (except initial context capture) happens via Python scripts. The orchestrator dispatches sub-agents; sub-agents invoke scripts; scripts emit prompts; LLM performs work and writes state.

### State directory location

Step 1 of each orchestrator creates the state directory through `shared/resources.py::resolve_state_dir(kind)` when `--state-dir` is absent, and honours the supplied path when it is present (the resume path -- re-running step 1 against an existing dir must not replace the plan being resumed). Steps 2+ always require `--state-dir`, and both orchestrators check that it is still a usable directory before reading `plan.json` from it -- retention can remove a run dir between steps, and reporting that as "plan.json not found" invites a fix that recreates the directory without its project marker.

The two orchestrators reset different things on a resume, deliberately: the executor clears `verify.json`, because a previous run's final verdict must never be inherited, while the planner clears nothing -- its `qr-<phase>.json` findings are the work being resumed. Neither clears `plan.json` in Python. The guarantee is not symmetric: the planner's skeleton write is guarded by `if not plan_path.exists()`, so a resumed plan survives structurally, whereas the executor's step 1 instructs the orchestrator to author `plan.json` fresh and therefore re-authors it by design. The resume promise is about the state DIRECTORY, not about every file in it.

| Branch          | Path                                                                  | When                                                                                                                                             |
| --------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Project-local   | `<project>/.agent-state/_runs/{planner,executor}/<UTC-stamp>-<rand>/` | The project resolves to a git repo, `.agent-state` is (or can be made) git-ignored there, and git confirms the run directory *itself* is ignored once minted |
| Per-session tmp | `<tmpdir>/cc-<session>/{planner,executor}-<rand>/`                    | Any other outcome: no project, no `.gitignore` to append to, git cannot answer, the file is a symlink or unreadable, the rule is present but negated, the append cannot be confirmed, the repo already *tracks* files under `.agent-state`, `.gitignore` exists but is not a regular file, the path is unwritable, the run directory cannot be minted inside it, or the minted directory turns out not to be ignored after all |

Project-local is preferred so state survives a `/tmp` reap or reboot and is attributable to the project it belongs to -- `plan.md` only reaches `docs/plans/` at approval, so an interrupted run would otherwise leave nothing behind.

#### Finding the project

`resolve_project_root()` reads `$CLAUDE_PROJECT_DIR`, then falls back to the process working directory. It never uses the scripts' own location: `Path(__file__)` is whichever repo holds the skill source, or an un-repo'd `~/.claude` for a user-global install. Anchoring there sends one project's state -- and its approved plans, via `_save_plan_to_docs` -- into an unrelated repository, and leaves the project-local branch unreachable entirely for a user-global install.

The working directory is only trustworthy where the caller has not been `cd`'d away from the project first, which is **step 1 alone**. Its `SKILL.md` invocation therefore uses `uv run --project <SKILLS_DIR> python -m ...` rather than `<invoke working-dir=...>`: `working-dir` resolves the install layout by `cd`-ing into it, discarding the working directory -- the one signal Claude Code supplies for these subprocesses. Claude Code populates `$CLAUDE_PROJECT_DIR` for hook subprocesses but not for the Bash-tool subprocesses these scripts run in, so in practice the working directory is what resolves.

Steps 2+ never repeat this lookup. Step 1 records the resolved root in `<state_dir>/project_root` via `ensure_project_root_recorded()`, and the terminal `docs/plans/` save reads it back with `load_project_root()` -- by then the process has been `cd`'d into `SKILLS_DIR` and the working directory would name the skill tree. `load_project_root` re-checks that the recorded path is still a repo, because a state dir can outlive the checkout it was minted against.

Identity is recorded independently of placement, on **every** route through step 1: project-local, either temp fallback, and a supplied `--state-dir` (which never calls `resolve_state_dir` at all). A run whose state lands in temp still belongs to a project and still archives its approved plan there. Tying the recording to the project-local branch alone would leave the likeliest first-run shape -- a fresh `git init` with no `.gitignore`, which declines project-local -- unable to archive anything. The recorded project is named on stderr, because a temp path carries no clue which repo the plan will be written into.

The recorder asks one question of an unusable marker: could `_save_project_root` have produced these bytes? It writes a single absolute line, always. Content that is empty, relative, or carrying a non-blank remainder after its first line answers **no** -- provably not ours -- and is replaced (a trailing blank line or NUL tail is *not* such a remainder: our own single-line write survives intact ahead of it, and an editor "fixing" the file on save or a post-crash ext4 tail produces exactly that shape) (undecodable bytes are not a separate test: they are decoded lossily and judged on that same shape, since a decode failure only proves "not ours" for an all-ASCII path); gating on the file merely existing instead makes such a marker permanent. Everything else is **kept and reported**: a marker that is not a regular file (symlink, FIFO, directory -- opening one either follows a link out of the project or blocks forever), a well-formed path whose project no longer resolves, a usable marker naming a different project than the current shell, and -- importantly -- content that could not be *read* at all, since a failed read answers "unknown" rather than "no". Overwriting any of them would silently re-point a run minted in project A at project B; the recorded value is the run's identity, the shell that happens to resume it is not. A truncated write is byte-for-byte a deleted project, so it is kept too; nothing here can originate one, because the marker write is atomic. One project path cannot be recorded at all: the marker is a single line, so a path containing a newline is refused rather than written in a form that reads back as foreign. Every path out of the recorder states what it did on stderr. Where an unusable marker is kept -- `_MARKER_KEEP`, or a usable one naming a different project than this shell -- the message names the marker file so it can be removed by hand; a corrupt marker's message names it too, before it is replaced. When no project resolves at all the message names the missing anchor instead: there is nothing to record, and the marker is not the problem.

The walk climbs to the filesystem root, so a working directory outside any project plus a dotfiles repo at `$HOME` would resolve the "project" to the home directory. That is refused: it is the same misfiling this anchor exists to prevent. An explicit `$CLAUDE_PROJECT_DIR` naming `$HOME` is honoured, because that is a choice rather than a stumble -- so if your dotfiles repo IS the project you want, export `CLAUDE_PROJECT_DIR=$HOME` (Claude Code does not set the variable for these subprocesses; see `skills/scripts/skills/lib/workflow/prompts/README.md`). The comparison resolves both sides, so a `$HOME` that is relative or reached through a symlink is still recognised.

The `cc-<session>` grouping is a convenience, not a guarantee. `CLAUDE_CODE_SESSION_ID` is not a secret -- it is also the basename of `~/.claude/projects/<slug>/<session>.jsonl` -- so that path is predictable to any local user. If something already sits there that is not a private directory of ours (wrong owner, wrong mode, or a symlink), it is not repaired and not adopted: an unguessable `cc-<rand>` parent is minted instead, and the decline is announced on stderr like every other decline in this module. An unguessable `0700` directory is the floor this must not fall below, and adopting a parent we cannot vouch for falls below it.

Every fallback prints its reason to stderr. All of the conditions above return the same kind of path, so without the reason "why is my state in /tmp again?" would be answerable only by re-deriving the predicates by hand.

#### Making `.agent-state` ignored

The rule is an anchored `/.agent-state/` appended to an **existing** `.gitignore`, announced on stderr because it writes to a version-controlled file the user authored. Ignore status is decided with `git check-ignore --no-index` run with `cwd` at the repo root, never by scanning `.gitignore` text: a negative-whitelist model (`*` plus an anchored allowlist) already ignores the path without naming it. `--no-index` is what makes the answer come from the rules alone; without it a path that happens to be in the index reports as not-ignored, which is a true statement about tracking and the wrong answer to "may I create state here".

The gate is asked about the runs directory the caller is about to mint -- `.agent-state/_runs/<kind>` -- never about a synthetic name. A hardcoded `.agent-state/probe` would ask about a file nothing ever creates, so a repo carrying a bare `probe` rule (or `*probe*`) would answer "ignored" while the run directory beside it stayed plainly visible to git. The minted leaf is then re-checked as well, for a different reason: the gate's answer was about a different path obtained a moment earlier, and `is not True` also catches git having become unable to answer at all in between. A nested negation cannot reach that branch -- git refuses to re-include anything below an excluded directory. The runs directory is also created *before* the gate runs and taken back if the gate declines: the append mutates a tracked file, so it must not happen for a directory that then turns out to be uncreatable -- that would strand the rule, and every later run would be silent about it, because the rule is by then already present.

Two rules govern every case where it declines to write instead:

- **Only mutate when the effect can be verified before and after.** A `check-ignore` that cannot answer (no git, not a repo, dubious ownership, timeout) means the edit could not be checked either. A symlinked `.gitignore` is the same case: git refuses to read one at all, while `Path.is_file()` follows the link, so appending would write through it into a file the repo may not own and the confirmation could not succeed regardless. An append whose re-probe fails is reported as failure -- and the write is announced when it lands, not when it is confirmed, so a confirm-failed mutation is never silent.
- **Only mutate within the narrowest unambiguous scope.** A repo with no `.gitignore` never gets one created: that means choosing a whole ignore policy for someone else's repo, which the git-ignore policy treats as a deliberate act. A rule already present as an active line while the path is still unignored means something later un-ignores it -- most plainly a deliberate `!.agent-state` -- and a second copy would both duplicate the rule and reverse that intent. A repo that already **tracks** files under `.agent-state` is that same case reached through the index rather than the rules: the append would not untrack what is committed, but it would make every new file there invisible, and committed content is the plainest expressed intent there is. `check-ignore --no-index` is deliberately blind to the index, so the question is asked separately with `git ls-files`.

Whitespace matters to the rule-already-present half of that second bullet: gitignore drops trailing whitespace but keeps **leading** whitespace as part of the pattern, so `  /.agent-state/` is an inert line, not the rule. It is treated as absent and the real rule is added.

**The append dirties a tracked `.gitignore`.** In a repo where `.gitignore` is committed, `git status` shows ` M .gitignore` afterwards. That is unavoidable -- a rule cannot reach a tracked file without a working-tree diff -- so it is stated here rather than surprising a first-time user. Repos whose `.gitignore` already covers `.agent-state` (including via a `*`-plus-allowlist model or `.git/info/exclude`) are never touched at all.

#### Namespacing and retention

`_runs/` is a reserved level: `.agent-state/<task-slug>/` belongs to the session task-tracking convention, and a task slugged `planner` would otherwise share a directory with planner runs. The reservation is a convention rather than something code enforces, but a leading underscore is not a shape kebab-case slugs take.

`/tmp` reaps itself; a project working tree does not, so a `resolve_state_dir` that lands project-local prunes its own `_runs/<kind>/` afterwards (a decline never reaches the reap). A directory is removed only when **all four** hold: its name matches the minted `<UTC-stamp>-<rand>` prefix (so an unrelated directory parked there is untouched, unless its name happens to take that shape -- `_runs/<kind>/` is machine-managed and not a place to keep anything by hand), it falls outside the newest `RUNS_KEEP_NEWEST`, it has been inactive for `RUNS_MAX_AGE_DAYS`, and it is not a symlink (a planted link is never handed to `rmtree`, and never stat'ed through -- inactivity would otherwise be measured on the link's target). Inactivity is measured across the run directory **and everything beneath it** -- a directory's own mtime moves only when an entry is created, renamed, or unlinked, so an in-place rewrite of `plan.json` would otherwise make an actively-edited run look stale. A run whose subtree cannot be examined in full is left alone for that pass rather than judged on the part that could be read: `rmtree` would fail at the same unreadable child, after unlinking the siblings it reached first. A child that vanishes between the listing and the stat also leaves the run unjudged for the pass; that costs nothing -- the next pass will not see the child at all. The age bound is what keeps a resumed session safe however many runs start after it. Retention is deliberately not keyed on whether a plan was approved. A planner run dir does record it -- `plan.md` has a single writer, reached only behind the terminal gate -- but approval is the wrong signal: the run that must survive is the **un**approved one still being worked, while an approved plan has already been published to `docs/plans/`. An executor run dir has no `plan.md` at all.

#### Two rules that govern every write

Both are stated once here because a new failure path otherwise gets added on the wrong side of them.

**What is gated, and what is not.** Machine state is created inside the user's tree only where git *proves* it ignored -- on the route that **mints** it. `resolve_state_dir` makes `.agent-state/`, checks the ignore status against the path actually minted (not a proxy), and takes the directory back again if that check fails. A supplied `--state-dir` is not gated: it is the caller naming a location outright, and `require_usable_state_dir` asks only whether it exists and is a directory, so pointing it at tracked territory writes there. Deliverables are created unconditionally in the recorded project -- `_save_plan_to_docs` mkdirs `docs/plans/` with no gate at all. The asymmetry is deliberate: `.agent-state/` is machine state that must never be committed, while an approved plan is output the user should be able to commit. A new write into the user's tree belongs on one side or the other, and which one follows from that question alone, not from where the code happens to sit.

**What aborts, and what degrades.** Abort when the run cannot proceed; degrade when only an ancillary artifact is lost. Aborting: no state directory at all (`_temp_state_dir`), a step 2+ invocation carrying no `--state-dir` (`validate_state_dir_requirement`, in both orchestrators), a supplied `--state-dir` that is missing or is not a directory (`require_usable_state_dir`), an unwritable `plan.json` at step 1 (planner only -- the executor deliberately writes no skeleton). Degrading: every decline of the project-local branch (`_fallback`), an unwritable project marker (only `docs/plans/` is lost), a stale `verify.json` that will not unlink, a reaping pass that fails. The split is not "caller mistake aborts, environment degrades" -- the `plan.json` write failure is an environment failure that aborts, because without it there is no run.

The **run** directory is `0o700` on both branches -- including inside the user's repository -- and so is the temp branch's `cc-<session>` parent. `mkdtemp` asks for that mode and the umask masks it, so `_mkdtemp_usable` and `_session_parent` re-assert it afterwards: a umask can only clear bits, so the re-assert cannot loosen anything, and without it a umask with owner bits set yields a directory the run itself cannot write into. The project-local ancestors -- `.agent-state/`, `_runs/`, `_runs/<kind>/` -- are not hardened: `mkdir` gets no mode, so they land at `0o777` masked by the process umask (measured `0o755` under `022`, `0o775` under `002`). The `0o700` floor exists for a predictable name in a shared `/tmp`, not for a directory inside a repository the user already owns.

The load-bearing property of both branches is that nothing is created at a top-level `/tmp/{planner,executor}-*`. That flat namespace is shared by every session on the machine, and a cleanup glob in one session destroyed another session's in-flight plan (2026-08-18).

### context.json

Created by orchestrator in step 2 (context-verify). Persists user-provided planning context for sub-agent handover.

```json
{
  "task_spec": ["goal sentence", "scope: dir/module", "out-of-scope: X"],
  "constraints": ["MUST: X", "SHOULD: Y"],
  "entry_points": ["file:function - why relevant"],
  "rejected_alternatives": ["alternative - why dismissed"],
  "current_understanding": ["how system works", "bug: symptom + repro"],
  "assumptions": ["inference (H/M/L confidence)"],
  "invisible_knowledge": ["design rationale", "invariants", "tradeoffs"],
  "user_quotes": ["verbatim quote with context"],
  "reference_docs": ["doc/spec.md - what it specifies"]
}
```

All fields are string arrays. Empty arrays are acceptable; omitting fields is not.

**QR workflow access**: context.json is available to all QR sub-agents (decompose, verify, fix) as read-only reference for semantic validation against original user requirements. This enables QR agents to verify not just structural correctness but also alignment with user intent.

### plan.json

Primary state file. Created in step 1 (plan-init) as skeleton. Mutated through planning phases.

**No schema versioning**: State files (context.json, plan.json, qr-\*.json) are ephemeral, created and consumed within a single planning session. Schema versioning adds complexity without benefit for short-lived artifacts. Pydantic v2 models in `shared/schema.py`.

```
Plan
  overview
    problem: string       -- what we're solving
    approach: string      -- how we're solving it

  planning_context
    decisions: Decision[]
      id: "DL-001"
      decision: string
      reasoning: string   -- logical chain using -> notation
                          -- e.g. "high call volume -> bcrypt too slow -> use HMAC-SHA256"

    rejected_alternatives: RejectedAlternative[]
      alternative: string
      reason: string
      decision_ref: "DL-XXX"

    constraints: string[] -- free-form, e.g. "MUST: support Python 3.9+ (user-specified)"

    risks: Risk[]
      risk: string
      mitigation: string
      anchor: string | null       -- "file:L###-L###" if location-specific
      decision_ref: "DL-XXX" | null

  invisible_knowledge
    system: string        -- architecture, data flow, structure rationale as prose
    invariants: string[]  -- must-preserve properties
    tradeoffs: string[]   -- known compromises

  diagram_graphs: DiagramGraph[]   -- populated by Architect (IR + ascii_render)
    id: "DIAG-001"
    type: "architecture" | "state" | "sequence" | "dataflow"
    scope: string         -- "overview" | "invisible_knowledge" | "milestone:M-XXX"
    title: string
    nodes: DiagramNode[]
      id: string          -- "node-001"
      label: string       -- free-form, e.g. "gRPC Server"
      type: string | null -- free-form, e.g. "service", "database", "queue"
    edges: DiagramEdge[]
      source: string      -- node id (validated: must exist)
      target: string      -- node id (validated: must exist)
      label: string       -- free-form, e.g. "validates", "sends", "reads"
      protocol: string | null  -- free-form, e.g. "gRPC", "HTTP"
    ascii_render: string | null  -- populated by Architect at plan-design

  milestones: Milestone[]
    id: "M-001"
    name: string
    files: string[]
    requirements: string[]
    acceptance_criteria: string[]
    tests: string[]       -- free-form entries, e.g.:
                          -- "file:tests/test_auth.py"
                          -- "scenario:EDGE empty token returns 401"
                          -- "skip:no integration environment"
                          -- sweep: EVERY test coupled to a changed function,
                          --        not just the obvious one

    code_intents: CodeIntent[]  -- binding behavioral contract; populated by Architect
      id: "CI-001"
      file: string
      behavior: string    -- what the code should do, includes function/params
      decision_refs: string[]

    is_documentation_only: bool
    delegated_to: string | null

  waves: Wave[]
    id: "W-001"
    milestones: string[]  -- M-XXX refs
```

Waves execute in array order. All milestones in W-001 complete before W-002 begins. Milestones within a wave may execute in parallel.

Cross-reference validation: `Plan.validate_refs()` checks:

- `code_intents.decision_refs` -> `decisions.id`
- `rejected_alternatives.decision_ref` -> `decisions.id`
- `risks.decision_ref` -> `decisions.id`
- `diagram_graphs.edges.source` -> `diagram_graphs.nodes.id` (within same diagram)
- `diagram_graphs.edges.target` -> `diagram_graphs.nodes.id` (within same diagram)
- `diagram_graphs.scope` -> `milestones.id` (when scope is `milestone:M-XXX`)

### qr-{phase}.json

Ephemeral QR state. Created during QR decomposition. Deleted after phase passes. Three phases: plan-design, impl-code, impl-docs.

```json
{
  "phase": "plan-design",
  "iteration": 1,
  "items": [
    {
      "id": "qa-001",
      "scope": "*",
      "check": "Description of what to verify",
      "status": "TODO",
      "finding": null
    }
  ]
}
```

**Top-level fields:**

- phase: Which QR phase this file tracks
- iteration: Current QR loop count (1 = first attempt, 2+ = retry after failures)

**Item fields:**

- id: Unique identifier within phase (qa-001, qa-002, ...)
- scope: Free-form location specifier (see Scope Philosophy below)
- check: Actionable verification instruction
- status: "TODO" | "PASS" | "FAIL"
- finding: null or explanation string (required when FAIL)

The number of items in the array is adaptive -- determined by content complexity, not preset ranges. Simple phases may have fewer items; complex phases with many architectural concerns may have more.

#### Iteration as Single Source of Truth

The `iteration` field tracks QR loop count within the file itself. This is the authoritative source for iteration state -- no CLI flags track iteration.

**Decompose step behavior:**

Decomposition runs exactly ONCE per QR phase. The first invocation generates all QR items; subsequent iterations skip decomposition and re-verify existing items.

1. Check if qr-{phase}.json exists
2. If exists: SKIP decomposition, proceed directly to verify step
3. If absent: run 8-step decomposition, create file with iteration: 1
4. Output next step command

WHY single decomposition per phase:
Decomposition defines verification target. Regenerating items on each
iteration creates moving target: new items introduce new failures
unrelated to original issues, preventing convergence. Fix-verify loop
requires stable item set to terminate.

WHY file existence check, not iteration check:
Existence signals "decomposition complete"; iteration signals "verification
cycle count". Checking iteration would couple decomposition to verification
progress (wrong abstraction).

**Iteration semantics:**

The iteration counter tracks verification cycles, not decomposition cycles:

- iteration=1: first verification after initial decomposition
- iteration=2+: re-verification after fixes (incremented by verify step on RETRY)

Manual re-decomposition: Delete qr-{phase}.json to force fresh decomposition.

**Why file-based iteration:**

- Decompose script determines iteration programmatically from file state
- Gate/route steps need only invoke work step with --state-dir (no iteration arg)
- Single source of truth eliminates state drift between CLI args and file contents
- Aligns with "state detection over flags" invariant

#### QR File Path is Computable

The path to qr-{phase}.json is always `{state_dir}/qr-{phase}.json`. Scripts compute this from --state-dir and phase name; no CLI flag passes the path explicitly.

**Router detection logic:**

```python
def detect_fix_mode(state_dir: str, phase: str) -> tuple[bool, int]:
    """Check if QR file exists with failures. Return (is_fix_mode, iteration)."""
    qr_path = Path(state_dir) / f"qr-{phase}.json"
    if not qr_path.exists():
        return False, 1
    qr_state = json.loads(qr_path.read_text())
    has_failures = any(item.get("status") == "FAIL" for item in qr_state.get("items", []))
    iteration = qr_state.get("iteration", 1)
    return has_failures, iteration
```

**Implication for gate routing:**

Gate steps loop back to work steps with only --state-dir. The work step's router inspects qr-{phase}.json to determine whether to dispatch execute or fix workflow. This eliminates orchestrator responsibility for tracking failure state.

#### Scope Philosophy

QA items fall into two categories:

1. **Scoped checks**: Apply to specific code locations (files, functions, line ranges)
2. **Global checks**: Apply across the entire artifact (quality aspects, consistency rules)

Rather than separate fields for file, line, component, quality_aspect, etc., a single free-form `scope` field handles all cases. The LLM fills it with whatever granularity is appropriate:

| Scope Value                | Meaning                                |
| -------------------------- | -------------------------------------- |
| `*`                        | Global check -- applies everywhere     |
| `file:src/auth.py`         | Entire file                            |
| `file:src/auth.py:L10-L50` | Specific line range                    |
| `function:validate_token`  | Named function (any file)              |
| `component:auth-flow`      | Architectural component spanning files |

This trusts the LLM's prose comprehension. The decompose agent writes scopes that match how humans describe locations. The verify agent reads the scope and knows where to look. No rigid taxonomy needed.

**Prompt generation**: Scripts emit scope values verbatim to verification prompts. Example prompt fragment: "Verify the following in scope `{scope}`: {check}"

#### QR State Mutation (cli/qr.py)

After decomposition creates the initial qr-{phase}.json file, all subsequent mutations go through the QR CLI script. Agents do not modify the JSON file directly -- they invoke the script to update item status.

**CLI interface:**

```
uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.cli.qr --state-dir {state_dir} --qr-phase <phase> update-item <id> --status <status> [--finding <text>]

Arguments:
  --state-dir    State directory containing qr-{phase}.json (required)
  --qr-phase     One of: plan-design, impl-code, impl-docs (required)
  --status       PASS or FAIL (required)
  --finding      Explanation text (required when FAIL, forbidden when PASS)
```

**Example invocations:**

```bash
# Verify agent marks item as PASS
uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.cli.qr --state-dir {state_dir} --qr-phase plan-design \
    update-item qa-001 --status PASS

# Verify agent marks item as FAIL
uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.cli.qr --state-dir {state_dir} --qr-phase plan-design \
    update-item qa-003 --status FAIL --finding "Missing null check in validate_token()"
```

**Status semantics:**

- Items without explicit status are interpreted as TODO (initial state after decomposition)
- TODO means "not yet verified" -- the decompose agent creates items, verify agents evaluate them
- PASS means "verification passed" -- item is immutable, further updates raise an error
- FAIL means "verification failed" -- finding explains why, item can transition to PASS after fix

**Valid state transitions:**

```
TODO -> PASS         (verification passes on first attempt)
TODO -> FAIL         (verification fails)
FAIL -> PASS         (re-verification passes after fix)
FAIL -> FAIL         (re-verification fails again, finding may update)
PASS -> *            (ERROR: item is immutable once passed)
```

**Why script-mediated mutation:**

Parallel verify agents update the same qr-{phase}.json file simultaneously. Direct JSON writes cause race conditions (read-modify-write without locking = lost updates). The CLI script uses file locking (fcntl.flock) and atomic writes (tmp + rename) to serialize concurrent updates safely.

**Implementation reuse:**

The script reuses helpers from `shared/qr/utils.py`:

- `load_qr_state(state_dir, phase)` -- load and parse qr-{phase}.json
- `get_qr_item(qr_state, item_id)` -- find item by ID
- `get_qr_iteration_from_state(qr_state)` -- get current iteration from loaded state (1 if absent)
- `has_qr_failures_from_state(qr_state)` -- True if the loaded state has blocking FAIL items

The CLI script adds atomic save with locking (not in utils.py because only the CLI needs it). Router scripts use `route_work_phase()` (`shared/routing.py`) to detect fix mode from QR state.

#### Plan State Mutation (cli/plan.py)

Plan.json entities are mutated through the plan CLI script with Compare-And-Swap (CAS) versioning. Agents do not modify plan.json directly -- they invoke set-X commands that enforce version consistency.

**CAS Versioning Model:**

Each versionable entity has a `version: int` field starting at 1. Updates require providing the current version; the script rejects mismatches.

- Creates: `--id` omitted, `--version` omitted -> auto-generate ID, version=1
- Updates: `--id` provided, `--version` required -> validate version matches, increment on success

**Why CAS:**

1. **Race condition prevention**: Multiple agents cannot blindly overwrite each other's changes
2. **Forced read-before-write**: Agents must read current state to obtain version number
3. **Conflict detection**: Stale reads surface immediately as version mismatches

**CLI interface:**

```
uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.cli.plan --state-dir <dir> set-intent \
    --milestone M-001 --file path.py --behavior "description"    # create

uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.cli.plan --state-dir <dir> set-intent \
    --id CI-M-001-001 --version 1 --behavior "updated"           # update
```

**Version mismatch output:**

On version mismatch, the CLI prints the full current entity JSON and retry instructions. This ensures the agent always has the latest state on failure:

```xml
<version_mismatch_error>
  <entity_id>CI-M-001-001</entity_id>
  <provided_version>1</provided_version>
  <current_version>2</current_version>
  <current_entity>
    {"id": "CI-M-001-001", "version": 2, "file": "...", ...}
  </current_entity>
  <action>Integrate your changes into the current entity above and retry with --version 2</action>
</version_mismatch_error>
```

**Success output:**

On success, the CLI prints the entity ID and new version:

```xml
<entity_result>
  <id>CI-M-001-001</id>
  <version>2</version>
  <operation>updated</operation>
</entity_result>
```

**Unified set-X commands:**

| Command            | Entity       | Role      |
| ------------------ | ------------ | --------- |
| set-milestone      | Milestone    | architect |
| set-intent         | CodeIntent   | architect |
| set-decision       | Decision     | architect |
| set-diagram        | DiagramGraph | architect |
| add-diagram-node   | DiagramNode  | architect |
| add-diagram-edge   | DiagramEdge  | architect |
| set-diagram-render | DiagramGraph | architect |
| set-wave           | Wave         | architect |

The legacy add-X and update-X commands have been removed. set-X commands use CAS versioning for versioned entities (Milestone, CodeIntent, Decision, DiagramGraph); `add-diagram-node` and `add-diagram-edge` remain real commands; `set-wave` mutates without CAS (Wave has no version field).

## Documentation Model

Documentation is authored by exec-docs (Technical Writer) directly in the real implemented source files after impl-code QR passes.

### Code-Local Documentation

Documentation that lives in source files. Written by exec-docs against the actual implemented code, sourced from the Decision Log and Invisible Knowledge.

| Tier           | What                                      | Where       | Example                                                |
| -------------- | ----------------------------------------- | ----------- | ------------------------------------------------------ |
| Module comment | File-level: what's in here                | Top of file | `# auth.py -- Token validation and session management` |
| Docstring      | Function-level: what it does, when to use | On function | `def validate(token): """Validate JWT..."""`           |
| Inline comment | Logic explanation: algorithms, decisions  | Above code  | `# xxhash for speed; collisions acceptable (DL-003)`   |

The developer adds no comments. exec-docs authors all documentation after code is implemented and reviewed.

### Cross-Cutting Documentation

Documentation spanning multiple files/components. Created directly by exec-docs as new files in the source tree.

| Type      | What                                    | Handling                                        |
| --------- | --------------------------------------- | ----------------------------------------------- |
| README.md | Design decisions, architecture overview | exec-docs creates file directly in source tree  |
| CLAUDE.md | Navigation index for LLMs               | exec-docs creates file directly in source tree  |

## Diagram Model

Diagrams serve as the primary entry point for humans to understand what a plan implements. A well-crafted diagram answers "what does this do?" in under 10 seconds.

### Diagram Types

| Type         | When to Use                                    | Structure                       |
| ------------ | ---------------------------------------------- | ------------------------------- |
| architecture | Services, APIs, SDKs, component boundaries     | Boxes with directional arrows   |
| state        | Explicit state machines, protocol lifecycles   | Named states with labeled edges |
| sequence     | Multi-party request/response, time-ordered     | Vertical timeline, horiz arrows |
| dataflow     | ETL pipelines, streaming, data transformations | Left-to-right flow with stages  |

Default to `architecture`. Use others only when the plan explicitly involves state machines, multi-party protocols, or data pipelines.

### Diagram Scope

Scope determines where the diagram appears in rendered output:

| Scope                 | Renders In             | Purpose                                |
| --------------------- | ---------------------- | -------------------------------------- |
| `overview`            | After Overview section | "Hero" diagram -- first visual context |
| `invisible_knowledge` | Invisible Knowledge    | Architectural mental model for LLMs    |
| `milestone:M-XXX`     | Top of milestone       | What this specific milestone adds      |

Multiple diagrams per scope are allowed. First diagram in list with matching scope is primary.

### Architect-Owned Workflow

Diagrams are fully owned by the Architect at plan-design:

**Architect (plan-design-work):**

- Creates diagram_graphs with nodes and edges
- Validates semantic correctness: no orphan nodes, valid edge references
- Renders ASCII via `cli.plan set-diagram-render` and populates ascii_render
- Validates format: width, box alignment

The Architect owns both WHAT to communicate (graph structure) and HOW to communicate (visual rendering). No separate rendering step exists.

### ASCII Conventions

Diagrams render as fixed-width ASCII for universal portability (cat, vim, git diff, terminal):

```
+------------------+     +------------------+
| Component A      | --> | Component B      |
| (description)    |     | (description)    |
+------------------+     +------------------+
        |
        v
+------------------+
| Component C      |
+------------------+
```

Syntax:

- Box corners: `+`
- Horizontal edges: `-`
- Vertical edges: `|`
- Arrows: `v`, `^`, `<`, `>`, `-->`, `<--`
- Edge labels: inline on arrow or parenthetical

Target width: 80 chars max. Diagrams wider than terminal wrap and lose value.

### Skip Criteria

Not all plans need diagrams. Skip diagram generation if:

- Pure refactoring (no new components)
- Single-file changes
- Documentation-only milestones
- Overview lacks structural keywords (services, layers, flow, protocol)

When skipping, diagram_graphs remains empty. This is valid state.

### Documentation Workflow

**exec-docs (impl-docs phase)**:

1. Reads Decision Log and Invisible Knowledge from plan.json
2. Authors inline comments and docstrings directly in the real implemented source files
3. Creates CLAUDE.md and code-adjacent README.md files directly in the source tree

The developer writes no comments during implementation. exec-docs is the sole author of all documentation after impl-code QR passes.

## Mutation Ownership

**Planning phase (plan.json mutations):**

| File                | Step | Agent            | Mutation                                                                              |
| ------------------- | ---- | ---------------- | ------------------------------------------------------------------------------------- |
| plan.json           | 1    | orchestrator     | Create skeleton                                                                       |
| context.json        | 2    | orchestrator     | Create and freeze                                                                     |
| plan.json           | 3    | architect        | Add overview, milestones, code_intents (binding contract), decisions, diagram IR + ascii_render |
| qr-plan-design.json | 4    | quality-reviewer | Create items with status: TODO                                                        |
| qr-plan-design.json | 5    | quality-reviewer | Update individual item status to PASS/FAIL                                            |
| qr-plan-design.json | 6    | orchestrator     | Delete file (all PASS) → PLAN APPROVED                                                |

**Execution phase (source file mutations; plan.json not mutated):**

| Files              | Step | Agent            | Mutation                                                                              |
| ------------------ | ---- | ---------------- | ------------------------------------------------------------------------------------- |
| source files       | E2   | developer        | Implement code_intents JIT against current live files (no plan.json write)            |
| qr-impl-code.json  | E3   | quality-reviewer | Create items with status: TODO                                                        |
| qr-impl-code.json  | E4   | quality-reviewer | Update individual item status to PASS/FAIL                                            |
| qr-impl-code.json  | E5   | orchestrator     | Delete file (all PASS)                                                                |
| source files       | E6   | technical-writer | exec-docs authors inline comments, docstrings, CLAUDE.md, README.md directly in source |
| qr-impl-docs.json  | E7   | quality-reviewer | Create items with status: TODO                                                        |
| qr-impl-docs.json  | E8   | quality-reviewer | Update individual item status to PASS/FAIL                                            |
| qr-impl-docs.json  | E9   | orchestrator     | Delete file (all PASS)                                                                |

## Workflows

### Planning Workflow (orchestrator/planner.py)

6 steps. Transforms user request into an approved plan (the IR). The plan-code and plan-docs phases are eliminated; the plan is complete after plan-design QR passes.

The single QR-able phase (plan-design) follows a 4-step block pattern:

- Work step (1 sub-agent): Execute or fix based on state detection. Sub-agent validates written state before returning.
- QR decompose (1 sub-agent): Create verification items. Sub-agent validates qr-{phase}.json before returning.
- QR verify (N sub-agents): Parallel item verification via batched dispatch.
- QR route (orchestrator): Aggregate results, loop or proceed.

```
Step 1: plan-init
  Action: Create state_dir, write plan.json skeleton
  Next: Step 2

Step 2: context-verify
  Action: Capture context into context.json, self-verify completeness
  Checklist: goal statable in one sentence, at least one out-of-scope item,
             at least one constraint (or explicit "none"), entry points identified
  Next: Step 3

Step 3: plan-design-work
  Agent: architect
  Script: architect/plan_design.py (router)
  Routing: If qr-plan-design.json has FAIL items -> quality_reviewer/exec_qr_fix.py --phase plan-design
           Otherwise -> architect/plan_design_execute.py
  Output: plan.json with overview, milestones, code_intents (binding contract),
          decisions, diagram_graphs (IR + ascii_render)
  Validation: Sub-agent validates plan.json against schema before returning
  Next: Step 4

Step 4: plan-design-qr-decompose
  Agent: quality-reviewer
  Script: quality_reviewer/qr_decompose.py --phase plan-design
  Output: qr-plan-design.json with items (status: TODO)
  Output: parallel_dispatch block listing all --qr-item IDs
  Next: Step 5

Step 5: plan-design-qr-verify
  Agent: quality-reviewer (N parallel instances)
  Script: quality_reviewer/qr_verify.py --phase plan-design --qr-item {id}
  Input: Orchestrator script parses parallel_dispatch from step 4, batches items by group
  Output: Each agent verifies its batch, updates items in qr-plan-design.json to PASS/FAIL
  Next: Step 6

Step 6: plan-design-qr-route
  Action: Orchestrator script determines routing from qr-plan-design.json
  Route: All PASS -> delete qr file, PLAN APPROVED (terminal)
         Any FAIL -> loop to Step 3 (router will dispatch to qr_fix)
```

### Execution Workflow (orchestrator/executor.py)

12 steps. Implements the approved plan.

```
Step 1: exec-init
  Action: Analyze plan, build wave dependency graph

Step 2: impl-code-work
  Agent: developer (up to 4 parallel per wave)
  Script: developer/exec_implement.py (router)
  Routing: If qr-impl-code.json has FAIL items -> quality_reviewer/exec_qr_fix.py --phase impl-code
           Otherwise -> developer/exec_implement_execute.py
  Dispatch carries: files, acceptance_criteria, Code Intent (code_intents[]),
                    decision/IK context
  Output: code_intents implemented JIT against current live files (regenerated per wave)
  Next: Step 3

Step 3: impl-code-qr-decompose
  Agent: quality-reviewer
  Script: quality_reviewer/qr_decompose.py --phase impl-code
  Output: qr-impl-code.json with items (status: TODO)
  Output: parallel_dispatch block listing all --qr-item IDs
  Next: Step 4

Step 4: impl-code-qr-verify
  Agent: quality-reviewer (N parallel instances)
  Script: quality_reviewer/qr_verify.py --phase impl-code --qr-item {id}
  Output: Each agent updates one item in qr-impl-code.json to PASS/FAIL
  Next: Step 5

Step 5: impl-code-qr-route
  Route: All PASS -> delete qr file, proceed to Step 6
         Any FAIL -> loop to Step 2

Step 6: impl-docs-work
  Agent: technical-writer (exec-docs)
  Script: technical_writer/exec_docs.py (router)
  Routing: If qr-impl-docs.json has FAIL items -> quality_reviewer/exec_qr_fix.py --phase impl-docs
           Otherwise -> technical_writer/exec_docs_execute.py
  Output: All documentation authored directly in source: inline comments, docstrings
          (sourced from Decision Log + Invisible Knowledge), CLAUDE.md, README.md
  Next: Step 7

Step 7: impl-docs-qr-decompose
  Agent: quality-reviewer
  Script: quality_reviewer/qr_decompose.py --phase impl-docs
  Output: qr-impl-docs.json with items (status: TODO)
  Output: parallel_dispatch block listing all --qr-item IDs
  Next: Step 8

Step 8: impl-docs-qr-verify
  Agent: quality-reviewer (N parallel instances)
  Script: quality_reviewer/qr_verify.py --phase impl-docs --qr-item {id}
  Output: Each agent updates one item in qr-impl-docs.json to PASS/FAIL
  Next: Step 9

Step 9: impl-docs-qr-route
  Route: All PASS -> delete qr file, proceed to Step 10
         Any FAIL -> loop to Step 6

Step 10: final-verify
  Action: Run the full test suite + lint + type-check against the final code AND
          docs; record the three results to verify.json (cli/verify.py). Placed
          AFTER doc QR because exec-docs (Step 6) edits source comments/docstrings
          after the last code test, and Step 2's per-wave test runs are advisory.
  Next: Step 11

Step 11: final-verify-gate
  Route: All green -> Step 12 (retrospective)
         Any red   -> reset qr-impl-code/-docs.json (so the fix gets a FRESH
                      code+doc QR review, not a re-verify of stale PASS items) and
                      loop to Step 2 in verify-fix mode; the fix then re-runs code
                      QR -> docs -> doc QR -> final-verify
         Still red at QR_ITERATION_LIMIT -> escalate to user (accept -> Step 12, abort)
  Note: routing is deterministic on verify.json; the pass/fail VERDICT is
        LLM-asserted (cli/verify.py guardrails narrow but do not close that trust).

Step 12: retrospective
  Action: Present execution retrospective -> EXECUTION COMPLETE
          (waves loop within Step 2: all waves complete before Code QR)
```

## Script Organization

Scripts follow router-dispatch pattern. Each QR-able phase has:

- Router script: Detects state, dispatches to appropriate workflow
- Execute script: First-time execution workflow
- QR fix script: Post-QR failure fix workflow
- QR decompose script: Creates verification items
- QR verify script: Verifies single item (called with --qr-item)

```
skills/planner/
  orchestrator/
    planner.py       -- 6-step planning workflow
    executor.py      -- 12-step execution workflow
  architect/
    plan_design.py            -- router (detects state, dispatches)
    plan_design_execute.py    -- first execution (6 steps)
  developer/
    exec_implement.py         -- router
    exec_implement_execute.py -- implementation (4 steps)
  technical_writer/
    exec_docs.py              -- router
    exec_docs_execute.py      -- impl-docs (6 steps)
  quality_reviewer/
    qr_decompose.py             -- decompose runner (--phase {plan-design|impl-code|impl-docs})
    qr_verify.py                -- single-item verify runner (--phase ...)
    qr_verify_base.py           -- shared verification base + verify_main
    exec_qr_fix.py              -- unified post-QR fix runner (--phase {plan-design|impl-code|impl-docs})
    prompts/content.py          -- per-phase decompose prompts + verifier classes
    prompts/decompose.py        -- shared 13-step decompose flow
    prompts/fix.py              -- shared 3-step fix flow + per-phase fix content
  shared/
    schema.py         -- Pydantic v2 schemas (context, plan, qr), validation
    resources.py      -- Path helpers, resource provider
    constraints.py    -- Constraint builders
    gates.py          -- Gate output builder
    qr/               -- QR subsystem utilities
      utils.py        -- QR state loading, item extraction
```

## CLI Interface

All scripts accept a common set of arguments. QR-related state is file-based, not CLI-based.

**Universal arguments (all scripts):**

| Argument      | Required | Description                     |
| ------------- | -------- | ------------------------------- |
| `--step`      | Yes      | Current step number (1-indexed) |
| `--state-dir` | Yes\*    | Path to state directory         |

\*Step 1 of orchestrators creates state_dir; subsequent steps require it.

**QR verify arguments:**

| Argument    | Required | Description                                                                       |
| ----------- | -------- | -------------------------------------------------------------------------------- |
| `--phase`   | Yes      | QR phase: `plan-design` \| `impl-code` \| `impl-docs` (selects verifier + qr file) |
| `--qr-item` | Yes      | Item ID to verify; repeatable for a batched agent (`--qr-item qa-001 --qr-item qa-002`) |

`--phase` makes the verify runner phase-parameterized. Repeated `--qr-item` flags assign a batch of related items to one agent (parallel dispatch = one batch per agent); there is no comma-joined `--qr-items` flag.

**Gate step arguments:**

| Argument      | Required | Description                                          |
| ------------- | -------- | ---------------------------------------------------- |
| `--qr-status` | Yes      | Aggregated verdict from verify agents: "pass"/"fail" |

**Explicitly forbidden arguments:**

| Argument         | Why forbidden                                      |
| ---------------- | -------------------------------------------------- |
| `--qr-fail`      | QR file path is computable from state_dir + phase  |
| `--qr-iteration` | Iteration is stored in qr-{phase}.json, not passed |

The orchestrator never passes failure paths or iteration counts. Routers and fix scripts read this information from qr-{phase}.json directly.

## Invariants

**Sub-agents cannot launch sub-agents**. Only orchestrator dispatches. Maintains audit trail, prevents hidden dependencies.

**Sub-agents cannot invoke AskUserQuestion**. Sub-agents that need user input yield with `<needs_user_input>` XML. Orchestrator relays question, then reinvokes sub-agent fresh with answer. Sub-agents cannot be resumed; they must be reinvoked with context restored from state files.

**Orchestrator LLM never reads/writes state files**. The orchestrator LLM agent must not use Read(), Write(), or Edit() tools on state files (plan.json, context.json, qr-{phase}.json). Context flows through dispatch prompts. State files are sub-agent territory.

Note: The orchestrator Python script (planner.py, executor.py) may read state files internally for reliable orchestration -- e.g., `load_qr_state()` to determine which QR items remain for dispatch. This is implementation machinery invisible to the LLM. The invariant applies to the LLM agent, not the Python code that generates prompts.

**Orchestrator is a dumb dispatcher**. The orchestrator routes based on status flags (pass/fail) and step numbers. It never makes quality judgments ("the plan looks comprehensive"), never decides to "proceed anyway" when protocol requires iteration, and never skips steps based on subjective assessment. If a sub-agent returns invalid output or the workflow requires iteration, the orchestrator follows the protocol mechanically.

**Sub-agent self-validation**. Every sub-agent that writes to state files (plan.json, qr-{phase}.json) must validate the written file before returning to orchestrator. The final step of any state-mutating workflow:

1. Loads the file just written
2. Validates against Pydantic schema via `validate_state()`
3. If invalid: fixes in-place, re-validates, loops until valid
4. If valid: formats final output and returns

The orchestrator must never see schema validation errors. Philosophy: detect problems IMMEDIATELY after they happen, at the source. Validation failures are sub-agent bugs to be fixed before handoff, not orchestrator concerns.

This applies to both execute and fix workflows. After the architect writes plan.json, it validates. After the QR fix agent updates plan.json, it validates. The orchestrator receives only valid state.

**User authority is absolute**. Agent findings may be wrong. User decisions override everything.

**Always run scripts**. Every step invokes a Python script. No free-form execution. Scripts emit prompts; LLM performs work. Router scripts dispatch to workflow scripts; this is still script-based execution.

**Router dispatch at step 1 only**. Router scripts detect state (qr-{phase}.json existence and contents) at step 1 and dispatch to the appropriate workflow script. Subsequent steps within a workflow script MUST NOT dispatch to other scripts.

**State detection over flags**. Work scripts detect their mode from state file presence, not from CLI flags. If qr-{phase}.json exists and has FAIL items, the router dispatches to the fix workflow. Orchestrator dispatches to the same step number regardless of mode.

**No distributed QR state**. All QR state lives in qr-{phase}.json. CLI flags for QR fail path (--qr-fail) and iteration count (--qr-iteration) MUST NOT exist. The decompose step reads/increments iteration from file; routers compute qr file path from state_dir + phase. Only --qr-status (orchestrator's aggregated verdict) and --qr-item (verify agent's assigned item) are valid QR-related CLI args.

**Adaptive item generation**. Decomposition creates as many items as the content requires. No fixed counts or caps. The 8-step workflow naturally terminates when structural enumeration is exhausted and coverage is validated. Item count varies by plan complexity.

**Call-site enumeration for pass-through helpers**. When a Code Intent modifies a pass-through, transform, filter, or gate function, the architect must enumerate every call site in the plan before the plan-design QR phase. A pass-through helper is any function where the same defect pattern at one call site replicates at others (URL rewriters, auth checks, validators, allowlist primitives, data mappers, sanitizers). QR decompose must verify completeness; missing call sites are MUST-severity findings.

**Blast-radius claims verified against gating primitives**. When a plan claims that certain code paths or actors are unaffected ("all production writers are safe", "only affects X"), the claim must be anchored to the actual gating function and its allowlist/guard logic — not assumed. A claim about what passes through a gate is unverifiable without quoting the gate. QR verify must treat unverified blast-radius claims as MUST-severity findings.

**QR decompose output contract**. Decompose scripts MUST output a `<parallel_dispatch>` block that orchestrator parses to launch N verify agents. Dispatch blocks are generated via the AST module at `lib/workflow/ast/` using three node types:

- `SubagentDispatchNode`: Single agent dispatch (sequential workflows)
- `TemplateDispatchNode`: Parallel dispatch with parameterized template (SIMD pattern)
- `RosterDispatchNode`: Parallel dispatch with unique prompts (MIMD pattern)

Rendered format:

```xml
<parallel_dispatch agent="quality-reviewer" count="N">
  <groups>
    <group id="component-auth" items="qa-001,qa-002,qa-003">Auth component checks</group>
    <group id="umbrella" items="qa-010,qa-011">Cross-cutting checks</group>
  </groups>
  <template>
    <invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.planner.quality_reviewer.qr_verify --step 1 --phase {phase} --state-dir {state_dir} $qr_item_flags" />
  </template>
</parallel_dispatch>
```

**QR file lifecycle**. qr-{phase}.json is created by decompose step, updated by verify agents, deleted by route step on PASS. The file's existence signals "QR in progress"; its absence signals "no QR done yet" or "QR passed and cleaned up".

**QR iteration limit**. Maximum 5 iterations (`QR_ITERATION_LIMIT`) per QR phase, enforced at the gate: once the limit is reached with blocking findings still open, the gate escalates to the user (accept-as-is or abort) instead of looping again. Blocking scope narrows by iteration via progressive de-escalation (iterations 1–2: MUST + SHOULD + COULD; iteration 3: MUST + SHOULD; iteration 4+: MUST only). MUST never de-escalates, which is exactly why the enforced ceiling exists — an unfixable MUST would otherwise loop forever.

## QR Workflow

Each QR block consists of 4 orchestrator steps:

**Decompose step (1 sub-agent):**

```
uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.quality_reviewer.qr_decompose --step 1 --phase <phase> --state-dir {state_dir}
```

Sub-agent explores the artifact being reviewed using an 8-step cognitive workflow, generates verification items adaptively (quantity determined by content, not preset bounds), writes qr-{phase}.json with all items status: TODO. Outputs parallel_dispatch block for orchestrator to parse.

### 8-Step Decomposition Workflow

The decomposition follows a top-down-then-bottom-up approach to generate verification items. Holistic brainstorming captures cross-cutting concerns that structural enumeration misses (overall approach validity, implicit requirements, integration risks). Structural enumeration then serves as completeness validation, not the generative source.

**Step 1: Absorb Context**
Read plan.json and context.json. Summarize understanding in 2-3 sentences. Establishes what the plan accomplishes and what success looks like for this phase. No items generated yet.

**Step 2: Holistic Concerns (Top-Down)**
Brainstorm freely: "If reviewing this phase output, what would I check?" Captures high-level validity, cross-cutting patterns, quality aspects, and risks. Output is an unfiltered bulleted list of concerns. This step identifies what structural enumeration cannot see.

**Step 3: Structural Enumeration (Bottom-Up)**
List what EXISTS in the plan for this phase. Phase-specific: decisions/constraints/risks/code_intents for plan-design, acceptance_criteria/code_intents for impl-code. Output is a structured enumeration with IDs and counts. This becomes the completeness checklist in Step 7.

**Step 4: Gap Analysis**
Compare Step 2 concerns vs Step 3 elements. Identify which concerns need umbrella items (cross-cutting), which map to specific elements, which elements need targeted items, and gaps in both directions.

**Step 5: Generate Initial Items**
Create items using the umbrella + specific pattern. Critical concerns get BOTH a broad catch-all item (scope: "\*") AND specific targeted items (scope: element reference). This intentional overlap ensures outliers are caught by umbrellas while known-critical aspects get explicit verification. Overlapping coverage is acceptable; gaps are not. No fixed item counts -- generate what the content requires.

**Step 6: Atomicity Check**
Review each item: tests exactly one thing? An item is ATOMIC if pass/fail is unambiguous and it cannot be "half passed". Non-atomic items are acceptable as umbrellas if they catch outliers.

Split criteria: Only split if the item is BOTH non-atomic AND critical. Critical determination:

- Related to MUST-severity concerns: knowledge loss, production reliability
- Architectural decisions in planning_context
- Cross-cutting error handling or security
- Public API contract changes

Non-critical concerns (internal implementation details, formatting, optimizations) remain as umbrellas for broader coverage.

When splitting: create specific items AND keep the umbrella.

**Step 7: Coverage Validation**
Use Step 3 enumeration as checklist. For each element: at least one covering item? For each concern: at least one addressing item? If uncertain, ADD an item. Overlap is preferred over gaps.

**Step 8: Finalize and Write**
Write qr-{phase}.json with final items. Output parallel_dispatch block. Item count is whatever emerged from the process -- no targets, no caps. Content determines quantity.

### Adaptive Item Generation

The workflow produces variable item counts based on plan complexity. Simple phases with few decisions and straightforward code_intents yield fewer items. Complex phases with many architectural decisions, cross-cutting concerns, and intricate code patterns yield more items.

The 8-step workflow provides natural termination without artificial bounds:

- Step 3 bounds items to what actually exists in the plan
- Step 7 terminates when the checklist is complete
- Umbrella items cover multiple concerns without 1:1 expansion

More items with overlap is preferred over fewer items with gaps.

**Verify step (N sub-agents, parallel):**

```
uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.quality_reviewer.qr_verify --step 1 --phase <phase> --state-dir {state_dir} --qr-item qa-001 --qr-item qa-002
```

Each sub-agent receives a batch of semantically related items to verify. Items are grouped by the decompose step (e.g., by component, by concern, or parent-child relationships). The agent reads the qr file, verifies each assigned item, and updates status to PASS or FAIL with finding.

**Output contract**: a verify agent's entire final response is one bare word -- `PASS` if
every item it was assigned passed, `FAIL` if any failed. Per-item findings are recorded in
qr-{phase}.json through the script's `--result PASS|FAIL --finding <text>` flag, not in the
returned text.

The orchestrator tallies these words mechanically (see `build_qr_verify_dispatch`): all PASS
-> `--qr-status pass`, any FAIL -> `--qr-status fail`. Malformed output is treated as FAIL.

**Route step (orchestrator only):**

The orchestrator script (not the LLM) reads qr-{phase}.json after all verify agents complete and checks the loaded state for remaining blocking failures:

```python
def has_qr_failures_from_state(qr_state: dict) -> bool:
    """True if the loaded qr_state still has blocking FAIL items."""
```

The script determines the routing and generates the appropriate prompt for the LLM. The LLM sees only the routing decision, not the file contents.

If no failures: delete qr file, proceed to next block.
If failures exist: loop back to work step. The work step's router will detect qr-{phase}.json with FAIL items and dispatch to the fix workflow.

**Fix workflow (via router):**

When orchestrator loops back to work step (e.g., step 3), the router script:

1. Checks for qr-{phase}.json
2. If exists with FAIL items -> dispatch to {phase}\_qr_fix.py
3. Fix script loads failed items, guides agent to fix issues
4. Agent validates state file after fixes (same self-validation requirement as execute workflow)
5. After fixes and validation, workflow continues to decompose step (fresh QR)

## Context Handover

Context is lost when orchestrator launches a sub-agent. The dispatch prompt must include all necessary context. Sub-agent reads state files for full detail.

Context categories for dispatch:

- Task Specification: what we're building, scope, out-of-scope
- Constraints: MUST/SHOULD/MUST-NOT
- Entry Points: where to start exploring
- Rejected Alternatives: what was dismissed and why
- Assumptions: inferences not verified
- Invisible Knowledge: rationale, invariants, tradeoffs
- User Quotes: verbatim user statements, especially corrections

Handover prompts should be concise. Initial handover (step 2->3) includes full detail. Subsequent handovers can be terse since sub-agents read state files.

**CLI mutation commands in prompts**: Sub-agents that mutate state files must have the relevant CLI commands surfaced in their prompts. The agent cannot use tools it doesn't know about. Scripts emit CLI usage examples as part of the prompt:

| Sub-agent | CLI commands to surface                                                              |
| --------- | ------------------------------------------------------------------------------------ |
| architect | `cli.plan set-milestone`, `set-intent`, `set-decision`, `set-diagram`,               |
|           | `add-diagram-node`, `add-diagram-edge`, `set-diagram-render`, `set-wave`             |
| qr-verify | `cli.qr update-item`                                                                 |

Example prompt fragment for architect:

```
State Mutation:
  uv run --project "${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts" python -m skills.planner.cli.plan --state-dir {state_dir} set-intent \
      --milestone M-001 --file path.py --behavior "description"
```

## Question Relay

When sub-agent needs user input:

1. Sub-agent saves state to plan.json
2. Sub-agent emits `<needs_user_input>` XML and stops
3. Orchestrator detects XML, extracts questions
4. Orchestrator calls AskUserQuestion
5. User responds
6. Orchestrator reinvokes sub-agent fresh with accumulated Q&A history in an extra prompt field
7. New sub-agent reads plan.json, continues with user's answers

On reinvocation, answers are provided in a `<user_response>` block:

```xml
<user_response>
  <answer header="Auth">JWT with refresh tokens</answer>
  <answer header="Scope">Not in initial implementation</answer>
</user_response>
```

Sub-agents cannot be resumed. They must be reinvoked fresh with explicit state file reading.
