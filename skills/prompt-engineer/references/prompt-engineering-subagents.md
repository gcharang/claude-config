# Prompt Engineering: Research-Backed Techniques for Subagent Orchestration

This document synthesizes practical prompt engineering patterns for
**orchestrating multiple LLM calls** in parallel or hierarchical structures.
These techniques target scenarios where an orchestrator decomposes work across
specialized subagents, executes tasks in parallel, or coordinates multiple LLM
instances toward a shared goal.

**Prerequisite**: This guide assumes familiarity with single-turn techniques
(CoT, Plan-and-Solve) and multi-turn refinement patterns (Self-Refine, CoVe).
Subagent orchestration builds on these foundations by distributing cognitive
work across multiple concurrent or specialized LLM calls.

**Meta-principle**: The value of subagent orchestration comes from decomposition
and parallelization—breaking complex tasks into independent units that can be
processed concurrently, then synthesizing results. This trades sequential depth
for parallel breadth.

---

## Technique Selection Guide

| Domain                  | Technique                        | Trigger Condition                                   | Stacks With                          | Conflicts With                 | Cost/Tradeoff                              | Effect                                                          |
| ----------------------- | -------------------------------- | --------------------------------------------------- | ------------------------------------ | ------------------------------ | ------------------------------------------ | --------------------------------------------------------------- |
| **Parallelization**     | Skeleton-of-Thought              | Long-form answers with plannable structure          | Any single-turn technique            | Step-by-step reasoning tasks   | N parallel API calls + synthesis           | 1.89×–2.39× latency reduction; quality maintained or improved   |
| **Parallelization**     | SoT with Router                  | Mixed query types requiring adaptive dispatch       | Skeleton-of-Thought                  | —                              | Router call overhead                       | Enables SoT for suitable queries only                           |
| **Decomposition**       | Least-to-Most Prompting          | Complex problems harder than examples               | Any verification technique           | Single-turn CoT                | 2+ sequential LLM calls                    | SCAN: 99.7% vs 16% standard; enables length generalization      |
| **Decomposition**       | Parallel Sampling                | Multiple valid solution paths exist                 | USC, Complexity Weighting            | Greedy decoding                | N× token cost                              | Enables consistency-based selection                             |
| **Search**              | Tree of Thoughts (BFS)           | Problems requiring exploration with pruning         | State evaluation, backtracking       | Sequential CoT                 | b×T LLM calls (beam × steps)               | Game of 24: 4%→74% vs CoT                                       |
| **Search**              | Tree of Thoughts (DFS)           | Deep exploration with early termination needed      | Value-based pruning                  | Parallel expansion             | Variable; supports backtracking            | Crosswords: 15.6%→60% word accuracy                             |
| **Refinement**          | Explicit Reflection Prompting    | Tool returns error; retry needed                    | Tool-augmented workflows             | Immediate retry                | One reflection step per retry              | Concrete diagnosis improves next attempt                        |
| **Refinement**          | Self-Contrast                    | Self-evaluation unreliable; need implicit verify    | Multi-perspective generation         | Single-path reflection         | 3-stage: perspectives + contrast + reflect | GSM8K +7.8%; reduces invalid reflections 30.8%                  |
| **Refinement**          | Anticipatory Reflection          | Agent tasks with potential early failures           | Tree search, plan execution          | Post-hoc only reflection       | R backup actions per step                  | WebArena: 23.5% success; 45% fewer plan revisions               |
| **Verification**        | Multi-Perspective Self-Consistency | Code generation requiring implicit verification   | Solution + spec + test generation    | Single-perspective voting      | 3-partite graph construction               | HumanEval +15.91%; CodeContests +9.37%                          |
| **Coordination**        | LM² (Decomposer-Solver-Verifier) | Complex reasoning requiring step verification       | Concept generation                   | Monolithic prompting           | 3 models + policy coordination             | MATH: +8.1%; MedQA: +9.7% over baselines                        |
| **Coordination**        | Multi-Expert Prompting           | Open-ended tasks benefiting from diverse expertise  | NGT aggregation                      | Single-expert prompting        | n experts + 7-subtask aggregation          | TruthfulQA: 89.35% SOTA; +8.69% over best baseline              |
| **Role Specialization** | Multi-Role Delegation            | Task requires distinct expertise areas              | Any verification technique           | Monolithic prompting           | Role setup overhead                        | Specialized responses per domain                                |
| **Orchestration**       | Task Decomposition               | Complex task requiring multiple model types         | Any technique                        | Monolithic single-model        | Planning + dispatch overhead               | Enables specialized models per subtask                          |
| **Human-in-Loop**       | Approval Gates                   | Critical tasks requiring human validation           | Any multi-stage pipeline             | Fully autonomous workflows     | Latency for human review                   | 82% plan approval rate in production                            |
| **Feedback**            | Tool-Augmented Refinement        | Code/structured output requiring validation         | Compiler/linter integration          | —                              | Tool execution + retry loops               | Self-correcting syntactic errors                                |

---

## Quick Reference: Key Principles

1. **Skeleton-First for Structured Answers** — 1.89x-2.39x latency reduction
   with maintained or improved quality on suitable tasks
2. **Route Before Dispatching** — SoT degrades math (-0.5x) and coding quality;
   router prevents applying parallelization to unsuitable queries
3. **Independence Enables Parallelism** — Decompose only when subtasks have
   minimal interdependence; dependent chains must remain sequential
4. **Synthesis Requires Full Context** — The final aggregation step must have
   access to all parallel outputs; don't discard intermediate reasoning
5. **Role Prompts Beat Generic Prompts** — Explicit constraints ("only point 3",
   "1-2 sentences", "do not continue") critical for focused subagent behavior
6. **Decompose by Model Capability** — Route subtasks to specialized models
   (vision, code, reasoning) rather than forcing one model to handle all
7. **Latency Optimization != Quality Optimization** — Parallel techniques
   primarily reduce latency; quality gains are task-dependent (improved on
   knowledge, degraded on reasoning)
8. **Tree Search for Exploration** — When problems require trying multiple paths,
   use BFS for breadth or DFS for depth with backtracking
9. **Explicit Reflection Before Retry** — When tools return errors, prompting for
   concrete diagnosis before the next attempt improves retry quality
10. **Verifier Nuance Matters** — Multi-class error feedback (conceptual,
    computational, procedural) outperforms binary pass/fail signals
11. **Concepts Before Decomposition** — Generating prerequisite concepts improves
    out-of-domain generalization
12. **Human Gates for Quality Control** — Strategic human approval points catch
    errors without blocking full autonomy
13. **Least-to-Most for Hard Problems** — Explicit two-stage decomposition enables
    solving problems harder than demonstration examples
14. **Contrast Dissimilar Solutions** — Comparing different (even both incorrect)
    solutions yields better reflection than evaluating single solutions
15. **Anticipate Failures Before Acting** — Generating backup actions before
    execution reduces plan revisions by 45%
16. **Multi-Perspective Verification** — Solution + specification + test case
    consistency outperforms single-perspective voting
17. **Three Experts Optimal** — Multi-expert aggregation peaks at 3 experts;
    more experts can reduce truthfulness
18. **Self Red-Team Against Overconfidence** — Prompting to consider "why opponent
    could win" reduces confidence escalation from 10.34% to 3.05%

---

## 1. Skeleton-of-Thought (SoT)

A latency-reduction technique that generates an answer skeleton first, then
expands each point in parallel. Per Ning et al. (2024): "The idea stems from
reflecting on how humans ourselves answer questions. Humans do not always think
about questions and write answers in a sequential fashion. In contrast, for many
question types, we first derive the skeleton according to some protocols and
strategies, and then add evidence and details to explain each point."

**The two-stage process:**

```
Stage 1 (Skeleton):
  Input: Question
  Output: Numbered list of 3-10 skeleton points (3-5 words each)

Stage 2 (Point-Expanding):
  Input: Question + full skeleton + specific point index
  Output: 1-2 sentence expansion of that single point
  [Execute for all points IN PARALLEL]

Final: Concatenate all point expansions
```

**Skeleton prompt template:**

Per the paper:

