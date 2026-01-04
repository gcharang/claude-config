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

| Domain                  | Technique                     | Trigger Condition                                 | Stacks With                        | Conflicts With               | Cost/Tradeoff                            | Effect                                                        |
| ----------------------- | ----------------------------- | ------------------------------------------------- | ---------------------------------- | ---------------------------- | ---------------------------------------- | ------------------------------------------------------------- |
| **Parallelization**     | Skeleton-of-Thought           | Long-form answers with plannable structure        | Any single-turn technique          | Step-by-step reasoning tasks | N parallel API calls + synthesis         | 1.89×–2.39× latency reduction; quality maintained or improved |
| **Parallelization**     | SoT with Router               | Mixed query types requiring adaptive dispatch     | Skeleton-of-Thought                | —                            | Router call overhead                     | Enables SoT for suitable queries only                         |
| **Decomposition**       | Parallel Sampling             | Multiple valid solution paths exist               | USC, Complexity Weighting          | Greedy decoding              | N× token cost                            | Enables consistency-based selection                           |
| **Search**              | Tree of Thoughts (BFS)        | Problems requiring exploration with pruning       | State evaluation, backtracking     | Sequential CoT               | b×T LLM calls (beam × steps)             | Game of 24: 4%→74% vs CoT                                     |
| **Search**              | Tree of Thoughts (DFS)        | Deep exploration with early termination needed    | Value-based pruning                | Parallel expansion           | Variable; supports backtracking          | Crosswords: 15.6%→60% word accuracy                           |
| **Refinement**          | Explicit Reflection Prompting | Tool returns error; retry needed                  | Tool-augmented workflows           | Immediate retry              | One reflection step per retry            | Concrete diagnosis improves next attempt                      |
| **Coordination**        | LM² (Decomposer-Solver-Verifier) | Complex reasoning requiring step verification  | Concept generation                 | Monolithic prompting         | 3 models + policy coordination           | MATH: +8.1%; MedQA: +9.7% over baselines                      |
| **Role Specialization** | Multi-Role Delegation         | Task requires distinct expertise areas            | Any verification technique         | Monolithic prompting         | Role setup overhead                      | Specialized responses per domain                              |
| **Orchestration**       | Task Decomposition            | Complex task requiring multiple model types       | Any technique                      | Monolithic single-model      | Planning + dispatch overhead             | Enables specialized models per subtask                        |
| **Human-in-Loop**       | Approval Gates                | Critical tasks requiring human validation         | Any multi-stage pipeline           | Fully autonomous workflows   | Latency for human review                 | 82% plan approval rate in production                          |
| **Feedback**            | Tool-Augmented Refinement     | Code/structured output requiring validation       | Compiler/linter integration        | —                            | Tool execution + retry loops             | Self-correcting syntactic errors                              |

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

## 4. Explicit Reflection Prompting

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

**Tool feedback as evaluator signal:**

In tool-augmented workflows, external tools (compiler, linter, test runner)
provide structured error signals. These shouldn't just pass through—they should
be explicitly analyzed in the reflection step.

```
Tool output:
TypeError: unsupported operand type(s) for +: 'int' and 'str'
  File "solution.py", line 12, in process_data

Reflection prompt:
The error indicates a type mismatch on line 12. The + operator received
an int and str. Looking at line 12: `total = count + user_input`—the
user_input variable is a string from input(), not converted to int.
The fix: wrap user_input in int() before the addition.
```

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

**When to use explicit reflection:**

- Tool returns error that needs diagnosis
- Previous attempt failed in a non-obvious way
- Complex multi-step task where error source is unclear

**When NOT to use explicit reflection:**

- Error is trivially obvious (missing import, typo)
- Already retried 2-3 times without progress
- Error message is self-explanatory and fix is clear

---

## 5. Parallel Sampling for Aggregation

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

## 6. LM² (Language Model Multiplex): Coordinated Multi-Model Reasoning

A framework that modularizes decomposition, solution, and verification into
three coordinated language models. Per Juneja et al. (2024): "LM² modularizes
the decomposition, solution, and verification into three different language
models... these models are trained to coordinate using policy learning."

**Core architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                           LM²                               │
├────────────────┬─────────────────┬──────────────────────────┤
│   Decomposer   │     Solver      │       Verifier           │
│   (finetuned)  │   (frozen API)  │      (finetuned)         │
├────────────────┼─────────────────┼──────────────────────────┤
│ 1. Generate    │ Answer each     │ Classify error type:     │
│    concepts    │ subquestion     │ - Conceptual             │
│ 2. Generate    │ given concepts  │ - Computational          │
│    subquestions│ and prior       │ - Procedural             │
│    step-by-step│ context         │ - Misunderstood question │
│                │                 │ - Position of mistake    │
│                │                 │ - No mistake             │
└────────────────┴─────────────────┴──────────────────────────┘
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

