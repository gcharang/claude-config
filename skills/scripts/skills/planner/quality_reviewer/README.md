# QR (Quality Review)

## Overview

Quality Review performs validation with severity-based blocking thresholds. Two phase-parameterized runners serve all three QR phases (`--phase {plan-design|impl-code|impl-docs}`): `qr_decompose.py` generates verification items, `qr_verify.py` executes them (single-item mode for parallel dispatch). Phase-specific content lives in `prompts/content.py`; the shared control flow lives in `prompts/decompose.py` (decompose) and `qr_verify_base.py` (verify).

## Modules

- `qr_decompose.py` — decompose runner; looks up per-phase prompts from `prompts.content.DECOMPOSE_CONTENT` and drives the shared 13-step `prompts.decompose.dispatch_step`.
- `qr_verify.py` — verify runner; selects the phase's `VerifyBase` subclass from `prompts.content.VERIFIERS` and routes through `verify_main`.
- `prompts/content.py` — per-phase decompose prompts (e.g. `PLAN_DESIGN_STEP_1_ABSORB`) + the `PlanDesignVerify` / `ImplCodeVerify` / `ImplDocsVerify` classes, registered in `DECOMPOSE_CONTENT` / `VERIFIERS`.

The phases:

- **plan-design** (orchestrator: `planner.py`) — the only plan-phase QR: validates plan.json structure, milestones, code_intents (the binding contract), acceptance criteria, decisions, and the diagram IR. Code and docs are verified at execution.
- **impl-code** (orchestrator: `executor.py`) — post-implementation code validation against plan specifications.
- **impl-docs** (orchestrator: `executor.py`) — post-implementation documentation review for accuracy and completeness.

**Supporting:**

- `qr_verify_base.py`: `VerifyBase` ABC implementing the shared dynamic verify workflow (1 context step + 2 steps per item [analyze/confirm] + 1 summary step; total = 2 + 2*N for N items) plus `verify_main` (CLI wiring + lock-safe `--result` recording). Each phase subclass only overrides `get_verification_guidance()`.

## QA State Tracking Integration

QR gates now integrate with QA state tracking for structured verification. QA decomposition applies plan-and-solve methodology to quality verification by breaking monolithic reviews into parallelizable checklist items.

### Philosophy: Minimal State, Dumb Main Agent, Just-In-Time Prompting

**Minimal State Files**: Store ONLY authoritative data -- item statuses (TODO/PASS/FAIL). Sub-agents compute status overview on-demand when THEY need it. No derived values stored.

**Dumb Main Agent**: Main agent dispatches and routes. It needs ONE bit: PASS or FAIL. The LLM reads responses naturally and follows instructions. No parsing logic required in main agent.

**Just-In-Time Prompting**: Executor sub-agent (fixer) invokes script and sees prompts about what failed. Main agent never sees these details. Details are injected only when needed, only to the agent that needs them.

### Why Main Agent Doesn't Parse

The main agent needs no parsing logic because the reply it routes on is one bare word: each
verify agent returns `PASS` or `FAIL`, and the main agent tallies those to pick the gate's
`--qr-status`. The detail behind a FAIL lives in qr-{phase}.json, written by the verify
runner's `--result/--finding` flags and read by the script, never lifted out of the response
text. A fix agent returns a bare `PASS` when done, which routes the orchestrator back into a
fresh QR pass rather than into a status tally; decompose also returns a bare `PASS`, and its
items reach the orchestrator through qr-{phase}.json (see Response Formats below).

This eliminates an entire class of bugs: parsing errors, schema mismatches, JSON escaping issues.

### Why Status Overview is Sub-Agent Only

The executor needs to see "5 items: 3 PASS, 2 FAIL" to decide what to fix. The main agent doesn't. The main agent only needs to know: did verification pass or fail?

