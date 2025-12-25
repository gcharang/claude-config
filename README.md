# Claude Code Workflow Extensions

A collection of skills, agents, and commands for Claude Code, implementing an
opinionated workflow designed for long-term software maintenance with LLM
coding agents.

## Philosophy

This repository embeds a structured approach to AI-assisted development:

- **Skills** orchestrate complex workflows via Python scripts that inject
  prompts "just in time" based on workflow state
- **Agents** are specialized sub-agents with domain expertise (developer,
  debugger, quality reviewer, technical writer)
- **Commands** trigger specific workflows like plan execution

The workflow prioritizes **hygiene over speed**: strict documentation rules,
decision tracking, and quality gates prevent technical debt accumulation when
maintaining repositories over long periods.

## Repository Structure

```
agents/                  Specialized sub-agents
  developer.md           Implements specs with tests
  debugger.md            Systematic bug analysis
  quality-reviewer.md    Production risk detection
  technical-writer.md    LLM-optimized documentation

commands/
  plan-execution.md      Executes approved plans via agent delegation

skills/
  planner/               Implementation planning workflow
    SKILL.md             Skill entry point
    scripts/             Just-in-time prompt injection
    resources/           Shared formats and conventions

  prompt-engineer/       Prompt optimization skill
    SKILL.md             Skill entry point
    references/          Prompt engineering patterns

  decision-critic/       Adversarial decision analysis
    SKILL.md             Skill entry point
    scripts/             Just-in-time prompt injection
```

---

## The Planning Workflow

The primary workflow for non-trivial changes:

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  Free-form       |---->|  Planning        |---->|  Plan Execution  |
|  Analysis        |     |  Phase           |     |  Phase           |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
  Explore codebase         Write plan to          Orchestrated
  Understand problem       markdown file          implementation
  Consider approaches      Review & refine        via sub-agents
```

### Step 1: Free-form Analysis

Start with open exploration. Claude Code investigates the problem space:

```
User: "I need to add retry logic to our API client"

Claude: [Explores codebase, understands patterns, considers approaches]
        [May ask clarifying questions]
        [Identifies constraints and dependencies]
```

### Step 2: Invoke the Planner Skill

Once you understand what needs to be done:

```
User: "Now use your planner skill to write an implementation plan to
       plans/api-retry.md"
```

The planner skill runs a multi-step planning process:

```
+--------------------------------------------------------------------------------+
|                           PLANNER SKILL WORKFLOW                               |
+--------------------------------------------------------------------------------+
|                                                                                |
|    Step 1: Context & Scope                                                     |
|    +------------------------------------------------------------------+        |
|    | - Confirm plan file path                                         |        |
|    | - Define scope and out-of-scope                                  |        |
|    | - Identify 2-3 approaches with tradeoffs                         |        |
|    | - List constraints (technical, organizational)                   |        |
|    +------------------------------------------------------------------+        |
|                                    |                                           |
|                                    v                                           |
|    Step 2: Decision & Architecture                                             |
|    +------------------------------------------------------------------+        |
|    | - Evaluate approaches (success probability, failure modes)       |        |
|    | - Select approach with multi-step reasoning                      |        |
|    | - Capture component diagrams (ASCII art)                         |        |
|    | - Break into deployable milestones                               |        |
|    +------------------------------------------------------------------+        |
|                                    |                                           |
|                                    v                                           |
|    Step 3: Refinement                                                          |
|    +------------------------------------------------------------------+        |
|    | - Document risks with mitigations                                |        |
|    | - Add uncertainty flags to milestones                            |        |
|    | - Specify exact file paths and acceptance criteria               |        |
|    | - Include code changes in diff format                            |        |
|    +------------------------------------------------------------------+        |
|                                    |                                           |
|                                    v                                           |
|    Step 4+: Final Verification                                                 |
|    +------------------------------------------------------------------+        |
|    | - Verify Planning Context completeness                           |        |
|    | - Check milestone specifications                                 |        |
|    | - Write plan to file                                             |        |
|    +------------------------------------------------------------------+        |
|                                    |                                           |
+--------------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------------+
|                              REVIEW PHASE                                      |
+--------------------------------------------------------------------------------+
|                                                                                |
|    Review Step 1: Technical Writer                                             |
|    +------------------------------------------------------------------+        |
|    | - Scrub temporally contaminated comments                         |        |
|    | - Add WHY comments to code snippets                              |        |
|    | - Enrich plan prose with rationale                               |        |
|    +------------------------------------------------------------------+        |
|                                    |                                           |
|                                    v                                           |
|    Review Step 2: Quality Reviewer                                             |
|    +------------------------------------------------------------------+        |
|    | - Check production reliability (RULE 0)                          |        |
|    | - Check project conformance (RULE 1)                             |        |
|    | - Verify TW annotations                                          |        |
|    | - Return: PASS | PASS_WITH_CONCERNS | NEEDS_CHANGES              |        |
|    +------------------------------------------------------------------+        |
|                                                                                |
+--------------------------------------------------------------------------------+
                                     |
                                     | (Plan approved)
                                     v
                              [Plan written to file]
