# Refactor

LLMs generate code that works but accumulates technical debt: copy-paste
duplication, god functions, missing abstractions, inline everything. This skill
provides systematic friction-driven refactoring -- understanding before judging,
verifying before proposing, validating before recommending.

## Philosophy

> "The purpose of abstraction is not to be vague, but to create a new semantic
> level in which one can be absolutely precise." -- Dijkstra

Good abstractions emerge from understanding patterns across multiple instances.
Bad abstractions predict patterns that don't exist.

| Principle      | Meaning                                      |
| -------------- | -------------------------------------------- |
| COMPOSABILITY  | Small pieces that combine cleanly            |
| PRECISION      | Names that create new semantic levels        |
| NO SPECULATION | Only abstract what you've seen repeated (3+) |
| SIMPLICITY     | The minimum needed for the current task      |

## Seven Phases

| Phase      | Question                             | Purpose                        |
| ---------- | ------------------------------------ | ------------------------------ |
| Explore    | What exists?                         | Map structure without judgment |
| Understand | What is it trying to do?             | Grasp intent before critiquing |
| Surface    | Where does it fight change?          | Find friction with evidence    |
| Verify     | Are these real issues?               | Cross-check, find root causes  |
| Derive     | What abstraction removes this?       | Propose grounded in evidence   |
| Validate   | Does this align with the philosophy? | Test against principles        |
| Synthesize | What should be done first?           | Prioritize and teach           |

## When to Use

- **Post-feature cleanup** -- After LLM-generated feature works, address debt
- **Before major changes** -- Refactor friction points that would complicate work
- **Code review findings** -- When review reveals structural issues
- **Composition breakdown** -- When simple changes require touching many files

## When to Skip

- Code is already clean and well-structured
- One-off script or prototype (debt doesn't compound)
- You're about to rewrite anyway
- The "friction" is actually necessary complexity

## Contrastive Examples

### GOOD Refactoring (Removes Friction, Grounded in Evidence)

```
FRICTION: data['user']['email'] appears 5 times across 3 functions
  > user_email = data['user']['email']
  > if validate_email(data['user']['email']):
  > send_to(data['user']['email'])

PROPOSAL: Extract User type with .email property

WHY GOOD:
  - Names the concept (User)
  - Single point of change
  - Evidence: 5 instances, pattern is stable
  - Composability: User type can gain more properties naturally
```

### BAD Refactoring (Premature, Speculative)

```
OBSERVATION: One config-parsing function (parse_config)

PROPOSAL: Create ConfigParserFactory with AbstractConfigStrategy,
          JSONConfigStrategy, YAMLConfigStrategy

WHY BAD:
  - Only ONE use case (no evidence of need for strategies)
  - Predicts futures that may not come
  - Violates SIMPLICITY: minimum needed is parse_config
  - "Manager", "Factory", "Strategy" for single case = red flag
```

### GOOD: God Function Decomposition

```
FRICTION: process_order (127 lines) does validation, pricing, inventory, email

PROPOSAL: Decompose into:
  - validate_order(order) -> ValidationResult
  - calculate_price(order) -> Price
  - reserve_inventory(order) -> ReservationResult
  - send_confirmation(order, result) -> None

WHY GOOD:
  - Each function has ONE responsibility
  - Names describe WHAT not HOW
  - Clean interfaces (parameters in, result out)
  - Can test/change each independently
```

### BAD: Unnecessary Abstraction

```
OBSERVATION: Two similar loops that iterate over items

PROPOSAL: Create ItemIterator base class with ConcreteIterator subclasses

WHY BAD:
  - Two instances isn't enough (need 3+)
  - "Similar" isn't "same" -- check if bug fix in one requires fix in other
  - Python already has iteration -- don't reinvent
  - SIMPLICITY: two loops might just be two loops
```

## Example Usage

```
Use your refactor skill on src/services/order.py.
I suspect there's duplication and the functions are too long.
```

The skill outputs recommendations with file:line references and evidence. Each
recommendation ties to identified friction and passes validation against the
philosophy.

## What It Does NOT Do

- Generate refactored code (recommendations only)
- Run linters or static analysis tools
- Apply style fixes (use formatters for that)
- Propose changes beyond what evidence supports

## Research Basis

- **Factored Verification** (Dhuliawala 2023): Answer verification questions
  independently to avoid confirmation bias
- **Quote Extraction**: Force evidence commitment before reasoning
- **Open Questions > Checklists**: Discovery questions reveal more than
  pattern matching
- **Separation of Concerns**: Each phase has ONE cognitive goal