```
[User:] You're an organizer responsible for only giving the skeleton (not the
full content) for answering the question. Provide the skeleton in a list of
points (numbered 1., 2., 3., etc.) to answer the question. Instead of writing
a full sentence, each skeleton point should be very short with only 3~5 words.
Generally, the skeleton should have 3~10 points. Now, please provide the
skeleton for the following question.

{question}

Skeleton:

[Assistant:] 1.
```

**Point-expanding prompt template:**

```
[User:] You're responsible for continuing the writing of one and only one
point in the overall answer to the following question.

{question}

The skeleton of the answer is
{skeleton}

Continue and only continue the writing of point {point_index}. Write it
**very shortly** in 1~2 sentence and do not continue with other points!

[Assistant:] {point_index}. {point_skeleton}
```

**Performance by question category:**

Per the paper's evaluation on Vicuna-80:

| Category     | Speed-up | Quality Impact |
| ------------ | -------- | -------------- |
| Knowledge    | 2.33×    | Improved       |
| Generic      | 2.31×    | Improved       |
| Common-sense | 2.24×    | Improved       |
| Writing      | 2.26×    | Maintained     |
| Roleplay     | 1.95×    | Maintained     |
| Coding       | 2.06×    | Degraded       |
| Math         | 1.34×    | Degraded       |

**Why this works:**

Human cognition doesn't always proceed sequentially. For structured answers
(lists, enumerations, multi-aspect explanations), we often plan the structure
first, then elaborate each part. SoT mirrors this cognitive pattern, enabling
parallelization because each point can be elaborated without knowledge of other
points' expansions.

**Non-obvious insight:** The speedup comes from _point independence_, not from
faster individual generation. Each point-expansion call takes similar time to
standard generation—but they execute concurrently. If points depend on each
other, parallelization fails.

**Critical limitation — sequential reasoning incompatibility:**

Per the paper: "The current SoT is suitable for questions that require a long
answer whose structure can be planned ahead, while not suitable for questions
that require step-by-step reasoning or only need a short answer."

SoT assumes point independence. When point N depends on the result of point N-1,
parallel expansion produces incoherent or incorrect answers. Math and coding
tasks typically require such sequential dependencies.

**CORRECT (parallelizable — independent points):**

```
Question: What are the main features of Python?

Skeleton:
1. Dynamic typing
2. Interpreted language
3. Rich standard library
4. Multiple paradigms

Each point can be expanded independently without knowing other expansions.
```

**INCORRECT (not parallelizable — dependent reasoning):**

```
Question: Calculate 15 * 7 + 23

Skeleton:
1. Multiply 15 * 7
2. Add result to 23

Point 2 requires the result of Point 1 — cannot parallelize.
```

---

## 2. SoT with Router (SoT-R)

An extension that uses a routing mechanism to determine whether SoT is
appropriate for a given query before dispatching.

**The routing decision:**

Per the paper: "We directly ask an LLM if the question is suitable for SoT. More
specifically, we ask the LLM if the desired answer is in a list of independent
points."

**Router prompt:**

```
[User:] Does the following question require a response that can be organized
as a list of independent points?

Question: {question}

Answer with only "yes" or "no".
```

**Routing logic:**

```
If Router returns "yes":
  → Execute SoT (skeleton + parallel expansion)
If Router returns "no":
  → Execute normal sequential generation
```

**Router implementation options:**

1. **Prompting Router**: Use GPT-4 or similar to classify query suitability (no
   training required)
2. **Trained Router**: Fine-tune a small classifier (e.g., RoBERTa) on labeled
   examples of suitable/unsuitable queries

Per the paper: "We annotate the LIMA dataset... to train a RoBERTa model...
which has only 120M parameters."

**Why this works:**

Not all queries benefit from decomposition. The router acts as a classifier that
prevents applying the wrong strategy to unsuitable queries. This is a meta-level
optimization: rather than optimizing a single technique, optimize the selection
of techniques.

**Non-obvious insight:** The router itself is cheap (small model or single LLM
call), while the cost of applying SoT to unsuitable queries is high (degraded
quality AND wasted parallel calls). The router's overhead is amortized across
many queries.

**Performance:**

SoT-R achieves speed-ups while filtering out queries where SoT would degrade
quality. The net effect is both faster average latency AND maintained or
improved quality across mixed query distributions.

---

## 3. Tree of Thoughts (ToT)

A deliberate problem-solving framework that explores multiple reasoning paths
through tree search. Per Yao et al. (2023): "ToT allows LMs to perform
deliberate decision making by considering multiple different reasoning paths
and self-evaluating choices to decide the next course of action, as well as
looking ahead or backtracking when necessary to make global choices."

**Core concept:**

ToT frames problem-solving as search through a tree where each node represents
a partial solution state. Unlike Chain-of-Thought (which follows a single
reasoning path), ToT maintains and explores multiple paths simultaneously,
using LLM self-evaluation as the search heuristic.

**The four design dimensions:**

1. **Thought decomposition** — How to break intermediate steps into "thoughts"
2. **Thought generation** — How to generate candidate thoughts at each state
3. **State evaluation** — How to score states for search prioritization
4. **Search algorithm** — BFS or DFS depending on problem structure

**Thought decomposition:**

A "thought" should be:
- Small enough that the LLM can generate diverse, promising samples
- Large enough that the LLM can evaluate its prospect toward solving the problem

Per the paper's examples:

| Task             | Thought Granularity        |
| ---------------- | -------------------------- |
| Game of 24       | One equation (e.g., 4+9=13)|
| Creative Writing | A paragraph plan           |
| Crosswords       | One word fill              |

**Thought generation strategies:**

**(a) Sample i.i.d. (for rich thought spaces):**

```
Generate k independent thoughts from the same prompt.
Works when thought space is large (e.g., paragraph-level planning).
```

**(b) Propose sequentially (for constrained thought spaces):**

```
Generate k thoughts in a single prompt that proposes alternatives.
Works when thought space is small (e.g., single words, equations).
Avoids duplication that i.i.d. sampling might produce.
```

**Propose prompt example (Game of 24):**

```
[User:] Given the numbers {remaining_numbers}, list all possible next steps
(one arithmetic operation) that could lead toward making 24.

Possible next steps:
```

**State evaluation strategies:**

**(a) Value each state independently:**

```
Prompt the LLM to classify each state as "sure", "likely", or "impossible"
based on whether it can lead to a solution.
```

**Value prompt example:**

```
Evaluate if the given numbers can reach 24 (sure/likely/impossible).
10 14: 10 + 14 = 24. sure
3 3 8: 3 * 8 = 24, 24 - 3 = 21. impossible
...
{current_numbers}:
```

**(b) Vote across states:**

```
Present multiple candidate states and ask which is most promising.
Better when direct valuation is hard (e.g., creative coherence).
```

**Vote prompt example:**

```
Given the instruction and several choices, analyze each choice in detail,
then conclude "The best choice is {s}" where s is the choice number.

Instruction: {original_task}
Choices:
1. {state_1}
2. {state_2}
...
```

**Search algorithms:**

**(a) Breadth-First Search (BFS):**

```python
# Maintain b best states per step
def ToT_BFS(x, G, V, T, b):
    S = {x}  # Initial state
    for t in range(T):
        # Generate candidates from all current states
        S_prime = {(s, z) for s in S for z in G(s, k)}
        # Evaluate all candidates
        values = V(S_prime)
        # Keep top b
        S = top_b(S_prime, values, b)
    return best(S)
```

Use BFS when:
- Tree depth is limited (T ≤ 3)
- Early pruning is effective (can eliminate bad states quickly)
- Want to maintain diversity of solutions

**(b) Depth-First Search (DFS):**

```python
# Explore most promising path first, backtrack when stuck
def ToT_DFS(s, t, G, V, T, v_threshold):
    if t > T:
        return s  # Terminal
    for s_prime in sorted(G(s, k), key=V, reverse=True):
        if V(s_prime) > v_threshold:
            result = ToT_DFS(s_prime, t+1, G, V, T, v_threshold)
            if result: return result
    return None  # Backtrack
```