**Policy learning for coordination:**

The decomposer is trained via PPO to coordinate with the solver and verifier.
Reward structure penalizes early mistakes more heavily:

```
R = γᵏ × Σ rᵢ

where:
- γ < 1 is discount factor (earlier mistakes penalized more)
- k is subquestion index
- rᵢ is reward for error type i

Error rewards:
- Conceptual: -0.15
- Computational: -0.05
- Procedural: -0.15
- Misunderstood: -0.20
- First step: -0.20
- First half: -0.12
- Second half: -0.08
- Last step: -0.05
- No mistake: +1.0
```

**Performance results:**

| Dataset  | Best Baseline | LM²    | Improvement |
| -------- | ------------- | ------ | ----------- |
| MATH     | DaSLaM        | +8.1%  | Across subtasks |
| JEEBench | DaSLaM        | +7.71% | Out-of-domain |
| MedQA    | DSP           | +9.7%  | Out-of-domain |

**Key finding — Concepts drive generalization:**

Removing concept generation drops accuracy by 17.5% on Chemistry (out-of-domain)
vs 6% on Math (in-domain). Concepts are critical for generalization.

**Key finding — Finetuned decomposer beats GPT-4:**

A finetuned LLaMA-2 7B decomposer generates more effective concepts than GPT-4
prompted for the same task, demonstrating the value of task-specific training.

---

## 7. Role-Specialized Subagents

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

## 8. Task Decomposition Orchestration

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

## 9. Human-in-the-Loop Orchestration

A framework that incorporates human feedback at strategic points in multi-agent
workflows. Per Takerngsaksiri et al. (2025): "Rather than aiming to fully
automate software development tasks, we designed an LLM-based software
development agent to collaborate with practitioners, functioning as an assistant
to help resolve software development tasks."

**Core architecture (HULA pattern):**

```
┌─────────────────────────────────────────────────────────────┐
│                    HUMAN-IN-THE-LOOP                        │
├─────────────────┬─────────────────┬─────────────────────────┤
│  AI Planner     │   AI Coder      │    Human Agent          │
│  Agent          │   Agent         │                         │
├─────────────────┼─────────────────┼─────────────────────────┤
│ - File          │ - Code          │ - Review plans          │
│   localization  │   generation    │ - Approve/reject        │
│ - Plan          │ - Self-refine   │ - Provide guidance      │
│   generation    │   via tools     │ - Edit outputs          │
└─────────────────┴─────────────────┴─────────────────────────┘
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

## 10. Implementation Patterns

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

## 11. Anti-Patterns

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

---

## 12. Technique Combinations

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
```

### ToT + Explicit Reflection

Combine tree search with reflection on failed paths:

```
ToT search → Best path fails tool verification
Reflection: "Path failed because X; alternative approach Y"
Continue ToT search with reflection in context
→ Pruning informed by explicit failure analysis
```

### LM² + Human-in-the-Loop

Add human gates to the decomposer-solver-verifier pipeline:

```
Decomposer → Concepts → [Human Review]
Decomposer → Subquestions → Solver → Verifier
If verifier flags critical error → [Human Review]
Final answer → [Human Approval]
```

### Parallel Sampling + Complexity Weighting

Combine parallel generation with quality-based filtering:

```
Stage 1: Generate N responses in parallel
Stage 2: Score each by reasoning complexity
Stage 3: Filter to top K by complexity
Stage 4: Apply USC or majority voting to filtered set
```

---

## Research Citations

- Chen, X., et al. (2023). "Universal Self-Consistency for Large Language Model
  Generation." arXiv.
- Juneja, G., Dutta, S., & Chakraborty, T. (2024). "LM²: A Simple Society of
  Language Models Solves Complex Reasoning." arXiv.
- Long, D.X., et al. (2024). "Multi-expert Prompting Improves Reliability,
  Safety and Usefulness of Large Language Models." arXiv.
- Ning, X., Lin, Z., Zhou, Z., et al. (2024). "Skeleton-of-Thought: Prompting
  LLMs for Efficient Parallel Generation." ICLR.
- Shen, Y., et al. (2023). "HuggingGPT: Solving AI Tasks with ChatGPT and its
  Friends in Hugging Face." arXiv.
- Shinn, N., et al. (2023). "Reflexion: Language Agents with Verbal
  Reinforcement Learning." NeurIPS. (Within-session reflection patterns only;
  cross-episode learning requires custom orchestration.)
- Takerngsaksiri, W., et al. (2025). "Human-In-the-Loop Software Development
  Agents." arXiv.
- Yao, S., et al. (2023). "Tree of Thoughts: Deliberate Problem Solving with
  Large Language Models." NeurIPS.
