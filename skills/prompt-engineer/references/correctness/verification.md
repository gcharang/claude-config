# Verification Techniques

Verification techniques add explicit checking steps to catch errors in LLM outputs
before finalization. Use these when factual accuracy is critical, hallucination risk
is high, or outputs require validation against external sources. Key insight: models
answering targeted verification questions often achieve higher accuracy than the same
facts embedded in longer responses.

**Critical caveat**: Intrinsic self-correction (without external feedback) typically
degrades reasoning performance. Effective verification requires either external tools,
structured decomposition, or grounded feedback sources.

---

## Chain-of-Verification (CoVe)

Generate baseline response, plan verification questions, answer them independently,
then produce final verified response. The "factored" variant answers verification
questions without access to the original response, preventing repetition of
hallucinations.

**Triggers**:

- Factual accuracy critical and hallucination risk high
- List-based questions requiring multiple entity answers
- Longform generation where exposure bias increases hallucinations
- Closed-book QA without retrieval support

**Tradeoffs**: 3-5x tokens, 4 sequential steps. Few-shot examples required for each
step. Factored variant needs separate prompts per verification question.

---

## Self-Refine

Same LLM iteratively generates output, provides feedback on its output, then refines
based on feedback. Requires actionable, specific feedback pointing to concrete
phrases to change.

**Triggers**:

- Output requires iterative refinement for quality improvement
- Tasks with multifaceted objectives (dialogue, code readability)
- Hard-to-define quality goals where initial output needs improvement
- Open-ended generation with large solution space

**Tradeoffs**: 3-4x tokens (accumulated history), 2-4 iterations. Few-shot examples
required. Diminishing returns after 2-3 iterations. Struggles with detecting nuanced
math errors -- feedback identifies location incorrectly 33% of time, suggests wrong
fix 61% of time in failure cases.

---

## CRITIC

LLM validates output via external tool interactions (search engines, code
interpreters, calculators) then self-corrects based on tool-generated critiques.
Addresses the fundamental limitation that LLMs cannot reliably verify their own
reasoning without external grounding.

**Triggers**:

- Factual accuracy verification needed
- Generated code requires execution validation
- Mathematical reasoning correctness must be verified
- Multi-hop reasoning with factual dependencies

**Tradeoffs**: 2-4x tokens per iteration, plus tool API calls. Requires access to
appropriate external tools. Verify-then-correct cycle can iterate until stopping
condition met.

---

## Reflexion

Agents verbally reflect on task feedback and store reflections in episodic memory
to improve subsequent trials. Works with binary/scalar rewards from environment
execution.

**Triggers**:

- Agent needs trial-and-error learning over multiple episodes
- Sequential decision-making with sparse binary rewards
- Self-generated tests or heuristics can validate outputs
- Credit assignment problem exists in long action trajectories

**Tradeoffs**: 2-12x tokens across trials, 1-12 iterative trials per task. Requires
episodic memory buffer (1-3 experiences) and environment feedback signal. Fails on
tasks requiring extreme exploration diversity.

---

## Factored Verification

Decompose summary into claims, verify each claim against sources independently,
then revise based on critiques. Targets summarization where individual facts can
be checked against provided context.

**Triggers**:

- Summarization of grounded source material where accuracy is critical
- Academic paper summarization or synthesis
- Claims must be verifiable against provided context
- Model-generated content needs citation verification

**Tradeoffs**: 2-3x tokens per claim, n+2 calls (1 decomposition + n claim
verifications + 1 revision). Increases false negatives when claims require
transitive reasoning across sources.

---

## Self-Contrast

Contrast diverse solving perspectives to identify discrepancies and generate
checklist for self-correction. Addresses overconfident or inconsistent self-feedback
by examining differences between multiple solution approaches.

**Triggers**:

- Self-evaluation produces overconfident or inconsistent feedback
- Multiple solving approaches exist for the problem
- Initial reflection shows stubborn biases or insufficient error detection
- Task benefits from examining discrepancies between different solutions