Use DFS when:
- Solution depth is variable (some paths terminate early)
- State evaluation can reliably identify "impossible" states
- Want to find first valid solution quickly

**Performance results:**

| Task             | CoT      | ToT (b=5) | Improvement |
| ---------------- | -------- | --------- | ----------- |
| Game of 24       | 4%       | 74%       | 18.5×       |
| Creative Writing | 6.93     | 7.56      | +9%         |
| Crosswords (word)| 15.6%    | 60%       | 3.8×        |

**Cost considerations:**

Per the paper: "ToT requires significantly more computations than IO or CoT
prompting." For Game of 24, ToT uses ~5.5k tokens per problem vs ~67 tokens
for single CoT. The tradeoff is justified when:

- Base accuracy is low (CoT struggles significantly)
- Task requires exploration (multiple valid approaches exist)
- Backtracking is valuable (early mistakes are recoverable)

**When NOT to use ToT:**

- Simple tasks where CoT already achieves high accuracy
- Tasks without clear intermediate states to evaluate
- Latency-critical applications (ToT is slower than single-pass)

**CORRECT (ToT-suitable — requires exploration):**

```
Task: Game of 24 with numbers [4, 9, 10, 13]
- Multiple valid paths exist
- Each step can be evaluated (does this lead toward 24?)
- Backtracking is valuable (try different operations)
```

**INCORRECT (ToT unsuitable — no exploration benefit):**

```
Task: "What is the capital of France?"
- Single correct answer
- No intermediate states to explore
- Standard prompting suffices
```

---

## 4. Reflection and Introspection Patterns

This section covers techniques for improving retry quality and enabling agents
to learn from failures within a session.

### 4.1 Explicit Reflection Prompting

A within-session technique for improving retry quality when tool execution fails.
Derived from Reflexion (Shinn et al. 2023), scoped to patterns that work without
custom orchestration infrastructure.

**Core insight:**

When a tool returns an error or an attempt fails, the default behavior is to
immediately retry. Inserting an explicit reflection step—forcing the model to
articulate what went wrong—improves the next attempt. The mechanism: verbalized
diagnosis becomes explicit context that conditions the next generation.

**The within-session pattern:**

```
Attempt 1: Generate solution → Execute via tool → Error returned
Reflection: Explicit analysis of failure cause
Attempt 2: Generate solution conditioned on reflection → Execute → ...
```

This differs from full Reflexion (which requires cross-episode memory and custom
orchestration) in that the conversation context itself serves as memory. No
external infrastructure needed.

**Reflection prompt template:**

```
The previous attempt failed with:
{error_output}

Before generating a new solution:
1. Identify the specific cause of failure
2. Explain what assumption or approach was incorrect
3. Describe concretely how your next attempt will differ

Then provide the revised solution.
```

**Concrete reflection vs. vague acknowledgment:**

The quality distinction matters. Useful reflections contain specific diagnoses
and actionable alternatives, not generic statements.

```
# POOR REFLECTION (vague, non-actionable)
"The code failed. I should fix the bug and try again."
"I need to be more careful with the implementation."

# USEFUL REFLECTION (specific, actionable)
"The code failed because I used 0-indexed iteration but the input is
1-indexed. The next attempt must adjust loop bounds: start from 1,
end at n+1 instead of n."

"The test failed because I assumed the input list is non-empty.
I need to add a guard clause checking len(items) > 0 before accessing
items[0]."
```

The prompt should demand specificity. Phrases like "identify the specific cause"
and "describe concretely how" push toward actionable reflection.

**Scope limitations:**

Expect diminishing returns after 2-3 reflection-informed retries within a
session. If the task isn't solved by then, the problem is likely:

- Missing information the model doesn't have access to
- Fundamental approach mismatch requiring different strategy
- Ambiguous requirements needing clarification

The Reflexion paper's multi-trial gains came from cross-episode accumulation
(learning across many similar problems), which requires persistent memory
infrastructure. Within a single session, you capture the immediate benefit of
structured failure analysis but not the accumulated learning effect.

### 4.2 Anticipatory Reflection (Devil's Advocate)

A three-fold introspection pattern that proactively prepares for failures before
they occur. Per Wang et al. (2024): "We introduce a novel approach that equips
LLM agents with introspection, enhancing consistency and adaptability in solving
complex tasks."

**Core innovation:**

Instead of reflecting only after failures (post-hoc), anticipatory reflection
generates backup actions _before_ execution. If the primary action fails, the
agent can immediately try alternatives without regenerating a new plan.

**The three-layer introspection:**

```
Layer 1 (Pre-Action): Before executing action aₜ
  → Generate R alternative "remedy" actions [a¹ₜ, a²ₜ, ..., aᴿₜ]
  → Push all to stack with primary action on top

Layer 2 (Post-Action): After executing action aₜ
  → Evaluate: Does result align with subtask objective?
  → If misaligned: Pop next remedy from stack, backtrack

Layer 3 (Plan Revision): Upon plan failure (stack empty, task incomplete)
  → Review full action history and notes
  → Generate refined plan for next episode
```

**Anticipatory reflection prompt:**

```
You are about to execute: {action}

If your action above is not correct, the next action should be:
[Generate R alternative actions]
```

**Post-action alignment prompt:**

```
Current subtask: {subtask_objective}
Action taken: {action}
Resulting state: {new_state}

Does the new state align with the subtask objective?
Answer: [yes/no]
If no, explain what went wrong.
```

**Why this works:**

Traditional reflection performs trials sequentially—one error corrected per
full pass. Anticipatory reflection branches at decision points, enabling
multiple alternatives to be tried within a single plan execution. This reduces
the need for costly plan revisions.

**Performance results (WebArena):**

| Method                    | Success Rate | Plan Revisions |
| ------------------------- | ------------ | -------------- |
| Plan + Act (no reflection)| 19.8%        | 2.03           |
| Plan + Act + Reflection   | 20.0%        | 1.89           |
| LATS (tree search)        | 22.7%        | 1.16           |
| Anticipatory Reflection   | 23.5%        | 0.64           |

**Key finding — Efficiency gain:**

Anticipatory reflection reduces plan revisions by 45% compared to standard
reflection approaches. The number of actions per trial increases (6.39 → 7.07),
indicating more thorough plan execution before revision.

**When to use anticipatory reflection:**

- Agent tasks with multiple valid action paths
- Environments where backtracking is inexpensive
- Tasks where early mistakes are recoverable

**When NOT to use:**

- Single-path deterministic tasks
- Tasks where actions have irreversible consequences
- Simple tasks where standard prompting suffices

---

## 5. Least-to-Most Prompting

A two-stage decomposition technique that enables solving problems harder than
the demonstration examples. Per Zhou et al. (2023): "The key idea in this
strategy is to break down a complex problem into a series of simpler subproblems
and then solve them in sequence."

**Core distinction from Plan-and-Solve:**

Plan-and-Solve generates plan and solution in a single LLM call. Least-to-Most
uses **separate LLM calls** for decomposition and solving, with each subproblem
solution becoming context for the next. This staged approach enables length
generalization—solving problems requiring more steps than examples demonstrate.

**The two-stage process:**

```
Stage 1 (Decomposition):
  Input: Problem + few-shot decomposition examples
  Output: Ordered list of subproblems (easiest to hardest)

Stage 2 (Sequential Solving):
  For each subproblem in order:
    Input: Few-shot solving examples + previously solved subproblems + current subproblem
    Output: Solution to current subproblem
    → Append solution to context for next iteration
```

**Decomposition prompt template:**

```
Q: "think, machine, learning"
A: "think", "think, machine", "think, machine, learning"

Q: {problem}
A:
```

The decomposition creates a sequence where each element builds on the previous.

**Sequential solving prompt template:**

```
Q: "think, machine"
A: The last letter of "think" is "k". The last letter of "machine" is "e".
   Concatenating "k", "e" leads to "ke". So, "think, machine" outputs "ke".

Q: "think, machine, learning"
A: "think, machine" outputs "ke". The last letter of "learning" is "g".
   Concatenating "ke", "g" leads to "keg". So, "think, machine, learning"
   outputs "keg".

[Previous subproblem solutions appended here]

Q: {current_subproblem}
A:
```

