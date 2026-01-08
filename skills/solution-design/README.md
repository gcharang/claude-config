# Solution Design

When asked to generate solutions, LLMs exhibit predictable failure modes. This
skill counteracts them through perspective-parallel generation, explicit
synthesis, and adversarial challenge.

## The Problem

LLMs fail at solution generation in six ways:

| Failure Mode          | What Happens                                           |
| --------------------- | ------------------------------------------------------ |
| Anchoring             | Proposes familiar patterns regardless of fit           |
| Premature Convergence | Generates minimum viable set, then defends it          |
| Superficial Diversity | "Add Redis" vs "Add Memcached" = one solution, not two |
| Vague Specification   | "Improve error handling" -- gesture, not solution      |
| Hidden Trade-offs     | Costs minimized or omitted                             |
| Missing Synthesis     | Partial insights never combine                         |

This skill forces genuine breadth through parallel sub-agents, each reasoning
from a different mode. It surfaces trade-offs through explicit challenge. It
combines insights through structured synthesis.

## Workflow

```
  Context ----------> Dispatch ----------> Aggregate
  (establish)         (4-6 parallel)       (collect)
       |                   |                   |
       v                   v                   v
  [root cause]        [perspectives]      [solution roster]
       |                   |                   |
       +-------------------+-------------------+
                           |
                           v
                      Synthesize
                   (convergence, tension, themes)
                           |
                           v
                       Challenge
                   (stress-test all)
                           |
                           v
                        Select
                   (rank, recommend)
                           |
                           v
                        Output
                   (final report)
```

| Step       | Question                              | Output                            |
| ---------- | ------------------------------------- | --------------------------------- |
| Context    | What problem are we solving?          | Root cause, constraints, baseline |
| Dispatch   | Which perspectives will be diverse?   | 4-6 parallel sub-agents           |
| Aggregate  | What solutions exist?                 | Deduplicated roster               |
| Synthesize | Where do perspectives agree/conflict? | Convergence, tension, themes      |
| Challenge  | What would make each solution fail?   | Viable vs eliminated              |
| Select     | Which solution fits best?             | Ranked list, trade-off matrix     |
| Output     | What should the user do?              | Final report with recommendations |

## Perspectives

Each perspective is a MODE OF REASONING, not an optimization target.
"Performance-focused" tells you WHAT to value; these perspectives tell you HOW
to think differently.

| Perspective      | Core Question                                                     |
| ---------------- | ----------------------------------------------------------------- |
| Minimal          | What is the smallest change that addresses the root cause?        |
| Structural       | What design change would make this class of problem impossible?   |
| Stateless        | What if we eliminated or dramatically simplified state?           |
| Domain-Modeled   | What concept from the problem domain are we failing to represent? |
| Removal          | What if we removed something instead of adding?                   |
| First Principles | If we derived from fundamental truths, what solution emerges?     |
| Upstream         | What if we solved this earlier in the causal chain?               |

Perspectives are domain-agnostic. They work for software problems, physical
systems (heating, plumbing), organizational challenges, and theoretical
problems. "Minimal Intervention" works whether you're fixing code or a furnace.

## Design Decisions

### Why Perspectives Are Modes of Reasoning

An earlier design used "performance-focused", "security-focused",
"maintainability-focused". Rejected because:

1. These are evaluation criteria, not reasoning strategies
2. The same engineer designing for performance vs maintainability often produces
   structurally similar solutions with different tuning
3. They're domain-specific ("security-focused" doesn't apply to heating systems)

The chosen perspectives employ genuinely different reasoning patterns:

- "Minimal" asks what's the least we can change
- "Removal" asks what we can subtract
- "First Principles" asks what we'd do ignoring convention

These produce structurally different solutions regardless of domain.

### Why Sub-Agent Orchestration

The skill uses parallel sub-agents (one per perspective) rather than a single
agent cycling through perspectives:

1. **Full context per perspective**: Each sub-agent gets the full context window
   to reason deeply. A single agent cycling through perspectives compresses each
   one and anchors on earlier perspectives.

2. **Model selection per perspective**: Minimal benefits from quick reasoning
   (Haiku). First Principles benefits from deeper reasoning (Opus).

3. **Parallel execution**: Five sub-agents complete faster than one agent
   working sequentially.

4. **Proven pattern**: The refactor skill uses identical sub-agent orchestration.

### Why LLM Selects Perspectives

An earlier design used fixed rules: "always include minimal", "include security
if root cause involves untrusted input". Replaced with guidance that lets the
LLM select perspectives based on the specific problem.

Fixed rules cannot anticipate problem variety. The LLM, given guidance about
what each perspective offers, makes better selections than mechanical rules.

### Why Synthesis Is Separate

An earlier design combined aggregation and synthesis. Split because:

1. **Aggregation is mechanical**: collect, deduplicate, note attribution
2. **Synthesis is analytical**: identify patterns, generate cross-cutting solutions

Combining them risks synthesis contaminating aggregation (solutions modified
based on synthesis) or aggregation limiting synthesis (rushing before patterns
emerge).

### Why Synthesized Solutions Are Not Prioritized

Synthesized solutions are hypotheses, not conclusions. A solution combining
insights from three perspectives might combine their strengths--or their blind
spots. Pure solutions have been reasoned through completely within a coherent
perspective. Synthesized solutions are assembled from parts reasoned in
different modes.

Equal treatment prevents gaming. If synthesized solutions ranked higher, the
synthesis step would always produce something, even when artificial.

### Why No Confidence Considerations

By the time solution-design runs, the user has decided to proceed with the
stated problem. Whether problem-analysis reported HIGH or LOW confidence, the
user chose this. The skill generates solutions fully, without reservation.

## Academic Grounding

| Paper                  | Finding                                      | Application                     |
| ---------------------- | -------------------------------------------- | ------------------------------- |
| Multi-Expert Prompting | Multiple perspectives + aggregation improves | Perspective-parallel generation |
| Self-Refine            | Iterative feedback improves quality          | Validate step self-checks       |
| Decomposed Prompting   | Sub-task handlers improve complex tasks      | Sub-agent architecture          |

From Multi-Expert Prompting: "We weight all the experts equally to prevent blind
trust in expert opinions, minimizing the group's vulnerability to biases." This
directly informs equal treatment of pure and synthesized solutions.

## Integration with Problem-Analysis

The skill is designed to consume output from problem-analysis but does not
require it.

**With problem-analysis**: Extract root cause, causal chain, constraints. The
refined problem statement becomes the root cause input.

**Standalone**: User provides problem statement directly. Step 1 extracts or
confirms root cause through analysis.

## Usage

After running problem-analysis:

```
Use your solution-design skill on the root cause from problem-analysis
```

Standalone:

```
Use your solution-design skill to generate solutions for: [problem statement]
```

With explicit constraints:

```
Use your solution-design skill. Problem: [statement]. Must complete in 2 days.
```

## What It Does NOT Do

- Identify problems or root causes (use problem-analysis)
- Implement solutions (generates recommendations only)
- Rank solutions by confidence from upstream analysis
- Force synthesis when perspectives are orthogonal
- Elevate synthesized solutions over pure ones
