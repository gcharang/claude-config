# Planner

Planning and execution workflows with QR (Quality Review) gates, TW (Technical Writer) passes, and Dev (Developer) execution phases.

This document is authoritative for the planner skill architecture.

## Architecture: Python Scripts vs LLM

Python scripts emit workflow prompts and routing. The LLM operates BETWEEN script invocations:

1. Script outputs prompt/guidance for current step
2. LLM reads prompt, performs reasoning/assessment
3. LLM decides outcome (e.g., QR PASS/FAIL)
4. LLM invokes next script based on outcome

QR PASS/FAIL is determined by LLM reading QR output, not Python. Gate routing is LLM's decision based on QR outcome. Python scripts provide structure; LLM provides intelligence.

## State Files

All state mutations (except initial context.json) happen via Python CLI commands. The state directory is created by `shared/resources.py::resolve_state_dir()`, anchored on `$CLAUDE_PROJECT_DIR` then the working directory: project-local and git-ignored (`<project>/.agent-state/_runs/{planner,executor}/<UTC-stamp>-<rand>/`) when that resolves to a repo whose `.agent-state` is ignorable, is not already tracked there, and whose minted run directory git confirms as ignored, else a per-session temp path (`<tmpdir>/cc-<session>/{planner,executor}-<rand>/`), with the reason on stderr. Step 1 records the resolved project in the state dir; later steps read it back rather than re-deriving it from a working directory that is no longer the project's. Old run dirs are pruned once they are both surplus and stale. Nothing is created at a top-level `/tmp/{planner,executor}-*` -- that flat namespace is shared by every session on the machine, so one session's cleanup glob deleted another's in-flight plan. See `skills/planner/INTENT.md` for the full contract.

| File              | Schema         | Created     | Mutated By     | Lifecycle              |
| ----------------- | -------------- | ----------- | -------------- | ---------------------- |
| `plan.json`       | Pydantic v2    | Step 1 init | CLI commands   | mutable                |
| `context.json`    | Loose JSON     | Step 2      | LLM Write tool | frozen after step 2    |
| `qr-{phase}.json` | QA item schema | QR dispatch | LLM during QR  | ephemeral per QR cycle |
| `verify.json`     | Pydantic v2    | Step 10     | `cli/verify.py`| suite/lint/type record |
| `project_root`    | Absolute path  | Step 1, every route | `ensure_project_root_recorded` | written when absent; content this planner provably did not write is replaced; anything else, including a marker naming another project, is kept |

### plan.json Schema

```
Plan
  plan_id: UUID                      (auto)
  created_at: ISO-8601 timestamp     (auto)

  overview:
    problem, approach

  planning_context:
    decisions[] (input alias: decision_log): id (DL-XXX), version, decision, reasoning   (reasoning <- reasoning_chain)
    rejected_alternatives[]: id (RA-XXX), alternative, rejection_reason, decision_ref
    constraints[]: plain strings (no IDs/types)
    risks[]: id (R-XXX), risk, mitigation, anchor?, decision_ref?   (input alias: known_risks)

  invisible_knowledge:
    system, invariants[], tradeoffs[]   (diagrams live in diagram_graphs, not here)

  milestones[]:
    id (M-XXX), version, number, name, files[], flags[], requirements[], acceptance_criteria[]
    tests[]: flat list of free-form descriptions
    code_intents[]: id (CI-XXX), version, file, function?, behavior, decision_refs[]
    is_documentation_only, delegated_to?

  waves[]: id (W-XXX), milestones[]   (top-level; no separate milestone_dependencies block)
  diagram_graphs[]: id (DIAG-XXX), type, scope, title, nodes[], edges[], ascii_render?
```

Reference integrity: code_intent.decision_refs -> decisions[].id.
Authoritative schema: `resources/plan-json-schema.md` (mirrors `shared/schema.py`).
No `schema_version` field -- state files are ephemeral (one planning session).

### context.json Schema

User-provided context captured during planning:

```json
{
  "task_spec": ["goal", "scope", "out-of-scope"],
  "constraints": ["MUST: X", "SHOULD: Y"],
  "entry_points": ["file:function - why"],
  "rejected_alternatives": ["alternative - why dismissed"],
  "current_understanding": ["how system works"],
  "assumptions": ["inference (confidence)"],
  "invisible_knowledge": ["design rationale", "invariants"],
  "user_quotes": ["verbatim quote"]
}
```