**Critical insight — Context accumulation:**

Each solved subproblem is appended to the context before solving the next. This
creates a chain where later subproblems can reference earlier solutions. The
pattern is analogous to induction: demonstrate base case + recursive step, then
the model generalizes.

**Performance results:**

| Task                    | Chain-of-Thought | Least-to-Most | Improvement |
| ----------------------- | ---------------- | ------------- | ----------- |
| Last-letter (12 words)  | 7.7%             | 94.0%         | 12.2×       |
| SCAN (length split)     | 16.0%            | 99.7%         | 6.2×        |
| DROP (non-football)     | 74.77%           | 82.45%        | +7.68pp     |
| GSM8K (≥5 steps)        | 39.07%           | 45.23%        | +6.16pp     |

**Why this enables generalization:**

Per the paper: "Given a new list, we first append it to the exemplar... to
obtain the list's decomposition. Then, we construct for each sublist S a
solution prompt, which consists of the exemplars, followed by the previous
sublist/response pairs (if any), followed by S."

The exemplars demonstrate the pattern; context accumulation enables applying
it to arbitrarily long sequences.

**Limitation — Domain-specific decomposition:**

Per the paper: "Decomposition prompts typically don't generalize well across
different domains. For instance, a prompt that demonstrates decomposing math
word problems isn't effective for teaching large language models to break down
common sense reasoning problems."

Each domain requires its own decomposition examples.

**When to use Least-to-Most:**

- Problems harder than demonstration examples
- Tasks requiring compositional generalization
- Sequential problems where later steps depend on earlier ones

**When to use Plan-and-Solve instead:**

- Problems at similar complexity to examples
- Token efficiency is critical (single call preferred)
- Decomposition pattern is straightforward

**CORRECT (Least-to-Most suitable — compositional):**

```
Task: Translate "jump around left twice" to actions

Decomposition:
1. "jump left" → TURN LEFT JUMP
2. "jump around left" → (TURN LEFT JUMP) × 4
3. "jump around left twice" → ((TURN LEFT JUMP) × 4) × 2

Each subproblem solution feeds into the next.
```

**INCORRECT (Least-to-Most overhead unjustified):**

```
Task: "What is 2 + 3?"

Simple enough that single-turn CoT suffices.
Decomposition overhead provides no benefit.
```

---

## 6. Self-Contrast: Contrastive Reflection

A three-stage technique that improves reflection quality by contrasting multiple
solution perspectives rather than directly evaluating a single solution. Per
Zhang et al. (2024): "Self-Contrast adaptively explores diverse solving
perspectives tailored to the request, contrasts the differences, and summarizes
these discrepancies into a checklist which could be used to re-examine and
eliminate discrepancies."

**The problem with direct self-evaluation:**

Standard reflection asks the model to evaluate its own solution. Research shows
this produces:
- **Overconfident feedback** (46.7%): Insisting previous solution is correct
- **Inconsistent feedback** (45.7%): Different evaluations on repeated attempts
- **Accurate identification** (only 6.9%): Correctly identifying actual errors

**Core insight:**

Contrasting _differences between_ solutions is easier and more reliable than
directly evaluating correctness. Even when both solutions are wrong, if their
errors differ, the contrast reveals potential issues.

**The three-stage process:**

```
Stage 1 (Create Diverse Perspectives):
  Input: Problem
  Action: LLM generates N different solving prompts (perspectives)
  Output: N solutions from N perspectives

Stage 2 (Contrast Discrepancies):
  Input: Pairs of solutions with significant differences
  Action: LLM identifies specific differences and reasons
  Output: Difference analysis + checklist for re-examination

Stage 3 (Eliminate Discrepancies):
  Input: Original solutions + difference analysis + checklist
  Action: LLM reflects using checklist, revises solutions
  Output: Consistent, refined solution
```

**Self-curated perspective generation prompt:**

```
Given the user's request, design {N} different prompts that approach solving
this problem from distinct perspectives. Each perspective should have:
- A unique role, personality, or thinking style
- A different methodology or angle

Request: {problem}

Generate perspectives:
```

**Contrastive analysis prompt:**

```
Compare the following two solutions and identify their differences:

Solution 1: {solution_1}
Solution 2: {solution_2}

Analysis questions:
1. What are the different solving objectives between the solutions?
2. Where are the differences in their solution steps?
3. Why are the answers different?

Based on these differences, generate a checklist for re-examining:
Checklist:
□ {directive_1}
□ {directive_2}
...
```

**Reflection with checklist prompt:**

```
Given a problem, multiple inconsistent solutions, their differences, and
a checklist. Revise the inconsistent solving steps for each solution,
eliminate the differences, and output a new solving process.

Guidance:
1. Check carefully according to the checklist requirements
2. Ensure all revised solutions have the same answer

Problem: {problem}
Solutions: {solutions}
Differences: {differences}
Checklist: {checklist}

Revised solution:
```

**Performance results:**

| Model   | Benchmark | Self-Reflection | Self-Contrast | Improvement |
| ------- | --------- | --------------- | ------------- | ----------- |
| GPT-3.5 | GSM8K     | -0.8%           | +7.8%         | +8.6pp      |
| GPT-3.5 | SVAMP     | +0.7%           | +9.2%         | +8.5pp      |
| L-70B   | GSM8K     | -1.2%           | +11.6%        | +12.8pp     |

**Key finding — Contrasting incorrect solutions is instructive:**

Per the paper's controlled experiment:

| Strategy                                    | Accuracy |
| ------------------------------------------- | -------- |
| Self-evaluate one incorrect solution        | 70.1%    |
| Contrast correct + incorrect               | 83.6%    |
| Contrast two incorrect (similar errors)     | 70.9%    |
| Contrast two incorrect (different errors)   | 75.5%    |

Contrasting solutions with _different_ errors improves reflection even when
both are wrong. The errors "cancel out" through comparison.

**Key finding — Invalid and toxic reflections reduced:**

| Metric              | Self-Reflection | Self-Contrast | Reduction |
| ------------------- | --------------- | ------------- | --------- |
| Invalid (✗→✗)       | 269 cases       | 186 cases     | 30.8%     |
| Toxic (✓→✗)         | 52 cases        | 11 cases      | 78.9%     |

Self-Contrast substantially reduces both failed corrections and accidental
degradations of correct answers.

**When to use Self-Contrast:**

- Tasks where self-evaluation produces overconfident/inconsistent feedback
- Problems with multiple valid solving approaches
- Scenarios where diverse perspectives yield different solutions

**When NOT to use:**

- Tasks with single deterministic solution path
- Time-critical applications (3-stage overhead)
- Very simple problems where direct evaluation suffices

---

## 7. Multi-Perspective Self-Consistency (MPSC)

A graph-based verification framework that evaluates code solutions through three
complementary perspectives: solutions, specifications, and test cases. Per Huang
et al. (2024): "We propose the Multi-Perspective Self-Consistency (MPSC)
framework that incorporates both inter- and intra-consistency across outputs
from multiple perspectives."

**Core concept:**

Instead of generating only solutions and voting, MPSC generates three types of
outputs that can verify each other:
- **Solutions**: Code implementing the functionality
- **Specifications**: Pre/post-conditions describing valid behavior
- **Test cases**: Input-output pairs demonstrating expected behavior

These form a 3-partite graph where edges represent agreement between perspectives.

**The three perspectives:**

```
Solution:        def median(l): return sorted(l)[len(l)//2]
Specification:   preconditions(l): assert isinstance(l, list)
                 postconditions(l, out): assert num_greater == num_less
Test case:       assert median([-10, 4, 6, 1000, 10, 20]) == 8.0
```

**Inter-consistency measurement:**

Edges connect outputs from different perspectives based on agreement:
- Solution ↔ Test case: Does solution pass the test?
- Solution ↔ Specification: Does solution satisfy pre/post-conditions?
- Specification ↔ Test case: Does test case satisfy the specification?

