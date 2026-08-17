# claude-config — a plan-then-execute workflow for Claude Code

*Deterministic scaffolding and quality-gate loops that let even smaller, cheaper models ship large features.*

This repository is a suite of Claude Code skills built around one centerpiece: a **planner** that
splits every non-trivial feature into two phases — **planning** and **execution** — run in separate
context windows and driven by a deterministic Python orchestrator. Specialised agents (architect,
developer, quality reviewer, technical writer, debugger) work in review loops behind hard quality
gates. Because the orchestrator carries the control-flow burden and the plan encodes binding,
machine-checkable contracts, the model at each step only has to solve one small, well-specified
problem at a time.

The premise: LLM-assisted code rots faster than hand-written code. Technical debt accumulates
because the LLM does not know what it does not know, and neither do you until it is too late. This
repo treats that as an engineering problem — force planning before execution, keep context focused,
and catch mistakes before they compound.

## The Planner Workflow

The planner is the spine of this repo. It runs in **two phases across two context windows**. You
`/clear` between them, so the *plan file* — not the transcript — carries the reasoning forward.
The orchestrator itself is a dumb dispatcher: it routes on status flags and step numbers and never
makes quality judgments. Intelligence lives in the sub-agents; structure lives in Python.

### Phase 1 — Planning (6 steps)

Driven by `skills/scripts/skills/planner/orchestrator/planner.py`. It turns an ambiguous request
into an approved, machine-checkable plan:

`plan-init` → `context-verify` (capture and freeze user context) → `plan-design-work` (the
**Architect** authors the overview, milestones, `code_intents[]`, decisions, risks, and diagram
IR) → `qr-decompose` (a **Quality Reviewer** breaks the plan into verification items) →
`qr-verify` (N parallel Quality Reviewers verify their items) → `qr-route`.

All items PASS ⇒ **PLAN APPROVED** and a human-readable `plan.md` is rendered. Any FAIL ⇒ loop
back into the design step in fix mode.

### Phase 2 — Execution (12 steps)

Driven by `skills/scripts/skills/planner/orchestrator/executor.py`. It implements the approved
plan against the live codebase:

`exec-init` (build the wave dependency graph) → `impl-code-work` (**Developer** agents implement
the `code_intents` just-in-time against the live files, dispatched in parallel per wave) →
`impl-code-qr` (decompose → verify → gate) → `impl-docs-work` (the **Technical Writer** authors
docs from the decision log) → `impl-docs-qr` → `final-verify` (run the full test suite, lint, and
type-check → `verify.json`) → `final-verify-gate` (deterministic; a red suite loops back to code
fix, and the iteration ceiling escalates to you) → `retrospective`.

### The specialised agents

Definitions live in `agents/`. Model tiers are configurable per agent.

| Agent            | Role                                                    | Default tier   |
| ---------------- | ------------------------------------------------------- | -------------- |
| Architect        | Turns ambiguous requests into unambiguous plans         | opus, xhigh    |
| Developer        | Implements code intents just-in-time; writes no prose   | sonnet, xhigh  |
| Quality Reviewer | Decomposes and verifies plans and code for defects      | opus, xhigh    |
| Technical Writer | Authors documentation after code passes review          | sonnet, medium |
| Debugger         | Systematic root-cause analysis                          | sonnet, xhigh  |

### The gates and loops

Every review-able phase is a four-step block: **work → decompose → verify (N parallel) →
route/gate**. Decomposition runs exactly once per phase, so verification aims at a fixed target
rather than a moving one. Findings carry a MoSCoW severity (MUST / SHOULD / COULD).

Termination is guaranteed by two mechanisms working together: severity **de-escalates** across
iterations (later rounds only block on MUST), and a hard ceiling (`QR_ITERATION_LIMIT = 5`) stops
runaway loops — at the ceiling with a blocking finding still open, the gate escalates to you rather
than looping forever.

## Why smaller, cheaper models can build large features

The workflow is model-agnostic. Its point is that a capable-but-cheaper model — say, a
DeepSeek-class model, cited here as an *example of the general principle* — can drive large features
it would fail at if asked in a single open-ended prompt. Six mechanisms make that possible:

1. **Cost-tiered delegation** — expensive models are reserved for genuine ambiguity (architecture,
   review); routine implementation runs on cheaper tiers.
2. **Decomposition** — features break into milestones, execution waves, and atomic `code_intents`,
   so no single step exceeds a small model's reliable working set.
