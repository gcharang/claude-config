# Planner batch/RPC surface — follow-ups

Residual items from the max-effort code review of the batch/RPC hardening and its
fix commit (`3547cc9`, branch `fix/planner-batch-roundtrip`). All 13 review findings
were implemented and adversarially verified (full suite green, ruff/pyright clean,
the original `read_batch_requests` crash class closed on both surfaces). The items
below are what the verification surfaced *after* those fixes — none block; they are
recorded so they aren't rediscovered cold.

Line numbers are as-of `3547cc9`; re-confirm with read-before-edit.

---

## A — CSV drift guard only covers `plan_commands` (LOW, latent)

**Location:** `cli/plan_common.py` (`CSV_PARAM_NAMES`) · guard:
`tests/test_batch_roundtrip_fixes.py::test_csv_param_names_matches_parse_csv_call_sites`

`CSV_PARAM_NAMES` is a single module-level frozenset, and
`dispatch._normalize_params` consults it for **every** dispatchable module — both
`plan_commands` and `qr_commands` (`qr.py` calls `discover_methods(qr_commands)`).
The introspective drift guard, however, AST-walks only `plan_commands`:

```python
tree = ast.parse(inspect.getsource(pc))   # pc == plan_commands only
```

So a future `parse_csv`-backed param added to `qr_commands` without also adding it
to `CSV_PARAM_NAMES` would be silently corrupted (`_normalize_params` unwraps its
single-element JSON array, then `parse_csv` comma-splits the unwrapped string — the
exact corruption the guard exists to catch) and the guard would stay green.

**Currently latent only:** `rg parse_csv skills/scripts/skills/planner/cli/qr_commands.py`
returns nothing, so there is no live corruption today.

**Proposed fix:** make the guard introspect every `discover_methods` target (at
minimum `plan_commands` + `qr_commands`) and assert `CSV_PARAM_NAMES` equals the
union of `parse_csv(<Name>)` call-site arg names across all of them.

---

## B — `batch()` dedup collides `1` / `1.0` (LOW, pre-existing, fails safe)

**Location:** `cli/dispatch.py` — `read_batch_requests` id check (~L380) and
`batch()` duplicate-id scan (~L192, `if rid in seen_ids`).

`bool` ids are rejected in both `read_batch_requests` and `batch()`. An integral
`float` id still equals the `int` id with the same value in the dedup scan.

**Why it's low / non-blocking:** the `id` field was entirely unguarded before
`3547cc9`, so these values already flowed identically into `seen_ids` — this is
pre-existing, not introduced by the fix. It **fails safe** (clean `validation_error`
frame, exit 1, no partial write) and is only reachable via exotic JSON-RPC ids no
agent authors (JSON-RPC ids are expected to be `str | number | null`).

**Proposed fix (optional):** reject non-integral-typed `float` ids so the accepted set
is `str | int | None`.

---

## C — CREATE-note prose order/wrapping drift (COSMETIC, not a defect — no action)

**Location:** `architect/plan_design_execute.py::_render_create_required_note`

Finding #2/#7's fix derives the CREATE-required bullet from `sorted(CREATE_REQUIRED)`,
so the rendered method order is now alphabetical (`set-decision; set-intent;
set-milestone; set-wave`) and the previously 2-wrapped lines render as one. The
content is fully preserved; this is LLM prompt prose where clause order and line
wrapping are semantically irrelevant, and nothing pins the old text. Recorded for
completeness only — no change recommended.
