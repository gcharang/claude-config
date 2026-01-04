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

| Domain                  | Technique             | Trigger Condition                             | Stacks With                | Conflicts With               | Cost/Tradeoff                    | Effect                                                        |
| ----------------------- | --------------------- | --------------------------------------------- | -------------------------- | ---------------------------- | -------------------------------- | ------------------------------------------------------------- |
| **Parallelization**     | Skeleton-of-Thought   | Long-form answers with plannable structure    | Any single-turn technique  | Step-by-step reasoning tasks | N parallel API calls + synthesis | 1.89×–2.39× latency reduction; quality maintained or improved |
| **Parallelization**     | SoT with Router       | Mixed query types requiring adaptive dispatch | Skeleton-of-Thought        | —                            | Router call overhead             | Enables SoT for suitable queries only                         |
| **Decomposition**       | Parallel Sampling     | Multiple valid solution paths exist           | USC, Complexity Weighting  | Greedy decoding              | N× token cost                    | Enables consistency-based selection                           |
| **Role Specialization** | Multi-Role Delegation | Task requires distinct expertise areas        | Any verification technique | Monolithic prompting         | Role setup overhead              | Specialized responses per domain                              |
| **Orchestration**       | Task Decomposition    | Complex task requiring multiple model types   | Any technique              | Monolithic single-model      | Planning + dispatch overhead     | Enables specialized models per subtask                        |

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

## 3. Parallel Sampling for Aggregation

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

## 4. Role-Specialized Subagents

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

## 5. Task Decomposition Orchestration

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

## 6. Implementation Patterns

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

---

## 7. Anti-Patterns

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

---

## 8. Technique Combinations

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
  - Complex reasoning → Sequential CoT
  - Multi-perspective → Multi-Expert parallel
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
