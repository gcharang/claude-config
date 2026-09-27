# QR Severity Taxonomy

## Severity Levels (MoSCoW)

| Level  | Meaning                  | Progressive De-Escalation |
| ------ | ------------------------ | ------------------------- |
| MUST   | Unrecoverable if missed  | All iterations            |
| SHOULD | Maintainability debt     | Iterations 1-3            |
| COULD  | Auto-fixable, low impact | Iterations 1-2            |

## The MUST bar

This bar governs free-form reviews: review lanes, and quality-reviewer outside
script mode. A finding is MUST only when it is unrecoverable if it ships and has
a trigger that shipped configuration or accepted input actually reaches. In an
instruction file an agent loads and acts on, it is MUST only when a wrong
reading changes what an agent does and nobody would notice. Scripts, test
harnesses, tooling, docs no agent acts on, commit messages, plans and records
are never MUST unless they make a product check pass falsely. A test's
strength, mutation survival and guard completeness, and titles, comments,
naming and restated claims, are SHOULD at most; a test is MUST only when it is
the sole guard of a security property, or a bug-fix regression test with no
evidence it failed on the pre-fix code. A finding that needs a hostile getter,
proxy or mutated state outside the threat model is SHOULD. In a free-form
review, a category below marked MUST yields a MUST only when its finding meets
this bar, and a SHOULD otherwise.

Scoped exception: the planner's script-mode plan and implementation reviews
keep the MUST levels their step prompts assign in
skills/scripts/skills/planner/quality_reviewer/prompts/content.py, knowledge
categories included; this bar does not lower them.

## Categories by Recoverability

### KNOWLEDGE (MUST)

Knowledge loss is permanent. These block in the planner's script-mode review,
under the scoped exception above, and in a free-form review when a finding
meets the MUST bar.

| Category                    | Detection                                   |
| --------------------------- | ------------------------------------------- |
| DECISION_LOG_MISSING        | Non-trivial choice without logged rationale |
| POLICY_UNJUSTIFIED          | Policy default without Tier 1 backing       |
| IK_TRANSFER_FAILURE         | Invisible knowledge not at BEST location    |
| TEMPORAL_CONTAMINATION      | Change-relative language in comments        |
| BASELINE_REFERENCE          | Comment references removed/replaced code    |
| ASSUMPTION_UNVALIDATED      | Architectural assumption without citation   |
| LLM_COMPREHENSION_RISK      | Pattern that would confuse future LLM       |
| MARKER_INVALID              | Intent marker without valid explanation     |
| DOC_DELIVERABLE_UNSATISFIED | Acceptance criteria unmet by authored files |

`DOC_DELIVERABLE_UNSATISFIED` is the one MUST a sub-agent can always fix -- the TW
authors the missing file. It sits in MUST because the unproduced planned document
*is* the knowledge loss, and a still-failing MUST escalates to the user at the
iteration ceiling (`get_blocking_severities` / `gates.py`) rather than looping --
so it never blocks a plan indefinitely. A doc-only milestone exists solely to
produce its deliverable; de-escalating it to a silent pass would finalize a plan
with its whole reason for existing unmet.

### STRUCTURE (SHOULD)

Maintainability debt. Compounds but detectable later.

| Category                    | Detection                                    |
| --------------------------- | -------------------------------------------- |
| GOD_OBJECT                  | >15 methods OR >10 deps OR mixed concerns    |
| GOD_FUNCTION                | >50 lines OR mixed abstraction OR >3 nesting |
| DUPLICATE_LOGIC             | Copy-pasted blocks, parallel functions       |
| INCONSISTENT_ERROR_HANDLING | Mixed exceptions/codes in same module        |
| CONVENTION_VIOLATION        | Violates documented project convention       |
| TESTING_STRATEGY_VIOLATION  | Tests don't follow confirmed strategy        |
| MISSED_SIMPLIFICATION       | Behavior-preserving restructuring would delete branches/helpers/layers, not taken |
| FILE_SIZE_EXPLOSION         | Diff grows a file past 1000 lines without decomposition or compelling reason |
| SPAGHETTI_CONDITIONAL       | Ad-hoc special-case branch/flag bolted onto an existing or shared flow |
| THIN_ABSTRACTION            | Identity wrapper, pass-through, or "magic" mechanism adding indirection without clarity |
| BOUNDARY_TYPE_EROSION       | Needless cast/`any`/`unknown`/optional papering over an invariant a type boundary should make explicit |
| CANONICAL_DUPLICATION       | Bespoke near-duplicate of an existing canonical utility/helper |
| LAYER_LEAK                  | Feature logic placed in a shared path, or logic/detail in the wrong layer or package |
| NON_ATOMIC_ORCHESTRATION    | Avoidable serialization of independent work, or related updates that can leave half-applied state |

These structural-simplification categories carry SHOULD severity: high-conviction
and concrete, never vague "could be cleaner" notes. Each flag must name the
specific behavior-preserving restructuring and what it deletes. Like all SHOULD
findings they de-escalate (see `get_blocking_severities`), so an unfixed
simplification never blocks a plan indefinitely.

### DIAGRAM (MUST for semantic, COULD for format)

Diagram graph integrity. Semantic issues block; format issues warn.

| Category             | Severity | Detection                                  |
| -------------------- | -------- | ------------------------------------------ |
| ORPHAN_NODE          | MUST     | Node with zero edges                       |
| INVALID_EDGE_REF     | MUST     | Edge source/target references missing node |
| INVALID_SCOPE_REF    | MUST     | Scope references non-existent milestone    |
| DIAGRAM_WIDTH_EXCEED | COULD    | ASCII render line > 80 chars               |
| UNCLOSED_BOX         | COULD    | Box corners misaligned in ASCII render     |

### COSMETIC (COULD)

Auto-fixable, minimal impact.

| Category            | Detection                                                  |
| ------------------- | ---------------------------------------------------------- |
| DEAD_CODE           | Unused functions, impossible branches                      |
| FORMATTER_FIXABLE   | Style issues fixable by formatter/linter                   |
| MINOR_INCONSISTENCY | Non-conformance with no documented rule                    |
| TOOLCHAIN_CATCHABLE | Error in planned code that compiler/linter/interpreter     |
|                     | would flag, where intended correct code is obvious from    |
|                     | context (typos, missing imports, non-exhaustive match).    |
|                     | NOT: errors revealing plan-level misunderstanding -- those |
|                     | are ASSUMPTION_UNVALIDATED (MUST)                          |

## IK Proximity Rule

Invisible knowledge must be at BEST location: "as close as possible to where
relevant, but not more"

| Knowledge Type | Best Location                           |
| -------------- | --------------------------------------- |
| Accepted risks | :TODO: comment at flagged code location |
| Architecture   | README.md in SAME directory             |
| Tradeoffs      | Code comment where decision shows       |
| Invariants     | Code comment at enforcement point       |

Wrong location = IK_TRANSFER_FAILURE (MUST)