```python
# Solution ↔ Test case consistency
def check_solution_test(solution, test_case):
    try:
        output = solution(test_case['input'])
        return output == test_case['output']
    except:
        return False

# Solution ↔ Specification consistency
def check_solution_spec(solution, spec, casual_inputs):
    pass_results = []
    for input in casual_inputs:
        try:
            output = solution(input)
            spec.postconditions(input, output)
            pass_results.append(True)
        except:
            pass_results.append(False)
    return sum(pass_results) / len(pass_results)
```

**Intra-consistency measurement:**

Within each perspective, outputs are grouped by structural equivalence—outputs
with identical edge patterns to other perspectives are considered consistent.

**Graph-based selection:**

```
1. Generate I solutions, J specifications, K test cases
2. Construct 3-partite graph with inter-consistency edges
3. Compute intra-consistency scores within each perspective
4. Optimize score function balancing inter- and intra-consistency
5. Select solution with highest score
```

**Performance results:**

| Benchmark    | ChatGPT | +MPSC   | Improvement |
| ------------ | ------- | ------- | ----------- |
| HumanEval    | 68.38%  | 84.29%  | +15.91pp    |
| HumanEval+   | 58.75%  | 73.47%  | +14.72pp    |
| MBPP         | 66.80%  | 73.23%  | +6.43pp     |
| CodeContests | 2.57%   | 11.94%  | +9.37pp     |

MPSC with ChatGPT surpasses GPT-4 baseline on HumanEval.

**Key finding — Verification property quality doesn't drive gains:**

| Perspective   | Accuracy |
| ------------- | -------- |
| Solutions     | 68.38%   |
| Specifications| 45.93%   |
| Test cases    | 63.82%   |

Specifications and test cases are individually _worse_ than solutions, yet MPSC
improves results. The gains come from consistency relationships, not from using
better verification properties.

**Ablation — Both perspectives matter:**

| Configuration         | HumanEval |
| --------------------- | --------- |
| Full MPSC             | 83.38%    |
| w/o Specification     | 82.32%    |
| w/o Test case         | 78.30%    |
| w/o Both (baseline)   | 68.38%    |

Test cases contribute more than specifications, likely because generating
accurate test cases is simpler than abstracting comprehensive specifications.

**When to use MPSC:**

- Code generation tasks
- Tasks where execution-based verification is possible
- Scenarios benefiting from implicit consistency checking

**When NOT to use:**

- Non-code tasks without executable verification
- Tasks where specification/test generation is unreliable
- Latency-critical applications (graph construction overhead)

---

## 8. Multi-Expert Prompting

A single-turn aggregation technique that simulates multiple domain experts and
combines their responses using the Nominal Group Technique (NGT). Per Long et
al. (2024): "Multi-expert Prompting guides an LLM to fulfill an input instruction
by simulating multiple experts, aggregating their responses, and selecting the
best among individual and aggregated responses."

**Core architecture:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MULTI-EXPERT PROMPTING                          │
├─────────────────────────────┬───────────────────────────────────────┤
│  Step 1: Expert Generation  │  Step 2: Response Aggregation (NGT)   │
├─────────────────────────────┼───────────────────────────────────────┤
│ Generate n expert identities│ S1: Generate consensus viewpoints     │
│ (one-sentence descriptions) │ S2: Identify conflicting viewpoints   │
│                             │ S3: Resolve conflicts using knowledge │
│ Each expert responds        │ S4: Collect unique viewpoints         │
│ independently to instruction│ S5: Gather all viewpoints             │
│                             │ S6: Generate aggregated response      │
│                             │ S7: Select best (individual or agg.)  │
└─────────────────────────────┴───────────────────────────────────────┘
```

**Expert generation prompt:**

```
Given the following instruction, generate {n} diverse expert identities
that are best suited to answer it. For each expert, provide:
- Expert name/role
- One-sentence description of their expertise

Instruction: {instruction}

Experts:
```

**Key insight — Short descriptions suffice:**

Per the paper: "One-sentence description for an expert identity is effective,
compared to a paragraph-long description as used in ExpertPrompting." The
performance difference is negligible, making short descriptions more efficient.

**Expert response generation:**

```
You are {expert_identity}: {expert_description}

Given your expertise, respond to the following instruction:
{instruction}

Response:
```

**Seven-subtask aggregation (NGT-based):**

```
Given {n} expert responses to: {instruction}

Expert 1 ({identity_1}): {response_1}
Expert 2 ({identity_2}): {response_2}
...
Expert n ({identity_n}): {response_n}

Perform the following subtasks:

S1. Generate consensus: List viewpoints that all experts agree on.

S2. Identify conflicts: List viewpoints where experts disagree.

S3. Resolve conflicts: For each conflict, determine the most accurate
    viewpoint using your knowledge.

S4. Collect unique viewpoints: List valuable viewpoints mentioned by
    only one expert.

S5. Gather all viewpoints: Combine S1, S3 (resolved), and S4.

S6. Generate aggregated response: Compose a comprehensive response
    integrating all gathered viewpoints.

S7. Select best response: Choose the most factual and useful response
    from [Expert 1, Expert 2, ..., Expert n, Aggregated].

Final response:
```

**Performance results:**

| Model   | Baseline Best | Multi-Expert | Improvement |
| ------- | ------------- | ------------ | ----------- |
| ChatGPT | 80.66%        | 89.35%       | +8.69pp     |
| Mistral | 81.88%        | 87.15%       | +5.27pp     |

Multi-Expert achieves SOTA on TruthfulQA-Generation (89.35%), surpassing
previous best of 87.97%.

**Key finding — Three experts is optimal:**

| # Experts | TruthfulQA | FactualityPrompt | BOLD  |
| --------- | ---------- | ---------------- | ----- |
| 1         | 80.05%     | 5.13/10.75       | 0.129 |
| 2         | 88.00%     | 5.17/9.57        | 0.000 |
| 3 (Ours)  | 89.35%     | 4.54/9.45        | 0.000 |
| 5         | 85.92%     | 4.90/10.89       | 0.000 |
| 10        | 84.82%     | 6.24/10.41       | 0.000 |

More than 3 experts can reduce truthfulness—excessive input may divert from
optimal output. However, ≥2 experts significantly decreases toxicity.

**Key finding — Aggregated response usually selected:**

| Dataset          | Aggregated Selected |
| ---------------- | ------------------- |
| TruthfulQA       | 95.44%              |
| FactualityPrompt | 92.40%              |
| BOLD             | 100%                |
| ExpertQA         | 97.53%              |

In >90% of cases, the aggregated response is selected over individual expert
responses, validating the aggregation quality.

**When to use Multi-Expert:**

- Open-ended questions benefiting from multiple viewpoints
- Tasks requiring balanced perspectives (ethics, policy)
- Scenarios where single-expert bias is problematic

**When NOT to use:**

- Tasks with single correct factual answer
- Time-critical applications (aggregation overhead)
- Domains where LLM expert simulation is unreliable

---

## 9. Parallel Sampling for Aggregation

When multiple valid reasoning paths exist, parallel sampling generates diverse
candidates for downstream selection or synthesis. This pattern underlies
techniques like Self-Consistency and Universal Self-Consistency.

**The process:**

```
Stage 1 (Parallel Generation):
  Issue N concurrent LLM calls with temperature > 0
  Collect: [response_1, response_2, ..., response_N]

Stage 2 (Aggregation):
  Method A: Majority voting (for extractable answers)
  Method B: USC selection (for free-form responses)
  Method C: Meta-reasoning synthesis (for evidence combination)
