# Claude Code Workflow Extensions

A collection of skills, agents, and commands for Claude Code, implementing an
opinionated workflow designed for long-term software maintenance with LLM
coding agents.

## Philosophy

LLM-assisted coding fails long-term because technical debt accumulates
unaddressed. I treat that as an engineering problem.

LLMs are tools, not collaborators. They cannot infer unspoken context -- the
culture, assumptions, and shared experiences that humans understand naturally.
When an engineer says "add retry logic", another engineer infers exponential
backoff, jitter, idempotency. An LLM infers nothing you do not explicitly state.

LLMs also have limited attention. Larger context windows do not solve this --
giving an LLM more text is like giving a human a larger stack of papers.
Attention drifts to the beginning and end; details in the middle are missed.
The solution is not more context, but precisely the right context.

This workflow addresses these failures through four principles:

### Context Hygiene

Each task receives precisely the information it needs -- no more. Sub-agents
start with fresh, focused context. CLAUDE.md files in each directory serve as
indexes; README.md captures decisions invisible in code.

Hygiene extends to code artifacts. Comments are scrubbed for temporal
contamination ("Added X" becomes "X handles Y"). Documentation uses tabular
indexes, not prose. Functions include "use when..." triggers and usage
examples. Decision rationale lives in README.md files, not lost chat history.
These rules prevent cruft accumulation.

### Planning Before Execution

LLMs make first-shot mistakes. The workflow separates planning from execution,
forcing ambiguities to surface when they are cheap to fix. Analysis is separate
from implementation. Each phase has clear inputs and outputs.

Plans capture why decisions were made, what alternatives were rejected, and
what risks were accepted. This survives context clears and new sessions --
the reasoning persists even when the conversation does not.

### Review Cycles

Plans pass through quality gates with multiple iterations until all checks
pass. Technical writer and quality reviewer run before execution begins,
catching issues when they are cheap to fix. Execution generates retrospectives
that feed back into planning.

### Cost-Effective Delegation

The orchestrator runs on a capable model, but delegates execution to smaller
agents -- Haiku-class for straightforward tasks, Sonnet-class for moderate
complexity. Just-in-time prompt injection provides precise guidance at each
step, allowing smaller models to perform reliably.

Model selection is dynamic. When quality review fails, issues appear subtle,
or problems recur, the orchestrator progressively escalates to higher-quality
models. The heavy lifting happens in well-scoped tasks with clear instructions;
expensive frontier models are reserved for genuine ambiguity, not routine work.

Plans are written to files. Execution can be interrupted and resumed.
Reconciliation detects already-completed milestones.

---

This workflow is opinionated. I am a backend engineer by trade -- the workflow
should apply equally to frontend, but feedback welcome. Same for whether these
patterns translate to less experienced engineers.

## Quick Start

Install by cloning into your Claude Code configuration directory:

```bash
# Per-project installation
git clone https://github.com/solatis/claude-config .claude

# Global installation (new)
git clone https://github.com/solatis/claude-config ~/.claude

# Global installation (existing ~/.claude with files)
cd ~/.claude
git remote add workflow https://github.com/solatis/claude-config
git fetch workflow
git merge workflow/main --allow-unrelated-histories
```

For non-trivial changes, the workflow is: explore -> plan -> execute.

1. Investigate the problem, ask clarifying questions
2. "Use your planner skill to write a plan to plans/my-feature.md"
3. `/clear` -- reset context
4. `/plan-execution plans/my-feature.md` -- execute via sub-agents