### qr-{phase}.json Schema

Phases: `qr-plan-design`, `qr-impl-code`, `qr-impl-docs`

```json
{
  "phase": "plan-design",
  "iteration": 1,
  "items": [
    {
      "id": "qa-001",
      "scope": "*",
      "check": "...",
      "status": "TODO|PASS|FAIL",
      "finding": null
    }
  ]
}
```

## Workflow Phases and Mutations

### Planner Workflow (6 steps)

| Step | Name                    | Pattern Function          | Mutates              | Agent        |
| ---- | ----------------------- | ------------------------- | -------------------- | ------------ |
| 1    | plan-init               | `init_step()` (renders; `main()` mints the state dir and writes the skeleton) | Creates plan.json    | Orchestrator |
| 2    | context-verify          | `verify_step()`           | Creates context.json | Orchestrator |
| 3    | plan-design-work        | `execute_dispatch_step()` | plan.json            | Architect    |
| 4    | plan-design-qr-decompose| `qr_decompose_step()`     | qr-plan-design.json  | QR           |
| 5    | plan-design-qr-verify   | `qr_verify_step()`        | qr-plan-design.json  | QR           |
| 6    | plan-design-qr-route    | `qr_route_step()`         | Renders plan.md (PASS) | Orchestrator |

Terminal on PASS at step 6: **PLAN APPROVED**.

**Mutation details**:

- Step 3 (Architect): Populates planning_context, milestones[], code_intents[], invisible_knowledge, renders diagram ASCII via `cli.plan set-diagram-render`

Code Intent (`code_intents[]`) is the binding behavioral contract. There are no plan-time unified diffs. At execution the developer regenerates implementation just-in-time per wave against the live file from Code Intent.

### Executor Workflow (12 steps)

| Step | Name                   | Mutates            | Agent              |
| ---- | ---------------------- | ------------------ | ------------------ |
| 1    | exec-init (analyze plan, transcribe waves) | Creates plan.json | Orchestrator |
| 2    | impl-code-work (wave-aware; verify-fix mode on a verify failure) | Codebase files | Developer |
| 3    | impl-code-qr-decompose | qr-impl-code.json  | QR                 |
| 4    | impl-code-qr-verify    | qr-impl-code.json  | QR                 |
| 5    | impl-code-qr-gate      | -                  | Orchestrator       |
| 6    | impl-docs-work         | Codebase docs      | TW                 |
| 7    | impl-docs-qr-decompose | qr-impl-docs.json  | QR                 |
| 8    | impl-docs-qr-verify    | qr-impl-docs.json  | QR                 |
| 9    | impl-docs-qr-gate      | -                  | Orchestrator       |
| 10   | final-verify (run full suite/lint/type) | verify.json | Orchestrator (LLM runs commands) |
| 11   | final-verify-gate (green -> retro; red -> reset QR + step 2; ceiling -> user) | resets qr-*.json on fail | Orchestrator |
| 12   | retrospective          | -                  | Orchestrator       |

impl-code QR is the single authoritative code review. exec-docs (impl-docs phase) authors ALL documentation directly in the real implemented source (inline comments, docstrings from Decision Log + Invisible Knowledge, plus CLAUDE.md and README).

**Final Verification gate** (steps 10-11): exec-docs (step 6) edits source comments
after the last code test, and the per-wave test runs in step 2 are advisory prose,
so the executor ends with a hard gate. Step 10 runs the full suite/lint/type and
records `verify.json` via `cli/verify.py` (the LLM types the verdict, so the gate
narrows but does not eliminate that trust -- see the consistency guardrails there).
Step 11 routes deterministically: all green -> retrospective; any red -> reset the
QR state (so the fix gets a FRESH code+doc QR review, not a re-verify of stale
PASS items) and route to step 2 verify-fix mode; still red after `QR_ITERATION_LIMIT`
cycles -> escalate to the user. A red suite/lint/type cannot reach the retrospective
on its own.

## Components