3. **Structured contracts** — binding `code_intents[]` carry `decision_refs`, acceptance criteria,
   tests, risks, and diagrams. The model implements a contract instead of reasoning open-endedly.
4. **Context hygiene / just-in-time prompting** — each agent starts fresh and gets exactly the
   guidance it needs, nothing more.
5. **A deterministic orchestrator** — control flow, sequencing, and routing live in Python, not in
   the model's head.
6. **Mechanical error-catching** — Pydantic self-validation, file-locking, and multi-gate
   quality-review loops catch model mistakes without relying on the model to notice them.

The hard thinking (architecture, tradeoffs, decisions) is front-loaded onto the planning phase; the
cheaper model in execution only has to faithfully implement a fully-specified, machine-checked step
at a time.

> The agent definitions currently name Anthropic model tiers (Haiku / Sonnet / Opus); the
> smaller-model claim is a design property of the scaffolding, not a benchmarked result.

## Principles

The workflow rests on four principles.

### Context Hygiene

Each task gets precisely the information it needs — no more. Sub-agents start with a fresh context,
so architectural knowledge must be encoded somewhere persistent. Larger context windows do not
help: giving an LLM more text is like giving a human a larger stack of papers — attention drifts to
the beginning and end, and details in the middle get missed.

The repo uses a two-file pattern in every directory:

- **CLAUDE.md** — loaded automatically on entering a directory. Because it loads whether needed or
  not, it stays minimal: a tabular index with short descriptions and triggers for when to open each
  file.
- **README.md** — invisible knowledge: architecture decisions and invariants not apparent from the
  code. The test: if a developer could learn it by reading source, it does not belong here.

The technical-writer agent enforces token budgets (~200 tokens for CLAUDE.md, ~500 for README.md,
100 for function docs, 150 for module docs). The limits force discipline — exceed them and you are
probably documenting what the code already shows. The planner maintains this hierarchy
automatically; bypass the planner and you maintain it yourself.

### Planning Before Execution

LLMs make first-shot mistakes. Always. Separating planning from execution forces ambiguities to
surface when they are cheap to fix. Plans capture why decisions were made, what alternatives were
rejected, and what risks were accepted — written to files, so when context is cleared the reasoning
survives.

### Review Cycles

Execution is split into milestones — smaller units that can be validated individually. Without
this, execution becomes a waterfall: one small early oversight and agents compound each mistake
until the result is unusable. Quality gates run at every stage; the loop runs until they pass. Plans
pass review before execution begins, and each milestone passes review before the next starts.

### Cost-Effective Delegation

The orchestrator delegates to smaller agents — cheaper tiers for straightforward and
moderate-complexity work — and injects prompts just-in-time, giving those models precisely the
guidance they need at each step. When quality review keeps failing, the orchestrator stops
at the iteration ceiling and escalates to you, not to a larger model.

## Quick Start

Clone into your Claude Code configuration directory:

```bash
# Per-project
git clone https://github.com/gcharang/claude-config .claude

# Global (new setup)
git clone https://github.com/gcharang/claude-config ~/.claude

# Global (existing ~/.claude)
cd ~/.claude
git remote add workflow https://github.com/gcharang/claude-config
git fetch workflow
git merge workflow/main --allow-unrelated-histories
```

## Usage

The workflow for non-trivial changes: explore → plan → execute.

**1. Explore the problem.** Understand what you are dealing with and figure out the solution. This
is free-form. If the surface area is large, use the `codebase-analysis` skill to explore the
project properly before proposing a solution.

**2. (Optional) Think it through.** `deepthink` handles analytical questions where the answer's
shape is not yet known — taxonomy design, trade-offs, definitional questions, evaluative judgments.
It auto-detects complexity: quick mode reasons directly; full mode launches parallel sub-agents with
different analytical perspectives, then synthesizes. For narrowly scoped questions, reach for
`problem-analysis` (root-cause analysis) or `decision-critic` (stress-testing a specific decision).

**3. Write a plan.** "Use your planner skill to write a plan to plans/my-feature.md" — the planner
runs it through review cycles until it passes, capturing all decisions, tradeoffs, and information
not visible from the code.

**4. Clear context.** `/clear` — start fresh. Everything needed is in the plan.

**5. Execute.** "Use your planner skill to execute plans/my-feature.md" — the planner delegates to
sub-agents and never writes code directly. Each milestone passes the developer, then the technical
writer and quality reviewer, before the next begins. Where possible, work runs in parallel.