**Tradeoffs**: 7-8x tokens, ~7.8 API calls average (2-9 perspectives + contrast +
reflection). Requires clustering for selection, pairwise contrast comparisons.
Outperforms multi-agent debate with 10% fewer calls.

---

## REFINER

Generator model iteratively refines intermediate reasoning steps using structured
feedback from a trained critic model. Critic provides fine-grained error types and
localized feedback on specific reasoning steps.

**Triggers**:

- Multi-step reasoning with structured intermediate representations
- Mathematical problem solving requiring equation generation
- Intermediate reasoning errors can be categorized into fine-grained error types
- Feedback can be structured and localized to specific reasoning steps

**Tradeoffs**: 3x tokens (T=3 iterations), 3-4 generator-critic iterations. Requires
finetuned critic model (220M params) and warm-up phase with 10% supervised data.
More effective than scalar reward feedback (PPO) or self-refinement.

---

## Instruct-of-Reflection (IoRT)

Dynamic instructor uses meta-thoughts and self-consistency to generate refresh, stop,
or select instructions guiding iterative reflection. Addresses redundancy (correct
answers remain correct), drift (correct becomes incorrect), and stubbornness
(incorrect persists).

**Triggers**:

- Static iterative reflection shows redundancy or drift
- Model is stubborn (incorrect answers persist across iterations)
- Multi-iteration reasoning where stopping condition is unclear
- Scenarios where self-correction degrades performance without oracle labels

**Tradeoffs**: Variable overhead, average 2.2 iterations vs fixed 4. 18.8-47.9%
fewer calls than fixed-iteration methods. Requires few-shot meta-thought examples,
retrieval system for meta-thought memory, self-consistency classifier.

---

## Intrinsic Self-Correction Failure (Anti-Pattern)

LLMs review their initial reasoning and attempt refinement without external feedback,
typically degrading performance. Documented to understand limitations.

**Evidence**: GPT-4 accuracy drops from 95.5% to 89.0% on GSM8K after self-correction;
Llama-2 drops from 62.0% to 36.5%. Multi-agent debate underperforms self-consistency
with equivalent inference cost.

**Root cause**: LLMs cannot properly judge correctness of their own reasoning. More
likely to change correct answers to incorrect than vice versa. Feedback prompt
biases model away from optimal initial response.

---

## Decision Guidance

**Choose based on feedback source availability:**

| Feedback Source             | Technique                 |
| --------------------------- | ------------------------- |
| External tools available    | CRITIC                    |
| Environment provides signal | Reflexion                 |
| Source documents available  | Factored Verification     |
| Trained critic available    | REFINER                   |
| Human correction acceptable | MCS (HITL-CoT)            |
| No external feedback        | Self-Contrast, CoVe       |
| None (avoid)                | Intrinsic self-correction |

**Choose based on task type:**

| Task Type                  | Technique                            |
| -------------------------- | ------------------------------------ |
| Factual QA / hallucination | CoVe, CRITIC, Factored Verification  |
| Code generation            | CRITIC (with interpreter), Reflexion |
| Math reasoning             | CRITIC (calculator), REFINER         |
| Multi-aspect quality       | Self-Refine                          |
| Summarization              | Factored Verification                |
| Complex reasoning          | Self-Contrast, IoRT                  |

---

## Composability Notes

**Effective combinations:**

- CoVe + retrieval augmentation: verification questions can use external sources
- CRITIC + CoT: tool interaction validates reasoning chains
- Reflexion + ReAct: episodic memory enhances action-observation loops
- Self-Contrast + Self-Consistency: diverse perspectives plus voting

**Conflicts to avoid:**

- Intrinsic self-correction + reasoning tasks: documented to degrade performance
- Multiple verification loops without stopping criteria: token explosion
- Generic feedback + refinement: specific, actionable feedback essential

**Cost optimization:**

- Use factored/2-step variants to prevent hallucination repetition
- Set maximum iterations (2-4 typical) -- diminishing returns after
- For equivalent inference budget, self-consistency often outperforms debate
- IoRT's adaptive stopping reduces overhead 27.6% vs fixed iterations