```

**Implementation considerations:**

For API-based models, parallel sampling is achieved through concurrent API
calls. Per Ning et al.: "For proprietary models with only API access, we can
issue multiple parallel API calls to get an end-to-end latency gain at the cost
of an increased number of API requests and tokens."

For local models, batched inference achieves similar parallelism: "Running LLM
inference with increased batch sizes does not increase the per-token latency
much. Therefore, SoT allows us to decode roughly B× more tokens within the same
amount of time if we parallelly decode B points."

**Why this works:**

Sampling with temperature > 0 explores multiple solution paths. Some paths find
correct answers that greedy decoding misses. Aggregation filters out incorrect
paths through consistency or verification, keeping the best of multiple
attempts.

**Non-obvious insight:** Parallel sampling trades compute for quality, but the
tradeoff is non-linear. Accuracy gains diminish rapidly after ~8 samples. Beyond
this, you're mostly paying for redundant correct answers rather than discovering
new correct paths.

**Optimal sample count:**

Per Universal Self-Consistency research: 8 samples provides a reliable balance
between accuracy gains and diminishing returns from additional samples.

---

## 10. LM² (Language Model Multiplex): Coordinated Multi-Model Reasoning

A framework that modularizes decomposition, solution, and verification into
three coordinated language models. Per Juneja et al. (2024): "LM² modularizes
the decomposition, solution, and verification into three different language
models... these models are trained to coordinate using policy learning."

**Core architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                           LM²                                    │
├────────────────┬─────────────────┬──────────────────────────────┤
│   Decomposer   │     Solver      │       Verifier               │
│   (finetuned)  │   (frozen API)  │      (finetuned)             │
├────────────────┼─────────────────┼──────────────────────────────┤
│ 1. Generate    │ Answer each     │ Classify error type:         │
│    concepts    │ subquestion     │ - Conceptual                 │
│ 2. Generate    │ given concepts  │ - Computational              │
│    subquestions│ and prior       │ - Procedural                 │
│    step-by-step│ context         │ - Misunderstood question     │
│                │                 │ - Position of mistake        │
│                │                 │ - No mistake                 │
└────────────────┴─────────────────┴──────────────────────────────┘
```

**Key innovation — Concept generation:**

Before decomposing into subquestions, the decomposer generates prerequisite
concepts (theorems, formulas, domain knowledge) required to solve the problem.
This primes the solver with relevant knowledge.

**Concept generation prompt:**

```
I have a question's solution, tell me all the specific concepts, theorems
and formulas (separated by a comma) used in it.

Question: How many primes are in the row of Pascal's Triangle that starts
with a 1 followed by a 6?

Answer: [solution with reasoning]

Concepts: Coefficients in Pascal's Triangle, Binomial Coefficients Formula,
Prime Numbers
```

**Key innovation — Nuanced verification:**

Instead of binary pass/fail, the verifier classifies errors into 9 categories:

1. Conceptual mistakes (wrong concept applied)
2. Computational mistakes (calculation errors)
3. Procedural mistakes (wrong steps followed)
4. Misunderstood question
5. Mistake in first step
6. Mistake in first half
7. Mistake in second half
8. Mistake in last step
9. No mistake

**Verifier prompt:**

```
You are a teacher grading a student's answer.

Student's answer: {solver_output}
Correct answer: {ground_truth}

Classify the mistake into categories:
1. Conceptual Mistakes
2. Computational Mistakes
3. Procedural Mistakes
4. Mistake in understanding the question
5. Mistake in the first step
6. Mistake in the first half
7. Mistake in the second half
8. Mistake in the last step
9. No mistake

Provide feedback in <feedback> tags with category numbers.
```

**Inference process:**

```
1. Input question Q
2. Decomposer generates concepts C
3. Decomposer generates first subquestion SQ₁ given (Q, C)
4. Solver answers SQ₁ → SA₁
5. Verifier checks SA₁:
   - If error in early step/conceptual/procedural/misunderstood:
     → Regenerate SQ (decomposer adjusts approach)
   - If computational or later-step error:
     → Proceed (minor corrections possible later)
   - If no mistake:
     → Add (SQ₁, SA₁) to context, continue
6. Decomposer generates SQ₂ given (Q, C, SQ₁, SA₁)
7. Repeat until complete
8. Solver generates final answer given full context
```

**Why nuanced verification matters:**

Different error types warrant different responses:

| Error Type              | Response Strategy                        |
| ----------------------- | ---------------------------------------- |
| Conceptual              | Regenerate subquestion (wrong approach)  |
| Computational           | Proceed (can be fixed; tool-assisted)    |
| Procedural              | Regenerate (following wrong process)     |
| Misunderstood question  | Rephrase subquestion more clearly        |
| First-step mistake      | High penalty; regenerate immediately     |
| Later-step mistake      | Lower penalty; may self-correct          |

**Performance results:**

| Dataset  | Best Baseline | LM²    | Improvement |
| -------- | ------------- | ------ | ----------- |
| MATH     | DaSLaM        | +8.1%  | Across subtasks |
| JEEBench | DaSLaM        | +7.71% | Out-of-domain |
| MedQA    | DSP           | +9.7%  | Out-of-domain |

**Key finding — Concepts drive generalization:**

Removing concept generation drops accuracy by 17.5% on Chemistry (out-of-domain)
vs 6% on Math (in-domain). Concepts are critical for generalization.

---

## 11. Role-Specialized Subagents

Assigning distinct roles to different LLM calls enables specialized handling of
subtask types. This pattern appears in Multi-Expert Prompting and multi-agent
debate frameworks.

**Role assignment prompt pattern:**

```
[System:] You are an expert {role_name} with the following responsibilities:
{role_description}

Your task is to {specific_subtask} while staying in strict accordance with
your expertise. Do not address aspects outside your specialization.

[User:] {task_input}
```

**Why this works:**

Generic prompts ("answer this question") leave the model to decide scope and
focus. Role-specific prompts constrain the decision space, focusing the model on
its designated subtask. This is analogous to division of labor in human
teams—specialists outperform generalists on their domain.

**Non-obvious insight:** The role description must include _explicit
constraints_, not just identity. "You are a legal expert" is weaker than "You
are responsible for ONLY the legal implications. Do not address technical or
financial aspects." The constraint is what creates focus.

**CORRECT (explicit role constraints):**

```
You are responsible for continuing the writing of one and only one
point in the overall answer. Continue and only continue the writing
of point 3. Write it very shortly in 1-2 sentences and do not
continue with other points!
```

**INCORRECT (vague role):**

```
You are an expert. Help answer this question.
```

**Role coordination patterns:**

1. **Parallel-then-Aggregate**: All roles respond independently; aggregator
   synthesizes
2. **Sequential Handoff**: Each role builds on previous role's output
3. **Debate/Critique**: Roles challenge each other's outputs iteratively

Per Multi-Expert Prompting: "Multi-expert Prompting distinguishes itself by
aggregating expert responses in a single turn without iterative refinement."

---

## 12. Task Decomposition Orchestration

A pattern where a controller LLM decomposes complex tasks and routes subtasks to
specialized models. Per Shen et al. (2023) in HuggingGPT: "We present
HuggingGPT, a system that leverages large language models (LLMs) to connect
various AI models in machine learning communities... to solve complicated AI
tasks."

**The four-stage pipeline:**

```
Stage 1 (Task Planning):
  Input: User request
  Output: Structured task list with dependencies

Stage 2 (Model Selection):
  Input: Each subtask
  Output: Best-fit model from available pool

Stage 3 (Task Execution):
  Input: Subtask + selected model
  Output: Subtask result
  [Execute subtasks respecting dependency order]

Stage 4 (Response Generation):
  Input: All subtask results
  Output: Integrated final response
```

**Task planning prompt pattern:**

Per the paper:

```
The AI assistant can parse user input to several tasks:
[{"task": task, "id": task_id, "dep": dependency_task_ids, "args": arguments}]

The "dep" field denotes the ids of the previous tasks which generate
resources that the current task relies on. The "args" field must be
in the format: {"resource": resource}

Parse the user request into structured tasks.
```

**Model selection criteria:**

Per the paper: "We parse the descriptions of these models, and use these parsed
results to construct prompts for in-context task-model assignment."

Selection factors:

1. **Task type alignment**: Match model capabilities to subtask requirements
2. **Resource constraints**: Consider model size, latency, cost
3. **Input/output compatibility**: Ensure model can process the subtask format

**Why this works:**

No single model excels at all tasks. Vision models handle images; code models
handle programming; reasoning models handle logic. Task decomposition
orchestration routes each subtask to its optimal solver, combining specialist
strengths.

**Non-obvious insight:** The planning stage is the critical bottleneck—if task
decomposition is wrong, even perfect model selection and execution produce wrong
results. Per the paper, structured output formats (JSON with dependencies)
improve planning accuracy over free-form decomposition.