For detailed breakdowns of each skill, see their READMEs:

- [DeepThink](skills/deepthink/README.md)
- [Codebase Analysis](skills/codebase-analysis/README.md)
- [Problem Analysis](skills/problem-analysis/README.md)
- [Decision Critic](skills/decision-critic/README.md)
- [Planner](skills/planner/README.md)

## In Practice: a worked example

Consider migrating a legacy C# Windows Service from print-based logging to something that rotates
files. The codebase has a homegrown `Log()` method writing to a single file with
`File.AppendAllText` — no rotation, no log levels, synchronous I/O blocking the thread — plus six
`Console.WriteLine` calls that go nowhere when running as a service.

Start with exploration and analysis in a single prompt:

```
Use your codebase analysis skill to briefly explore this C# project,
with a focus on all the places where debug logs are currently emitted.

Then use your problem analysis skill to think through an appropriate
logging framework:
 * must work with .NET Framework 4.8.1
 * must support log rotation out of the box
 * we run multiple processes on the same machine, so it needs structured
   multi-process support
```

The codebase analysis finds the call sites and the `Console.WriteLine` leakage. The problem
analysis evaluates NLog, Serilog, log4net, and Microsoft.Extensions.Logging against the
constraints, and recommends NLog — rotation and async out of the box, multi-process support via
layout variables, where Serilog would need three packages for the same functionality.

With the recommendation accepted, move to planning:

```
Use your planner skill to write an implementation plan to: plan-logging.md
```

The planner surfaces ambiguities a human would gloss over — replace all `Log()` call sites or just
the implementation? which rotation defaults? — and the plan goes through review. The technical
writer flags comments that explain *what* rather than *why*. The quality reviewer catches two
issues easy to miss: no explicit `LogManager.Shutdown()` in the service's `OnStop()` handler, and
file paths missing the `src/` prefix. These are exactly the bugs that ship to production when review
cycles are skipped — the shutdown gap would lose logs on restart; the path bug would fail silently.

After fixes, clear context and execute:

```
Use your planner skill to execute: @plan-logging.md
```

The developer, technical writer, and quality reviewer run the implementation. Each milestone passes
review before the next starts, and any deviation from the plan is visible.

## Other Skills

Not every task needs the full planning workflow. These skills handle specific concerns.

### DeepThink

For questions where the shape of the answer is not yet known. Unlike `problem-analysis` or
`decision-critic`, deepthink has no fixed structure — trade-offs, taxonomy questions, evaluative
judgments, meta-cognitive debugging, strategy evaluation, best-practices research, architecture and
design. Two modes, auto-detected: quick mode reasons directly; full mode launches parallel
sub-agents with distinct analytical perspectives, then synthesizes through agreement patterns.

```
Use your deepthink skill to think through [question]

# Explicit mode selection:
Use your deepthink skill (quick) to [question]
Use your deepthink skill (full) to [question]
```

### Refactor

LLM-generated code accumulates technical debt — duplication across files, god functions — that the
model does not notice. The refactor skill explores multiple dimensions in parallel (naming,
extraction, types, errors, modules, architecture, abstraction), validates findings against
evidence, and outputs prioritized recommendations. It does not generate code; it tells you what to
fix and why.

```
Use your refactor skill on src/services/
```

### Prompt Engineer

This workflow consists entirely of prompts, and each can be optimized. The skill analyzes prompts,
proposes changes with explicit pattern attribution, and waits for approval before applying anything.
It was optimized using itself.

```
Use your prompt engineer skill to optimize the system prompt for agents/developer.md
```

### Doc Sync

The CLAUDE.md/README.md hierarchy drifts as structure changes. The doc-sync skill audits and
synchronizes documentation across a repository — primarily for bootstrapping the workflow on an
existing repo or recovering after a major refactor. If you use the planning workflow consistently,
the technical-writer agent handles documentation as part of execution.

```
Use your doc-sync skill to synchronize documentation across this repository
```

## Credits

This project began as a fork of [solatis/claude-config](https://github.com/solatis/claude-config)
by Leon Mergen; substantial parts of the planner workflow and skill framework originate there. It is
maintained and extended here by [gcharang](https://github.com/gcharang).

## License

MIT — see [`LICENSE`](LICENSE). This is an MIT-licensed derivative; the original copyright is
retained alongside the current maintainer's.
