# Iterative Refinement Techniques

Iterative refinement improves LLM outputs through feedback loops that progressively correct errors and enhance quality. Use refinement when single-shot generation produces inconsistent results, when complex reasoning requires course correction, or when output quality matters more than latency. Refinement is particularly effective for multi-step reasoning, open-ended generation, and tasks where errors compound -- but adds token overhead proportional to iteration count.

---

## Progressive-Hint Prompting (PHP)

**Mechanism:** Feed previous answers back as "hints" until consecutive answers converge.

**When to use:**

- Math reasoning with frequent calculation errors
- Multi-step problems where early errors derail later steps
- When base CoT produces unstable answers across runs

**Implementation:**

- Generate base answer with CoT/Complex CoT
- Append hint to question: "(Hint: The answer is near to [A1, A2, ...])"
- Add answer prefix: "We know the Answer Hints: [A1, A2, ...]"
- Stop when two consecutive answers match

**Tradeoffs:**

- 2-4 LLM calls typical (more with weaker models/prompts)
- Works better with stronger models (GPT-4 > GPT-3.5)
- Composable with self-consistency (reduces sample paths 46%)

---

## Prompt Chaining vs Stepwise Prompt

**Mechanism:** Separate draft/critique/refine into discrete calls (chaining) vs single generation (stepwise).

**When to use:**

- Text generation requiring iterative improvement (summarization, writing)
- When quality matters more than latency
- Avoid stepwise for complex refinement -- produces "simulated" improvement

**Implementation (Prompt Chaining):**

1. Draft: Generate initial output
2. Critique: Evaluate draft, identify issues
3. Refine: Improve based on critique
4. Each phase = separate LLM call with focused prompt

**Tradeoffs:**

- Chaining: 3x calls, better quality (77% win rate vs baseline)
- Stepwise: 1 call, but model may fake errors to "correct" them later
- Chaining requires more prompt engineering effort

---

## Iteration of Thought (IoT)

**Mechanism:** Inner Dialogue Agent (IDA) generates dynamic prompts; LLM Agent refines based on evolving context.

**When to use:**

- Complex reasoning requiring adaptive exploration (GPQA, HotpotQA)
- Multi-hop QA across documents
- When static CoT reasoning paths fail

**Implementation:**

- AIoT (Autonomous): Model decides when to stop (efficient, risk of early termination)
- GIoT (Guided): Fixed iteration count (thorough, risk of hallucination)
- IDA generates context-specific prompts based on query + previous response
- Loop until stop signal or max iterations

**Tradeoffs:**

- AIoT: 60% tasks complete in 1 iteration, 90% in 2 -- efficient but may underexplore
- GIoT: Better for explorative tasks (Game of 24), worse for GPQA
- More transparent than ToT (explicit reasoning trace with IDA guidance)

---

## Progressive Thought Refinement (PTR)

**Mechanism:** Train model to understand "how to improve" via weak-strong model collaboration and thought masking.

**When to use:**

- Open-ended tasks without clear correctness criteria
- When you need generalizable refinement (not task-specific)
- Model struggles with self-correction without external feedback

**Implementation:**

- Weak model generates initial thoughts (can be incorrect)
- Strong model produces refined answer given thoughts + query
- Fine-tune with thought-mask: model sees thoughts but loss only on final answer
- At inference: iterate with "please refine your answer" instruction

**Tradeoffs:**

- Requires fine-tuning (not prompt-only)
- Generalizes across domains without task-specific training
- 3-4 iterations optimal; diminishing returns after

---

## Multi-round Thinking (Think Twice)

**Mechanism:** Discard intermediate reasoning, keep only final answer as input for next round.

**When to use:**

- Reasoning models (DeepSeek-R1, QwQ-32B) on competition-level problems
- When model gets stuck in incorrect reasoning chains
- Breaking cognitive inertia on hard math/coding tasks

**Implementation:**

- Round 1: Generate (thinking, answer) from question
- Round N: "The assistant's previous answer is: <answer>X</answer>, please re-answer"
- Discard previous thinking trace -- only pass answer
- Continue 2-4 rounds

**Tradeoffs:**

- Simple prompt change, no training required
- 2-4% accuracy improvement on AIME, GPQA, LiveCodeBench
- Response length decreases with rounds (more confident/decisive)
- Doubles or quadruples inference cost

---

## Decision Guidance

| Problem                              | First Choice      | Alternative     |
| ------------------------------------ | ----------------- | --------------- |
| Math reasoning errors                | PHP               | Multi-round     |
| Text quality improvement             | Prompt Chaining   | IoT (GIoT)      |
| Multi-hop QA                         | IoT (AIoT)        | PTR             |
| Open-ended generation                | PTR               | Prompt Chaining |
| Competition-level math/code          | Multi-round       | IoT (GIoT)      |
| Inconsistent answers across runs     | PHP + SC          | Multi-round     |
| Need generalizable refinement        | PTR (requires FT) | IoT             |
| Latency-sensitive with quality needs | AIoT              | PHP (2 rounds)  |

---

## Composability Notes

**Strong combinations:**

- PHP + Self-Consistency: Reduces sample paths while improving accuracy
- PHP + Complex CoT: Better hints -> better refinement
- IoT + CoT: IDA can use CoT internally for prompt generation
- Multi-round + any reasoning model: Orthogonal to base prompting

**Avoid:**

- Stepwise refinement for complex tasks (produces simulated improvement)
- GIoT on tasks with clear answers (over-iteration causes hallucination)
- Multiple refinement techniques stacked (compounding overhead, diminishing returns)

**Efficiency tips:**

- Start with AIoT for adaptive early stopping
- Use PHP stopping criterion (consecutive match) to avoid over-iteration
- Multi-round: 2 rounds often sufficient, 4 max for hard problems