```

The Python script (`scripts/planner.py`) injects step-specific guidance as you
progress. Each step produces concrete outputs before advancing.

### Step 3: Clear Context

After planning completes:

```
User: /clear
```

This clears the conversation context, preventing the exploration/planning phase
from polluting the execution phase.

### Step 4: Execute the Plan

```
User: /plan-execution plans/api-retry.md
```

Plan execution delegates to specialized agents:

```
+--------------------------------------------------------------------------------+
|                          PLAN EXECUTION WORKFLOW                               |
+--------------------------------------------------------------------------------+
|                                                                                |
|  Coordinator reads plan, analyzes dependencies, identifies parallel work       |
|                                                                                |
|                           +----------------+                                   |
|                           |  Coordinator   |                                   |
|                           +-------+--------+                                   |
|                                   |                                            |
|         +------------+------------+------------+------------+                  |
|         |            |            |            |            |                  |
|         v            v            v            v            v                  |
|  +-----------+ +-----------+ +-----------+ +-----------+ +-----------+         |
|  | Developer | | Developer | | Debugger  | | Quality   | | Technical |         |
|  | (Task 1)  | | (Task 2)  | | (if error)| | Reviewer  | | Writer    |         |
|  +-----------+ +-----------+ +-----------+ +-----------+ +-----------+         |
|         |            |            |            |            |                  |
|         +------------+------------+            |            |                  |
|                      |                         |            |                  |
|                      v                         |            |                  |
|              [Parallel batch                   |            |                  |
|               completes]                       |            |                  |
|                      |                         |            |                  |
|                      +------------------------>+            |                  |
|                                                |            |                  |
|                                    [QR validates            |                  |
|                                     implementation]         |                  |
|                                                |            |                  |
|                                                +----------->+                  |
|                                                             |                  |
|                                                 [TW documents                  |
|                                                  changes]                      |
|                                                             |                  |
+--------------------------------------------------------------------------------+
                                                              |
                                                              v
                                                    [Execution complete
                                                     with retrospective]
```

The coordinator:

- Never writes code directly (delegates to @agent-developer)
- Parallelizes independent work across up to 4 developers
- Sequences dependent milestones
- Runs quality review after implementation
- Generates execution retrospective

---

## The Prompt Engineer Skill

A meta-skill for optimizing prompts themselves. Since this entire workflow
consists of prompts consumed by LLMs, each can be individually optimized.

### Basic Usage

Optimize a simple prompt:

```
User: Use your prompt engineer skill to optimize the following prompt:

      "You are a helpful assistant that writes Python code.
       Be concise and write clean code."
```

### Optimizing Sub-Agents

Optimize a Claude Code sub-agent definition:

```
User: Use your prompt engineer skill to optimize the system prompt for
      the following claude code sub-agent: agents/developer.md
```

### Optimizing Multi-Prompt Workflows

For complex workflows where multiple prompts interact:

```
User: Consider the following Python file. Your task:
      - Identify all different system/user prompts
      - Understand how they interact together
      - Use your prompt engineer skill to optimize each of these individually

      @skills/planner/scripts/planner.py
```

### Full Workflow Optimization

Optimize the entire planning/execution workflow:

```
User: Consider the following tightly integrated workflow:

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