Status overview is computed on-demand by the executor when it runs. It's not stored in qr-{phase}.json because it's derived data. Storing it would violate the minimal state principle and create consistency risks (what if counts don't match items?).

### Response Formats

**DECOMPOSE Mode**: writes `qr-{phase}.json` (every item `status: TODO`) through `prompts/decompose.py`; its final response is `PASS`. The orchestrator reads the file, not the response.

**VERIFY Mode**: the agent's entire final response is one bare word.

```
PASS
```

or

```
FAIL
```

Per-item verdicts and findings reach qr-{phase}.json through the runner's
`--result PASS|FAIL --finding <text>` flag, never through the returned text; the
orchestrator tallies the single word to pick `--qr-status pass|fail`.

**FIX Mode**: `exec_qr_fix.py --phase <phase>` (`prompts/fix.py`) runs inside the work phase's own agent (architect, developer, or technical writer): load the blocking FAIL items, apply targeted fixes, validate. Its final response is a bare `PASS`.

### Three Modes

**DECOMPOSE**: Break artifact into verifiable QA items. Sub-agent reads artifact, identifies quality dimensions, and writes the items to qr-{phase}.json. Items start with status=TODO.

**VERIFY**: Execute verification for each item. The orchestrator re-bins the items into at most `VERIFY_MAX_PARALLEL` balanced groups (`shared/qr/utils.py::balance_verify_groups`) and dispatches every group in parallel; each verifier records PASS or FAIL per item with `--result`/`--finding`.

**FIX**: `exec_qr_fix.py --phase <phase>` repairs the blocking FAIL items inside the work phase's own agent (see FIX Mode above).

### State File Schema (qr-{phase}.json)

```json
{
  "phase": "plan-design",
  "iteration": 1,
  "items": [
    {
      "id": "qa-001",
      "scope": "*",
      "check": "Verify milestone definitions are complete with acceptance criteria",
      "status": "PASS",
      "severity": "SHOULD",
      "finding": null
    },
    {
      "id": "qa-002",
      "scope": "milestone:M-001",
      "check": "Validate acceptance criteria for milestone M-001",
      "status": "FAIL",
      "severity": "MUST",
      "finding": "Acceptance criteria missing. Need success conditions and verification steps."
    },
    {
      "id": "qa-003",
      "scope": "milestone:M-002",
      "check": "Verify every code_intent in M-002 cites a decision for its thresholds",
      "status": "TODO",
      "severity": "SHOULD",
      "finding": null
    }
  ]
}
```

**phase**: Verification phase -- one of `plan-design`, `impl-code`, `impl-docs`.

**iteration**: QR cycle counter (starts at 1); drives severity de-escalation.

**items**: `QRItem` records; `shared/schema.py::QRItem` defines their fields.

### Orchestrator Loop

The orchestrator loop (work -> decompose -> verify -> gate) is specified in `skills/planner/INTENT.md`; gate routing is in `shared/gates.py`.

### Why JSON

**Consistency**: JSON is universal. Every language, every tool. YAML requires pyyaml dependency and has indentation gotchas.

**Avoid pyyaml dependency**: One less package to install, one less version conflict risk.

**Simplicity**: JSON schema is unambiguous. YAML has multiple syntaxes for the same structure (flow vs block, quoted vs unquoted).

**Tooling**: Every editor has JSON validation built-in. JSON Schema validators are ubiquitous.

**LLM-friendly**: Modern LLMs handle JSON natively. ChatML and Claude both have JSON mode. No escaping issues for simple structures like QA items.

## QR Iteration Blocking

Severity thresholds vary by iteration depth to prevent infinite retry loops:

| Iteration | Block Severities        | Rationale                                |
| --------- | ----------------------- | ---------------------------------------- |
| 1-2       | All (MUST/SHOULD/COULD) | High failure rate, force immediate fixes |
| 3         | MUST/SHOULD             | Address nuanced issues                   |
| 4+        | MUST only               | Prevent infinite retry loops             |

## LoopState Tracking

QR gates use LoopState enum to track iteration progression:

- **INITIAL**: First review attempt
- **RETRY**: Fixing issues from previous iteration
- **COMPLETE**: Passed review

State transitions:

```
INITIAL -> (QRStatus.PASS) -> COMPLETE [terminal]
INITIAL -> (QRStatus.FAIL) -> RETRY -> (iteration++) -> RETRY -> ...
```