For details, see [The Workflow](#the-workflow).

## The Workflow

The primary workflow for non-trivial changes:

```mermaid
flowchart LR
    A[Free-form Analysis] --> B[Decision Critic]
    B --> C[Planning Phase]
    C --> D[Plan Execution]

    A -.- A1[Explore codebase<br>Understand problem<br>Consider approaches]
    B -.- B1[Stress-test approach<br>before committing]
    C -.- C1[Write plan to file<br>Review & refine]
    D -.- D1[Orchestrated implementation<br>via sub-agents]

    style B stroke-dasharray: 5 5
    style B1 stroke-dasharray: 5 5
```

Note: Decision Critic (dashed) is optional.

### Step 1: Free-form Analysis

Start with open exploration. Claude Code investigates the problem space:

```
I need to add retry logic to our API client.

Before proposing a solution:
- Explore the codebase to understand the existing API client structure
- Identify existing error handling patterns and conventions
- Ask clarifying questions about retry strategies, failure scenarios, and configuration
```

Claude explores the codebase, understands existing patterns, may ask clarifying
questions, and identifies constraints and dependencies.

### Step 2: Decision Critic (Optional)

If you're uncertain about your approach, or want to make sure you're not
overlooking something, invoke the decision critic skill:

```
Use your decision critic skill to stress-test my reasoning about the retry
logic approach before we commit to a plan.
```

This forces adversarial analysis of your assumptions and approach. Skip this
step for straightforward changes where the path forward is clear. See
[Decision Critic](#decision-critic) for details.

### Step 3: Invoke the Planner Skill

Once you understand what needs to be done:

```
"Now use your planner skill to write an implementation plan to plans/api-retry.md"
```

The planner runs a multi-step process: context gathering, decision/architecture,
refinement, then review by technical writer and quality reviewer. The review
loop catches LLM mistakes before execution begins. See [Planner](#planner) for
the full phase breakdown.

### Step 4: Clear Context

After planning completes:

```
/clear
```

This clears the conversation context, preventing the exploration/planning phase
from polluting the execution phase.

### Step 5: Execute the Plan

```
/plan-execution plans/api-retry.md
```

Plan execution delegates to specialized agents (developer, debugger,
quality-reviewer, technical-writer). The coordinator never writes code directly
-- it orchestrates. See [Plan Execution](#plan-execution) for the delegation
flow.

---

## Workflow Skills

These skills form the core workflow, used in sequence.

### Decision Critic

LLMs tend toward sycophancy -- agreeing with the user rather than providing
genuine pushback. For important architectural decisions, you want stress-testing,
not validation.

The decision-critic skill forces structured adversarial analysis:

```mermaid
flowchart LR
    D[Decomposition] --> V[Verification] --> Ch[Challenge] --> S[Synthesis]
```

| Phase         | Actions                                                                    |
| ------------- | -------------------------------------------------------------------------- |
| Decomposition | Extract claims, assumptions, constraints; assign IDs; classify each        |
| Verification  | Generate questions for verifiable items; answer independently; mark status |
| Challenge     | Steel-man argument against; explore alternative framings                   |
| Synthesis     | Verdict (STAND/REVISE/ESCALATE); summary and recommendation                |

#### When to Use

Use for important decisions where you want genuine criticism, not agreement:

- Architectural choices with long-term consequences
- Technology selection (language, framework, database)
- Tradeoffs between competing concerns (performance vs. maintainability)
- Decisions you're uncertain about and want stress-tested

#### Example Usage

```
I'm considering using Redis for our session storage instead of PostgreSQL.
My reasoning:

- Redis is faster for key-value lookups
- Sessions are ephemeral, don't need ACID guarantees
- We already have Redis for caching

Use your decision critic skill to stress-test this decision.
```

The skill will:

1. **Decompose** the decision into claims (C1: Redis is faster), assumptions
   (A1: sessions don't need durability), constraints (K1: Redis already deployed)
2. **Verify** each claim -- is Redis actually faster for your access pattern?
   What's the actual latency difference?
3. **Challenge** -- what if sessions DO need durability (shopping carts)?
   What's the operational cost of Redis failures?
4. **Synthesize** -- verdict with specific failed/uncertain items

#### The Anti-Sycophancy Design

The skill is grounded in three research-backed techniques:

- **Chain-of-Verification** (Dhuliawala et al., 2023) -- factored verification
  prevents confirmation bias by answering questions independently
- **Self-Consistency** (Wang et al., 2023) -- multiple reasoning paths reveal
  disagreement
- **Multi-Expert Prompting** (Wang et al., 2024) -- diverse perspectives catch
  blind spots

The 7-step structure forces the LLM through adversarial phases rather than
allowing it to immediately agree with your reasoning.

### Planner

The planner skill runs a multi-step planning process with built-in review:

```mermaid
flowchart TB
    subgraph planning[Planning Phase]
        P1[Context & Scope] --> P2[Decision & Architecture]
        P2 --> P3[Refinement]
        P3 --> P4[Final Verification]
    end

    subgraph review[Review Phase]
        R1[Technical Writer] --> R2[Quality Reviewer]
    end

    planning --> review
    R2 -->|pass| done[Plan written to file]
    R2 -->|fail| planning
```

**Planning Phase:**

| Step                    | Actions                                                                    |
| ----------------------- | -------------------------------------------------------------------------- |
| Context & Scope         | Confirm path, define scope, identify approaches, list constraints          |
| Decision & Architecture | Evaluate approaches, select with reasoning, diagram, break into milestones |
| Refinement              | Document risks, add uncertainty flags, specify paths and criteria          |
| Final Verification      | Verify completeness, check specs, write to file                            |

**Review Phase:**

| Step             | Actions                                                                            |
| ---------------- | ---------------------------------------------------------------------------------- |
| Technical Writer | Scrub temporal comments, add WHY comments, enrich rationale                        |
| Quality Reviewer | Check reliability, check conformance, return PASS/PASS_WITH_CONCERNS/NEEDS_CHANGES |

The review feedback loop catches LLM mistakes before execution begins. Plans
frequently have gaps -- missing error handling, incomplete acceptance criteria,
ambiguous specifications. The workflow iterates until QR passes, ensuring
problems are caught when they are cheap to fix rather than during implementation.

### Plan Execution

Plan execution delegates to specialized agents:

```mermaid
flowchart TB
    subgraph milestone[Per Milestone]
        C[Coordinator] --> D[Developer]
        C -.->|if error| Db[Debugger]
        Db -.-> D
        D --> QR[Quality Reviewer]
        QR -->|fail| C
    end

    QR -->|pass| next[Next Milestone]
    next -.-> C
    next -->|all complete| TW[Technical Writer]
    TW --> done[Execution complete]
```

The coordinator:

- Never writes code directly (delegates to developers)
- Parallelizes independent work across up to 4 developers per milestone
- Runs quality review after each milestone
- Sequences dependent milestones
- Invokes technical writer only after all milestones complete

The quality review feedback loop is intentional. LLMs almost always have
oversights -- missed edge cases, incomplete implementations, sometimes entire
components skipped. The workflow treats this as expected, not exceptional. When
QR fails, the coordinator receives specific findings and delegates fixes. This
cycle repeats until QR passes, then the next milestone begins.

The technical writer runs once at the end, updating the CLAUDE.md/README.md
hierarchy for all changes made during execution.

---

## Standalone Skills

These skills can be used independently, outside the main workflow.

### Prompt Engineer

A meta-skill for optimizing prompts themselves. Since this entire workflow
consists of prompts consumed by LLMs, each can be individually optimized.

#### Basic Usage

Optimize a simple prompt:

```
Use your prompt engineer skill to optimize the following prompt:

"You are a helpful assistant that writes Python code.
 Be concise and write clean code."
```

#### Optimizing Sub-Agents

Optimize a Claude Code sub-agent definition:

```
Use your prompt engineer skill to optimize the system prompt for
the following claude code sub-agent: agents/developer.md
```

#### Optimizing Multi-Prompt Workflows

For complex workflows where multiple prompts interact:

```
Consider the following Python file. Your task:
- Identify all different system/user prompts
- Understand how they interact together
- Use your prompt engineer skill to optimize each of these individually

@skills/planner/scripts/planner.py
```

#### Full Workflow Optimization

Optimize the entire planning/execution workflow:

```
Consider the following tightly integrated workflow:

Claude Code sub-agents:
* @agents/developer.md
* @agents/debugger.md
* @agents/quality-reviewer.md
* @agents/technical-writer.md

Planner skill:
* @skills/planner/SKILL.md
* @skills/planner/scripts/planner.py
* @skills/planner/resources/diff-format.md

Plan execution command:
* @commands/plan-execution.md

Your task:
* Think deeply to understand how everything fits together
* Identify all different prompts being consumed by LLMs
* Use your prompt engineer skill to optimize each of these
```

The prompt engineer skill:

1. Reads prompt engineering pattern references
2. Analyzes the prompt(s) for issues
3. Proposes changes with explicit pattern attribution
4. Waits for approval before applying changes
5. Presents optimized result with verification

### Doc Sync

The CLAUDE.md/README.md hierarchy is central to context hygiene. CLAUDE.md files
are pure indexes -- tabular navigation with "What" and "When to read" columns
that help LLMs (and humans) find relevant files without loading everything.
README.md files capture invisible knowledge: architecture decisions, design
tradeoffs, invariants that are not apparent from reading code.

The `doc-sync` skill audits and synchronizes this hierarchy across a repository.

#### How It Works

1. **Discovery** -- Maps all directories, identifies missing or outdated
   CLAUDE.md files
2. **Audit** -- Checks for drift (files added/removed but not indexed),
   misplaced content (architecture docs in CLAUDE.md instead of README.md)
3. **Migration** -- Moves architectural content from CLAUDE.md to README.md
4. **Update** -- Creates/updates indexes with proper tabular format
5. **Verification** -- Confirms complete coverage and correct structure

#### When to Use

- **Bootstrapping** -- Adopting this workflow on an existing repository
- **After bulk changes** -- Major refactors, directory restructuring
- **Periodic audits** -- Checking for documentation drift
- **Onboarding** -- Before starting work on an unfamiliar codebase

If you use the planning workflow consistently, the technical writer agent
maintains documentation as part of execution. The `doc-sync` skill is primarily
for bootstrapping or recovery.

#### Example Usage

```
Use your doc-sync skill to synchronize documentation across this repository
```

For targeted updates:

```
Use your doc-sync skill to update documentation in src/validators/
```

---

## How Skills Use Python Scripts

Skills can include Python scripts for "just in time" prompt injection. Rather
than loading a massive prompt upfront, the script outputs step-specific
guidance based on workflow state.

Example from `planner.py`:

```python
def get_planning_step_guidance(step_number: int, total_steps: int) -> dict:
    """Returns guidance for planning phase steps."""

    if step_number == 1:
        return {
            "actions": [
                "PRECONDITION: Confirm plan file path before proceeding.",
                "CONTEXT (understand before proposing):",
                "  - What code/systems does this touch?",
                # ... step 1 specific guidance
            ],
            "next": f"Invoke step {next_step} with your context analysis."
        }

    if step_number == 2:
        return {
            "actions": [
                "BEFORE deciding, evaluate each approach:",
                # ... step 2 specific guidance
            ],
            "next": f"Invoke step {next_step} with your chosen approach."
        }
    # ... and so on
```

Invocation:

```bash
python3 scripts/planner.py --step-number 1 --total-steps 4 --thoughts "..."
```

This pattern keeps context focused, allows workflows that adapt based on
intermediate results, and enables cost-effective model selection -- smaller
models can handle well-scoped tasks with precise instructions.

---

## Acknowledgments

I stood on the shoulders of giants, and [Southbridge Research's exceptional analysis of Claude Code prompts](https://southbridge-research.notion.site/Prompt-Engineering-The-Art-of-Instructing-AI-2055fec70db181369002dcdea7d9e732) has been of tremendous help to kick-start my understanding of how to write effective prompts.