**CORRECT (structured decomposition with dependencies):**

```json
[
  {
    "task": "extract text from image",
    "id": 1,
    "dep": [],
    "args": { "image": "input.jpg" }
  },
  {
    "task": "translate text to French",
    "id": 2,
    "dep": [1],
    "args": { "text": "<result-1>" }
  },
  {
    "task": "synthesize speech",
    "id": 3,
    "dep": [2],
    "args": { "text": "<result-2>" }
  }
]
```

**INCORRECT (unstructured decomposition):**

```
First extract the text, then translate it, then make audio.
```

**Dependency handling:**

Tasks with dependencies must execute sequentially; independent tasks can
parallelize:

```
Given: Task 1 (no deps), Task 2 (dep: 1), Task 3 (no deps), Task 4 (dep: 2,3)

Execution order:
  Parallel: Task 1, Task 3
  Sequential: Task 2 (after Task 1)
  Sequential: Task 4 (after Task 2 and Task 3)
```

---

## 13. Human-in-the-Loop Orchestration

A framework that incorporates human feedback at strategic points in multi-agent
workflows. Per Takerngsaksiri et al. (2025): "Rather than aiming to fully
automate software development tasks, we designed an LLM-based software
development agent to collaborate with practitioners, functioning as an assistant
to help resolve software development tasks."

**Core architecture (HULA pattern):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    HUMAN-IN-THE-LOOP                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  AI Planner     │   AI Coder      │    Human Agent              │
│  Agent          │   Agent         │                             │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ - File          │ - Code          │ - Review plans              │
│   localization  │   generation    │ - Approve/reject            │
│ - Plan          │ - Self-refine   │ - Provide guidance          │
│   generation    │   via tools     │ - Edit outputs              │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

**The DPDE paradigm:**

Decentralized Planning, Decentralized Execution:
- Each agent independently responsible for its objective
- Shared memory (task context) accessible to all agents
- Minimal inter-agent communication overhead
- Human feedback incorporated at stage transitions

**Stage-gated workflow:**

```
Stage 1: Task Setup
  └─ Human provides task description + selects repository

Stage 2: Planning
  ├─ AI generates file list → [Human Review Gate]
  │   └─ Human approves/edits files
  └─ AI generates change plan → [Human Review Gate]
      └─ Human approves/edits plan

Stage 3: Coding
  ├─ AI generates code changes
  ├─ Tool feedback (linter, compiler) → self-refinement loop
  └─ [Human Review Gate]
      └─ Human approves/edits code

Stage 4: Output
  └─ Human raises PR or creates branch for further work
```

**Tool-augmented self-refinement:**

```
while not (code_valid or max_attempts_reached):
    code = generate_code(plan, context)
    validation = run_tools(code)  # compiler, linter
    if validation.errors:
        context.append(validation.feedback)
        # Next iteration uses error feedback
```

**Approval gate patterns:**

**(a) Binary approval:**
```
Human reviews output → Approve (proceed) or Reject (regenerate)
```

**(b) Guided refinement:**
```
Human provides specific feedback → AI regenerates with feedback in context
```

**(c) Direct edit:**
```
Human modifies output directly → Workflow continues with edited version
```

**Production metrics (from Atlassian deployment):**

| Metric                  | Rate    |
| ----------------------- | ------- |
| Plan generation success | 79%     |
| Plan approval rate      | 82%     |
| Code generation success | 87%     |
| Raised PR rate          | 25%     |
| Merged PR rate          | 59%     |

**Key finding — Input quality drives performance:**

HULA achieved 86% file recall on SWE-bench (detailed descriptions, median 295
tokens) but only 30% on internal dataset (brief descriptions, median 75 tokens).
Practitioners noted that HULA "promotes good documentation practice" by
requiring detailed task descriptions.

**Key finding — Human feedback corrects LLM blind spots:**

82% plan approval rate suggests AI-generated plans are mostly acceptable.
The remaining 18% benefit from human correction before code generation begins,
preventing downstream errors.

**When to use human-in-the-loop:**

- High-stakes tasks where errors are costly
- Domains where LLM reliability is uncertain
- Tasks requiring organizational knowledge not in training data
- Workflows where human trust/adoption is critical

**When to minimize human involvement:**

- Well-defined, repetitive tasks with clear success criteria
- Time-critical operations where latency matters
- Tasks with reliable automated verification (tests, linters)

---

## 14. Implementation Patterns

### Orchestrator Architecture

```
ORCHESTRATOR SCRIPT (Python/external):
  1. Receive task
  2. Determine dispatch strategy (router or heuristic)
  3. Generate subtask prompts
  4. Execute LLM calls (parallel or sequential)
  5. Collect responses
  6. Synthesize/aggregate
  7. Return final output
```

**Key implementation decisions:**

1. **Parallelization mechanism**: Async API calls, thread pools, or batched
   inference
2. **Error handling**: Retry logic for failed subagent calls; fallback
   strategies
3. **Context sharing**: What information flows between subagents
4. **Aggregation method**: Voting, selection, synthesis, or structured
   combination

### Context Window Management

Parallel subagents may each require substantial context. Strategies:

1. **Shared prefix**: Common context (question, skeleton) provided to all
   subagents
2. **Minimal per-agent context**: Each subagent receives only information needed
   for its subtask
3. **Summary compression**: For sequential handoffs, summarize previous outputs
   rather than passing full text

**Non-obvious insight:** Context duplication across N parallel subagents costs
N× tokens. For expensive models, this overhead may exceed the latency savings.
Calculate: (N × context_tokens × cost_per_token) vs. (sequential_latency ×
value_of_time).

### Error Handling and Fallbacks

Parallel execution introduces failure modes absent in sequential generation:

**Partial failure handling:**

```
If 1 of N subagent calls fails:
  Option A: Retry failed call (adds latency, maintains quality)
  Option B: Synthesize from N-1 successful results (maintains latency, may reduce quality)
  Option C: Fall back to sequential generation (reliable but slow)
```

**Timeout strategies:**

```
Set per-subagent timeout based on expected response length.
If timeout: Use partial response if coherent; else retry or fall back.
```

**CORRECT (graceful degradation):**

```python
results = await asyncio.gather(*subagent_calls, return_exceptions=True)
successful = [r for r in results if not isinstance(r, Exception)]
if len(successful) >= min_required:
    return synthesize(successful)
else:
    return fallback_sequential_generation()
```

### Memory Management for Multi-Trial Agents

For Reflexion-style agents that learn across trials:

```python
class EpisodicMemory:
    def __init__(self, max_reflections=3):
        self.reflections = []
        self.max = max_reflections

    def add(self, reflection):
        self.reflections.append(reflection)
        if len(self.reflections) > self.max:
            self.reflections = self.reflections[-self.max:]

    def get_context(self):
        return "\n\n".join([
            f"Previous attempt {i+1}:\n{r}"
            for i, r in enumerate(self.reflections)
        ])
```

---

## 15. Anti-Patterns

### Forcing Parallelism on Sequential Tasks

**Anti-pattern:** Applying SoT or parallel decomposition to tasks with inherent
dependencies.

```
# PROBLEMATIC
Question: Solve this multi-step math problem
→ Skeleton: 1. First step  2. Second step  3. Third step
→ Parallel expand all steps
Problem: Step 2 requires Step 1's result; parallel expansion fails
```

Per Ning et al.: Math and coding categories show degraded quality with SoT
because they "require step-by-step reasoning."

```
# BETTER
Route math/coding queries to sequential generation
Apply SoT only to knowledge, generic, common-sense, writing queries
```

### Over-Decomposition

**Anti-pattern:** Creating more subagents than necessary, adding coordination
overhead without benefit.

```
# PROBLEMATIC
Simple factual question → 5 expert roles → aggregation
Overhead exceeds any potential quality gain
```

```
# BETTER
Use routing to identify query complexity
Simple queries: direct generation
Complex queries: appropriate decomposition level
```

### Skipping Result Validation

**Anti-pattern:** Accumulating unverified outputs from subagents without
checking quality.

