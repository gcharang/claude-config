# Refactor

LLM-generated code accumulates technical debt faster than hand-written code. The
LLM does not see duplication across files. It does not notice god functions
growing. It cannot detect that three modules implement the same validation logic
differently.

I built this skill to catch what the LLM misses. It explores multiple dimensions
in parallel, validates findings against evidence, and outputs prioritized
recommendations.

## Workflow

```
  Dispatch ---------> Triage ---------> Deep Dive
  (10 parallel)      (select 3-5)      (cross-check)
       |                  |                  |
       v                  v                  v
  [dimensions]       [ranking]          [evidence]
       |                  |                  |
       +------------------+------------------+
                          |
                          v
                       Derive
                     (proposals)
                          |
                          v
                      Validate
                    (philosophy)
                          |
                          v
                   Pattern Synthesis
                  (cross-cutting)
                          |
                          v
                      Synthesize
                (tiered recommendations)
```

| Phase             | Question                           | Output                           |
| ----------------- | ---------------------------------- | -------------------------------- |
| Dispatch          | What exists?                       | Parallel findings per dimension  |
| Triage            | Which dimensions matter?           | Top 3-5 ranked by impact         |
| Deep Dive         | Are these real issues?             | Confirmed findings with evidence |
| Derive            | What change removes this friction? | Proposals tied to evidence       |
| Validate          | Does this align with philosophy?   | Validated or killed proposals    |
| Pattern Synthesis | What patterns cut across findings? | Emergent abstractions            |
| Synthesize        | What should be done first?         | Tiered recommendations           |

So, why all the phases? I enforce understanding before proposing and evidence
before abstracting. Deep Dive cross-checks findings by re-reading code and
applying detection questions. Validate kills proposals that fail the philosophy
test. Without these gates, LLMs propose abstractions from single instances.

## Dimensions

The skill launches parallel Explore agents across these dimensions:

| Dimension     | Weight | Focus                                                    |
| ------------- | ------ | -------------------------------------------------------- |
| architecture  | 3      | Wrong boundaries, scaling bottlenecks, structural issues |
| modules       | 3      | Circular dependencies, wrong cohesion, layer violations  |
| abstraction   | 3      | Repeated patterns across files needing unification       |
| types         | 2      | Missing domain concepts, primitive obsession             |
| errors        | 2      | Inconsistent or poorly-located error handling            |
| conditionals  | 2      | Complex conditionals signaling missing abstractions      |
| naming        | 1      | Names that mislead or obscure intent                     |
| extraction    | 1      | Duplication, mixed responsibilities, god functions       |
| testability   | 1      | Hard-coded dependencies, global state                    |
| modernization | 1      | Outdated patterns, deprecated APIs                       |
| readability   | 1      | Code requiring external context to understand            |

Weight affects triage scoring. Structural dimensions (weight 3) surface first --
they constrain everything else.

## Philosophy

Every proposal passes validation against four principles:

| Principle      | Test                                              |
| -------------- | ------------------------------------------------- |
| COMPOSABILITY  | Can this piece combine cleanly with others?       |
| PRECISION      | Does the name create a new semantic level?        |
| NO SPECULATION | Have I seen this pattern 3+ times?                |
| SIMPLICITY     | Is this the simplest thing that removes friction? |

Proposals that predict futures or abstract from single instances get killed.
Dijkstra: "The purpose of abstraction is not to be vague, but to create a new
semantic level in which one can be absolutely precise."

## Output

Recommendations are tiered by impact and effort:

| Tier        | Criteria                                     |
| ----------- | -------------------------------------------- |
| Critical    | High impact, low effort (start here)         |
| Recommended | High impact, medium/high effort (plan these) |
| Consider    | Valid but lower priority (revisit later)     |

Each recommendation includes dimension, location, quoted evidence, and specific
action.

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