---

## The Decision Critic Skill

LLMs tend toward sycophancy -- agreeing with the user rather than providing
genuine pushback. For important architectural decisions, you want stress-testing,
not validation.

The decision-critic skill forces structured adversarial analysis:

```
+--------------------------------------------------------------------------------+
|                        DECISION CRITIC WORKFLOW                                |
+--------------------------------------------------------------------------------+
|                                                                                |
|  DECOMPOSITION (Steps 1-2)                                                     |
|  +----------------------------------------------------------------------+      |
|  | Extract claims, assumptions, constraints, judgments                  |      |
|  | Assign stable IDs: C1, C2, A1, A2, K1, J1...                         |      |
|  | Classify each: [V]erifiable, [J]udgment, [C]onstraint                |      |
|  +----------------------------------------------------------------------+      |
|                                    |                                           |
|                                    v                                           |
|  VERIFICATION (Steps 3-4)                                                      |
|  +----------------------------------------------------------------------+      |
|  | Generate verification questions for [V] items                        |      |
|  | Answer independently (factored verification)                         |      |
|  | Mark each: VERIFIED | FAILED | UNCERTAIN                             |      |
|  +----------------------------------------------------------------------+      |
|                                    |                                           |
|                                    v                                           |
|  CHALLENGE (Steps 5-6)                                                         |
|  +----------------------------------------------------------------------+      |
|  | Steel-man the strongest argument AGAINST the decision                |      |
|  | Explore alternative problem framings                                 |      |
|  | Surface hidden assumptions in original formulation                   |      |
|  +----------------------------------------------------------------------+      |
|                                    |                                           |
|                                    v                                           |
|  SYNTHESIS (Step 7)                                                            |
|  +----------------------------------------------------------------------+      |
|  | Verdict: STAND | REVISE | ESCALATE                                   |      |
|  | Summary of verified/failed/uncertain items                           |      |
|  | Specific recommendation for next action                              |      |
|  +----------------------------------------------------------------------+      |
|                                                                                |
+--------------------------------------------------------------------------------+
```

### When to Use

Use for important decisions where you want genuine criticism, not agreement:

- Architectural choices with long-term consequences
- Technology selection (language, framework, database)
- Tradeoffs between competing concerns (performance vs. maintainability)
- Decisions you're uncertain about and want stress-tested

### Example Usage

```
User: I'm considering using Redis for our session storage instead of
      PostgreSQL. My reasoning:

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

### The Anti-Sycophancy Design

The skill is grounded in three research-backed techniques:

- **Chain-of-Verification** (Dhuliawala et al., 2023) -- factored verification
  prevents confirmation bias by answering questions independently
- **Self-Consistency** (Wang et al., 2023) -- multiple reasoning paths reveal
  disagreement
- **Multi-Expert Prompting** (Wang et al., 2024) -- diverse perspectives catch
  blind spots

The 7-step structure forces the LLM through adversarial phases rather than
allowing it to immediately agree with your reasoning.

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

This pattern keeps context focused and allows workflows that adapt based on
intermediate results.

---

## Design Principles

**Separation of concerns**: Planning is separate from execution. Analysis is
separate from implementation. Each phase has clear inputs and outputs.

**Explicit decision tracking**: The Planning Context section captures why
decisions were made, what alternatives were rejected, and what risks were
accepted. This survives context clears and new sessions.

**Quality gates**: Technical writer and quality reviewer run before execution
begins, catching issues when they're cheap to fix.

**Hygiene over speed**: Comments are scrubbed for temporal contamination
("Added X" becomes "X handles Y"). Documentation uses tabular indexes, not
prose. These rules prevent cruft accumulation.

**Resumability**: Plans are written to files. Execution can be interrupted and
resumed. Reconciliation detects already-completed milestones.

---

## Acknowledgments

I stood on the shoulders of giants, and [Southbridge Research's exceptional analysis of Claude Code prompts](https://southbridge-research.notion.site/Prompt-Engineering-The-Art-of-Instructing-AI-2055fec70db181369002dcdea7d9e732) has been of tremendous help to kick-start my understanding of how to write effective prompts.
