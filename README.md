# Claude Code Workflow Extensions

I use Claude Code for most of my work. After months of iteration, I noticed
a pattern: LLM-assisted code rots faster than hand-written code. Technical
debt accumulates because the LLM doesn't know what it doesn't know, and
neither do you until it's too late.

This repo is my solution: skills and workflows that force planning before
execution, keep context focused, and catch mistakes before they compound.

## Why This Exists

LLM-assisted coding fails long-term. Technical debt accumulates because
the LLM cannot see it, and you're moving too fast to notice. I treat
this as an engineering problem, not a tooling problem.

LLMs are tools, not collaborators. When an engineer says "add retry logic",
another engineer infers exponential backoff, jitter, and idempotency. An LLM
infers nothing you don't explicitly state. It cannot read the room. It has
no institutional memory. It will cheerfully implement the wrong thing with
perfect confidence and call it "production-ready".

Larger context windows don't help. Giving an LLM more text is like giving
a human a larger stack of papers; attention drifts to the beginning and
end, and details in the middle get missed. The solution isn't more context.
It's the proper context.

## Principles

This workflow is built on four principles:

### Context Hygiene

Each task gets precisely the information it needs — no more. Sub-agents
Start with a fresh context. CLAUDE.md files in each directory serve as
indexes; README.md captures decisions that aren't visible in the code.

This extends to code artefacts. Comments get scrubbed for temporal
contamination — "Added X" becomes "X handles Y". Functions include
"use when..." triggers. Decision rationale lives in README files, not
in chat history that gets cleared.

### Planning Before Execution

LLMs make first-shot mistakes. Always. The workflow separates planning
from execution, forcing ambiguities to surface when they're cheap to fix.

Plans capture why decisions were made, what alternatives were rejected,
and what risks were accepted. Plans are written to files. When you clear
context and start fresh, the reasoning survives.

### Review Cycles

Execution is split into milestones -- smaller units that are manageable
and can be validated individually. This ensures continuous, verified
progress. Without it, execution becomes a waterfall: one small oversight
early on and agents drown in accumulated mistakes by the end.

Quality gates run at every stage. A technical writer agent checks
clarity; a quality reviewer checks completeness. The loop runs until
both pass.

Plans pass review before execution begins. During execution, each
milestone passes review before the next starts.

### Cost-Effective Delegation

The orchestrator delegates to smaller agents — Haiku for straightforward
tasks, Sonnet for moderate complexity. Prompts are injected just-in-time,
giving smaller models precisely the guidance they need at each step.

When quality review fails or problems recur, the orchestrator escalates
to higher-quality models. Expensive models are reserved for genuine
ambiguity, not routine work.

---

This workflow is opinionated. I'm a backend engineer — the patterns should
apply to frontend work, but I haven't tested that. If you're less experienced
with software engineering, I'd like to know whether this helps or adds
overhead.

## Quick Start

Clone into your Claude Code configuration directory:

```bash
# Per-project
git clone https://github.com/solatis/claude-config .claude

# Global (new setup)
git clone https://github.com/solatis/claude-config ~/.claude

# Global (existing ~/.claude)
cd ~/.claude
git remote add workflow https://github.com/solatis/claude-config
git fetch workflow
git merge workflow/main --allow-unrelated-histories
```

## Usage

The workflow for non-trivial changes: explore → plan → execute.

**1. Explore the problem.**
In this phase, it's important to:

- understand what you're dealing with,
- figure out the solution.

This is relatively free-form. If the project and/or our surface area is
particularly large, use the `analyze` skill to explore the project's
code properly before proposing a solution.

**2. (Optional) Stress-test your approach.**
If you're uncertain, use the `decision-critic` skill to find holes in
your reasoning before you commit to a direction.

**3. Write a plan.**
"Use your planner skill to write a plan to plans/my-feature.md"

The planner runs your plan through review cycles — technical writer
for clarity, quality reviewer for completeness — until it passes.

The planner captures all decisions, tradeoffs, and information not
visible from the code so that this context does not get lost.

**4. Clear context.**
`/clear` — this is important. You don't want to minimise context usage,
and you have already written down everything necessary for
plan execution.

**5. Execute.**
"Use your planner skill to execute plans/my-feature.md"

The planner delegates to sub-agents. It never writes code directly.
Each milestone goes through the developer, then the technical-writer
and quality-reviewer. No milestone starts until the previous one
passes review.

Where possible, it executes multiple tasks in parallel.

For detailed breakdowns of each skill, see their READMEs:

- [Analyze](skills/analyze/README.md)
- [Decision Critic](skills/decision-critic/README.md)
- [Planner](skills/planner/README.md)
