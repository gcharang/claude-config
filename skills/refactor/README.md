# Refactor

LLM-generated code accumulates technical debt faster than hand-written code. The
LLM does not see duplication across files. It does not notice god functions
growing. It cannot detect that three modules implement the same validation logic
differently.

This skill catches what the LLM misses. It explores multiple smell categories in
parallel, validates findings against evidence, and outputs prioritized work
items.

## Workflow

`../scripts/skills/refactor/refactor.py` defines the steps and routes them by mode
(`WORKFLOW`, `format_output`, and the next command each step prints). Its dispatch
steps launch one haiku sub-agent per category, each running
`../scripts/skills/refactor/explore.py`.

## Design Decisions

### 1. Search and Report as Separate Explore Steps

Each explore agent searches in one script step and writes its smell_report in the
next. Splitting the work further (domain context, principle extraction, search
patterns) has the agent write intermediate artifacts that only it reads, each at
the cost of a Bash round trip. A separate report step means a haiku agent that
stops early in one long prompt still runs a command that asks for the report.

### 2. Domain Context Per-Category (Not Lifted to Parent)

Each explore agent works out the project's language, frameworks and naming itself,
rather than refactor.py doing it once and passing it to all agents.

Rationale: Different smell categories need different domain context aspects. A
"naming precision" category cares about naming conventions; a "module structure"
category cares about import patterns.

Rejected alternative: Lift domain context to refactor.py Step 1. Rejected
because it assumes all categories need identical context.

### 3. Synthesis in One Main-Session Step

The explore agents return their smell reports to the main session's context,
where no script reads them, so one main-session step turns them into work items.
Separate triage, cluster and contextualize steps would each re-emit the same
evidence as JSON for the next step to read.

### 4. Grep-Hints as Exemplars Requiring Translation

The markdown files contain generic patterns like `Manager, Handler, Utils` from
language-agnostic examples. Using these literally in a Go codebase would miss
`Store, Controller` patterns.

Solution: Treat grep-hints as abstract exemplars that must be translated to
project-specific equivalents based on domain context.

### 5. "Illustrative, Not Exhaustive" Framing

LLMs tend to interpret lists as complete. Without explicit framing, the model
searches only for listed patterns and misses analogous violations.

Mechanisms used:

- "Illustrative patterns (not exhaustive -- similar violations exist)"
- "e.g.," prefix on examples
- Open-ended escape hatches: "Any X that causes Y"

## Code Quality Categories

Categories are defined in `conventions/code-quality/` and organized by cognitive
mode:

| File                               | Scope                      | Cognitive Mode  |
| ---------------------------------- | -------------------------- | --------------- |
| `01-naming-and-types.md`           | Names, types, interfaces   | Local           |
| `02-structure-and-composition.md`  | Functions, control flow    | Local           |
| `03-patterns-and-idioms.md`        | Language idioms, patterns  | Local           |
| `04-repetition-and-consistency.md` | Duplication, uniformity    | Cross-Reference |
| `05-documentation-and-tests.md`    | Comments, tests, examples  | Local           |
| `06-module-and-dependencies.md`    | Module structure, imports  | Local           |
| `07-cross-file-consistency.md`     | Shared concerns, contracts | Cross-Reference |
| `08-codebase-patterns.md`          | Architecture, system view  | System          |

Each file contains numbered categories (`## N. Title`) with:

- `<principle>`: The core rule
- `<grep-hints>`: Abstract search patterns (exemplars, not exhaustive)
- `<violations>`: Illustrative patterns with severity
- `<exceptions>`: When not to flag
- `<threshold>`: When to flag

The parser extracts categories by line range. Content within categories is
free-form -- the parser passes raw text, the LLM interprets structure.

## Philosophy

Proposals pass validation against four principles:

| Principle      | Test                                              |
| -------------- | ------------------------------------------------- |
| COMPOSABILITY  | Can this piece combine cleanly with others?       |
| PRECISION      | Does the name create a new semantic level?        |
| NO SPECULATION | Have I seen this pattern 3+ times?                |
| SIMPLICITY     | Is this the simplest thing that removes friction? |

Proposals that predict futures or abstract from single instances get killed.

## Usage

```
Use your refactor skill on src/services/
```

With focus area:

```
Use your refactor skill on src/ -- focus on shared abstractions
```

## What It Does NOT Do

- Generate refactored code (recommendations only)
- Run linters or static analysis
- Apply style fixes
- Propose changes beyond what evidence supports
