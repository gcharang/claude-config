# Problem Analysis

LLMs jump to solutions. You describe a problem, they propose an answer. For
complex decisions with multiple viable paths, that first answer often reflects
the LLM's biases rather than the best fit for your constraints. This skill
forces structured reasoning before you commit.

The skill runs through six phases:

| Phase       | Actions                                                                  |
| ----------- | ------------------------------------------------------------------------ |
| Decompose   | State problem; identify hard/soft constraints, variables, assumptions    |
| Generate    | Create 2-4 distinct approaches (fundamentally different, not variations) |
| Critique    | Self-Refine feedback: specific weaknesses, eliminate or refine           |
| Verify      | Factored verification: answer questions WITHOUT looking at solutions     |
| Cross-check | Reconcile verified facts with original claims; update viability          |
| Synthesize  | Trade-off matrix with verified facts; decision framework                 |

## When to Use

Use this for decisions where the cost of choosing wrong is high:

- Multiple viable technical approaches (Redis vs Postgres, REST vs GraphQL)
- Architectural decisions with long-term consequences
- Problems where you suspect your first instinct might be wrong

## Example Usage

```
I need to decide how to handle distributed locking in our microservices.
Options I'm considering:

- Redis with Redlock algorithm
- ZooKeeper
- Database advisory locks

Use your problem-analysis skill to structure this decision.
```

## The Design

Grounded in three research-backed techniques:

- **Tree of Thoughts** (Yao 2023) -- decompose into thoughts "small enough for
  diverse samples, big enough to evaluate"
- **Chain-of-Verification** (Dhuliawala 2023) -- factored verification with
  open questions (not yes/no); answer WITHOUT seeing original solutions to
  avoid confirmation bias. Improves accuracy from 17% to 70%.
- **Self-Refine** (Madaan 2023) -- feedback must be actionable and specific;
  separate feedback phase improves quality by 5-40%

The structure prevents premature convergence. Critique catches obvious flaws
before costly verification. Factored verification prevents confirmation bias.
Cross-check forces explicit reconciliation of evidence with claims.