```
orchestrator/
  planner.py      6-step planning workflow
  executor.py     12-step execution workflow (adds final-verify run + gate)

architect/
  plan_design.py  Plan creation (exploration, milestones, code_intents, diagram render)

developer/
  exec_implement.py  Wave-aware implementation (just-in-time from code_intents)

technical_writer/
  exec_docs.py    Post-implementation docs (inline comments, docstrings, CLAUDE.md, README)

quality_reviewer/
  qr_decompose.py              QR decompose runner (--phase plan-design|impl-code|impl-docs)
  qr_verify.py                 QR verify runner (--phase ...)
  qr_verify_base.py            VerifyBase ABC + verify_main
  prompts/content.py           Per-phase decompose prompts + verifier classes
  prompts/decompose.py         Shared 13-step decompose flow (dispatch_step)

shared/
  resources.py    Conventions, script paths, state dir validation + placement
  builders.py     XML output builders
  constraints.py  Orchestrator constraint AST builders
  schema.py       Pydantic v2 schemas + defaults for plan.json / context.json / qr state
  qr/             QR utilities (types, constants, utils, schema)

cli/
  plan.py         plan.json manipulation commands
  qr.py           qr-{phase}.json item mutation (parallel-safe, file-locked)
  verify.py       verify.json recorder (final suite/lint/type results)
```

## QR Gate Mechanics

QR gates use LoopState enum: INITIAL -> RETRY -> COMPLETE

```
INITIAL -> PASS -> COMPLETE (terminal)
INITIAL -> FAIL -> RETRY (iteration++)
RETRY   -> FAIL -> RETRY (iteration++)
RETRY   -> PASS -> COMPLETE (terminal)
```

Blocking severity by iteration:

| Iteration | Blocks              |
| --------- | ------------------- |
| 1-2       | MUST, SHOULD, COULD |
| 3         | MUST, SHOULD        |
| 4+        | MUST only           |

Each orchestrator runs QR as a 4-step block per phase — work → decompose → verify
(N parallel) → gate. The planner has one QR phase (plan-design); the executor has
two (impl-code, impl-docs).

## Step Handler Architecture

Closures capture static config, handlers receive dynamic state:

```python
def execute_dispatch_step(title, agent, script, ...):
    def handler(ctx):  # Receives state_dir, qr, qr_fail
        return {"title": ..., "actions": ..., "next": ...}
    return handler

STEPS = {
    1: init_step("plan-init", ...),
    3: execute_dispatch_step("plan-design-work", agent="architect", ...),
    4: qr_decompose_step("plan-design-qr-decompose", ...),
    5: qr_verify_step("plan-design-qr-verify", ...),
    6: qr_route_step("plan-design-qr-route", ...),
}
```

## Design Decisions

**Closure-based step dispatch**: STEPS dict maps step numbers to handler closures. Pattern functions capture static config (title, agent, script), handlers receive dynamic state via ctx. Replaces magic keys with explicit patterns.

**Convention-based paths**: Sub-agents receive --state-dir, derive file paths via get_context_path(). Changing context.json location requires only updating resources.py.

**LLM-managed state**: State files written by LLM agents reading step guidance, not Python scripts. Leverages LLM capabilities for understanding context and following formats.

**JSON-IR-First**: plan.json is authoritative; plan.md derived from it.

**QR iteration blocking**: Severity thresholds vary by iteration. Early iterations block all severities. Later iterations block only MUST to prevent infinite loops.

**Run-dir retention**: the project-local branch reaps its own `_runs/<kind>/` -- a run
dir is removed only once it is BOTH surplus beyond `RUNS_KEEP_NEWEST` and idle past
`RUNS_MAX_AGE_DAYS`, and a run whose subtree cannot be examined in full is left alone.
The temp fallback is left to the OS.

**Fix-mode routing**: routers call `route_work_phase()` (`shared/routing.py`) to detect fix
mode from `qr-{phase}.json` state — no `--qr-fail` flag is threaded.

## Invariants

1. Every skill entry point defines exactly ONE Workflow
2. discover_workflows() finds all Workflows without import errors
3. plan.json is self-contained for execution
4. qr-{phase}.json files are ephemeral (exist only during QR cycle)
5. QR iteration blocking: iter 1-2 all; iter 3 MUST/SHOULD; iter 4+ MUST only