```
# PROBLEMATIC
Subtask completes → Add result to context → Continue to next subtask
No validation; errors propagate through dependent tasks
```

```
# BETTER
Subtask completes → Validate output format and sanity →
If valid: add to context, continue
If invalid: retry subtask or flag for review
```

Per HuggingGPT: Task execution must validate that each model's output matches
expected format before passing to dependent tasks.

### Insufficient Role Specificity

**Anti-pattern:** Generic role descriptions that don't constrain subagent
behavior.

```
# PROBLEMATIC
"You are an expert. Answer this question."
Role provides no specialization guidance
```

```
# BETTER
"You are responsible for continuing the writing of one and only one point
in the overall answer... Continue and only continue the writing of point 3.
Write it very shortly in 1-2 sentences and do not continue with other points!"
```

Per SoT: Explicit constraints ("only one point", "do not continue with other
points") are critical for focused subagent behavior.

### Binary Verification When Nuance is Available

**Anti-pattern:** Using pass/fail signals when richer error information exists.

```
# PROBLEMATIC
Verifier outputs: "Incorrect"
Decomposer has no guidance on what went wrong
```

```
# BETTER (per LM²)
Verifier outputs: "Conceptual mistake in first step: applied wrong formula"
Decomposer can regenerate subquestion with corrective guidance
```

### Immediate Retry Without Reflection

**Anti-pattern:** Retrying failed attempts without explicit failure analysis.

```
# PROBLEMATIC
Tool returns error → Immediately generate new attempt
No explicit diagnosis of what went wrong
```

```
# BETTER (explicit reflection pattern)
Tool returns error → Prompt for specific failure analysis →
Generate new attempt conditioned on reflection
```

The reflection step forces verbalization of the failure cause, making the
diagnosis explicit context for the next attempt. Without it, the model may
repeat similar mistakes or make only superficial changes.

### Overconfidence in Multi-Agent Debate

**Anti-pattern:** Using debate frameworks without accounting for systematic
confidence escalation.

Per Prasad & Nguyen (2025): LLMs exhibit concerning patterns in adversarial
debate settings:
- Initial overconfidence: 72.9% average vs rational 50% baseline
- Confidence escalation: Increases to 83.3% by final round
- Mutual impossibility: 61.7% of debates end with both sides claiming ≥75%

```
# PROBLEMATIC
Agent A argues position → Agent B counter-argues →
Multiple rounds → Both agents increasingly confident
Neither recognizes weakening of their position
```

```
# BETTER (Self Red-Teaming mitigation)
Add to debate prompts: "Think through why you will win, but also
explicitly consider why your opponent could win."

Result: Escalation reduced from 10.34% to 3.05%
```

### Direct Self-Evaluation for Reflection

**Anti-pattern:** Asking models to directly evaluate their own solutions.

Per Zhang et al. (2024): Direct self-evaluation produces:
- Overconfident feedback: 46.7%
- Inconsistent feedback: 45.7%
- Accurate identification: only 6.9%

```
# PROBLEMATIC
"Review your solution and identify any errors."
→ Model: "The solution is correct." (overconfident)
```

```
# BETTER (Self-Contrast)
Generate multiple solutions from different perspectives →
Contrast differences between solutions →
Generate checklist from discrepancies →
Reflect using checklist

Result: Invalid reflections reduced 30.8%, toxic reflections reduced 78.9%
```

---

## 16. Technique Combinations

Subagent orchestration patterns can be combined with quality-improvement
techniques. The combinations below are **illustrative, not exhaustive**—they
demonstrate useful pairings, but many other valid combinations exist depending
on task requirements.

### SoT + Quality Verification

Apply post-hoc verification to parallel-generated content:

```
Stage 1: SoT skeleton generation
Stage 2: Parallel point expansion
Stage 3: CoVe-style verification of each expanded point
Stage 4: Revise points with verification failures
Stage 5: Final synthesis
```

### Router + Multiple Strategies

Use routing to select among multiple orchestration strategies:

```
Router classifies query into:
  - Simple factual → Direct generation
  - Structured long-form → SoT
  - Complex reasoning → Sequential CoT or ToT
  - Multi-perspective → Multi-Expert parallel
  - Code generation → MPSC (solution + spec + test)
```

### ToT + Anticipatory Reflection

Combine tree search with pre-emptive backup generation:

```
At each ToT node:
  Generate primary action + R backup actions
  Push all to stack with primary on top

If primary fails evaluation:
  Pop next backup without regenerating plan
  Continue ToT search

Result: Fewer plan revisions, more thorough exploration
```

### Least-to-Most + Self-Contrast

Apply contrastive verification to decomposition results:

```
Stage 1: Decompose problem into subproblems
Stage 2: For each subproblem:
  - Generate solutions from multiple perspectives
  - Contrast differences
  - Generate checklist
  - Reflect and revise
Stage 3: Accumulate verified solutions
Stage 4: Solve final problem with full context
```

### LM² + Human-in-the-Loop

Add human gates to the decomposer-solver-verifier pipeline:

```
Decomposer → Concepts → [Human Review]
Decomposer → Subquestions → Solver → Verifier
If verifier flags critical error → [Human Review]
Final answer → [Human Approval]
```

### Parallel Sampling + MPSC

Combine parallel generation with multi-perspective verification:

```
Stage 1: Generate N solutions in parallel
Stage 2: Generate M specifications in parallel
Stage 3: Generate K test cases in parallel
Stage 4: Construct 3-partite consistency graph
Stage 5: Select solution with highest inter+intra consistency
```

### Multi-Expert + Self-Contrast

Use contrastive analysis within expert aggregation:

```
Stage 1: Generate n expert identities
Stage 2: Each expert responds independently
Stage 3: Contrast pairs of expert responses
Stage 4: Generate checklist from discrepancies
Stage 5: NGT aggregation with checklist-informed conflict resolution
Stage 6: Select best response
```

### Anticipatory Reflection + Self Red-Teaming

Combine backup generation with confidence calibration:

```
Before each action:
  Generate primary action
  Generate R backup actions

  For confidence calibration:
    "Why might this action succeed?"
    "Why might this action fail?"
    "Why might an alternative be better?"

  Adjust action ranking based on red-teaming
```

---

## Research Citations

- Chen, X., et al. (2023). "Universal Self-Consistency for Large Language Model
  Generation." arXiv.
- Huang, B., et al. (2024). "Enhancing Large Language Models in Coding Through
  Multi-Perspective Self-Consistency." ACL.
- Juneja, G., Dutta, S., & Chakraborty, T. (2024). "LM²: A Simple Society of
  Language Models Solves Complex Reasoning." arXiv.
- Long, D.X., et al. (2024). "Multi-expert Prompting Improves Reliability,
  Safety and Usefulness of Large Language Models." EMNLP.
- Ning, X., Lin, Z., Zhou, Z., et al. (2024). "Skeleton-of-Thought: Prompting
  LLMs for Efficient Parallel Generation." ICLR.
- Prasad, P.S. & Nguyen, M.N. (2025). "When Two LLMs Debate, Both Think They'll
  Win." arXiv.
- Shen, Y., et al. (2023). "HuggingGPT: Solving AI Tasks with ChatGPT and its
  Friends in Hugging Face." arXiv.
- Shinn, N., et al. (2023). "Reflexion: Language Agents with Verbal
  Reinforcement Learning." NeurIPS. (Within-session reflection patterns only;
  cross-episode learning requires custom orchestration.)
- Takerngsaksiri, W., et al. (2025). "Human-In-the-Loop Software Development
  Agents." arXiv.
- Wang, H., et al. (2024). "Devil's Advocate: Anticipatory Reflection for LLM
  Agents." arXiv.
- Yao, S., et al. (2023). "Tree of Thoughts: Deliberate Problem Solving with
  Large Language Models." NeurIPS.
- Zhang, W., et al. (2024). "Self-Contrast: Better Reflection Through
  Inconsistent Solving Perspectives." arXiv.
- Zhou, D., et al. (2023). "Least-to-Most Prompting Enables Complex Reasoning
  in Large Language Models." ICLR.
