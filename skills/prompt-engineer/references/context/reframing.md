# Context Reframing Techniques

Context reframing restructures how the model perceives and processes input -- changing the frame of reference, perspective, or role through which the task is interpreted. Use these techniques when: (1) the model misinterprets ambiguous questions due to human-LLM frame disparity, (2) the model ignores provided context in favor of memorized facts, (3) you need to elicit implicit chain-of-thought reasoning without explicit CoT prompts, or (4) multiple perspectives would improve answer quality. These techniques operate at the understanding phase before reasoning begins, shaping attention patterns and knowledge retrieval.

---

## Rephrase and Respond (RaR)

**Mechanism:** Prompt the LLM to rephrase and expand the question before answering in a single query, aligning human-framed questions with LLM-preferred interpretations.

**Triggers:**

- Questions contain ambiguity that humans do not perceive but LLMs misinterpret
- Zero-shot setting where prompt quality significantly impacts response
- Human-LLM frame-of-thought disparity exists (e.g., "even month" interpreted as months with even days)
- Factual questions with semantic confusion

**Tradeoffs:** ~2x token overhead (rephrased question + answer). Single API call. More advanced models benefit more; weaker models show modest improvement. Less effective on well-designed unambiguous questions. Complementary to CoT -- can be combined.

---

## Role-Play Prompting

**Mechanism:** Assign LLM an expert role via two-stage dialogue (role-setting prompt + role-feedback response) to trigger implicit chain-of-thought reasoning through persona immersion.

**Triggers:**

- Zero-shot reasoning tasks requiring step-by-step thinking
- Arithmetic word problems requiring mathematical reasoning
- Domains where expert knowledge naturally provides reasoning advantage
- Tasks where explicit CoT trigger ("Let's think step by step") is insufficient
- Model fails to spontaneously generate CoT

**Tradeoffs:** Minimal token overhead -- single role-setting + role-feedback prompt prepended. 1 call per question after one-time role construction. Requires manual role selection per task. Performance saturates on simple tasks already near ceiling. Acts as implicit CoT trigger more effective than Zero-Shot-CoT.

---

## ExpertPrompting

**Mechanism:** Automatically synthesize detailed expert identity descriptions via ICL (3 instruction-expert exemplar pairs), then condition LLM responses on that specialized background.

**Triggers:**

- Instruction requires domain-specific expertise or specialized knowledge
- Response quality benefits from detailed, comprehensive, professional answers
- Task spans diverse domains requiring automatic adaptation
- User expects authoritative, thorough responses rather than generic answers

**Tradeoffs:** ~1.3x tokens (answers average 27% longer). 2 API calls per instruction (identity generation + answer). May generate unwanted self-referential statements about the expert identity requiring post-processing removal.

---

## Context-faithful Prompting (Opinion-based)

**Mechanism:** Reframe context as a narrator's opinion ("Bob said...") and questions as opinion-seeking ("in Bob's opinion?"), forcing the model to attend to context over memorized facts.

**Triggers:**

- Input contains facts conflicting with model parametric knowledge
- Knowledge acquisition tasks like MRC or information extraction
- Need to prevent model from parroting memorized answers
- Context may be irrelevant and model should abstain from answering
- Factual accuracy to provided context is critical

**Tradeoffs:** 1.2-1.5x tokens for opinion-based reframing. Single call. Optional counterfactual few-shot examples for knowledge conflict scenarios. May underperform on smaller models lacking reading comprehension ability.

---

## Step-Back Prompting

**Mechanism:** Ask an abstract "step-back question" first to retrieve high-level concepts and principles, then reason using that abstraction to answer the original detailed question.

**Triggers:**

- Question contains excessive detail obscuring underlying principles
- Multi-step STEM problems requiring domain concepts or first principles
- Knowledge-intensive QA with temporal or contextual constraints
- Multi-hop reasoning where high-level concepts enable better retrieval

**Tradeoffs:** 2x tokens, 2 API calls (abstraction + reasoning). Requires few-shot examples for abstraction step. Unnecessary for simple factual questions or when question already references first principles directly.

---

## Contrastive Prompting

**Mechanism:** Prompt LLM to generate both correct and wrong answers simultaneously, then extract the correct answer by explicit contrast.

**Triggers:**

- Arithmetic reasoning problems requiring accuracy over step-by-step decomposition
- Commonsense reasoning tasks requiring awareness of individual knowledge pieces
- Tasks where LLM needs self-awareness of potential errors
- Math problems with infinite possible answers where eliminating wrong patterns helps

**Tradeoffs:** 2x tokens, 2 calls (reasoning extraction + answer extraction). Performs worse than CoT on symbolic reasoning with limited action spaces requiring explicit step decomposition. Strong on arithmetic and commonsense.

---

## Contrastive In-Context Learning

**Mechanism:** Provide positive and negative example pairs with explicit labels, then elicit reasoning about their differences before generation.

**Triggers:**

- User preference alignment needed (style, tone, format)
- Desired output characteristics hard to describe explicitly in instructions
- Multiple valid outputs exist with preference ordering
- Need to guide model away from default mechanical style
- Implicit stylistic constraints (concise vs detailed, formal vs casual)

**Tradeoffs:** 2x tokens (positive + negative examples vs positive only). Single call. Requires paired positive/negative examples. Optional reasoning step increases tokens by ~50-100.

---

## Multi-expert Prompting

**Mechanism:** Generate multiple expert identities, collect their independent responses, aggregate via 7-step Nominal Group Technique (NGT) framework, select best answer.

**Triggers:**

- Open-ended questions with multiple valid perspectives
- Questions requiring diverse domain expertise
- Tasks where truthfulness, factuality, and safety are critical
- Long-form generation requiring informativeness and usefulness
- Questions where single expert view introduces bias

**Tradeoffs:** 2x tokens (TruthfulQA), 1.5x (BOLD). n+1 API calls (n expert responses + 1 aggregation). Requires good instruction-following capability. Less effective for short-form answers without CoT reasoning traces.

---

## Argument Generation

**Mechanism:** Generate arguments for and against each possible answer, then rank arguments to select the strongest one.

**Triggers:**

- Multiple choice questions with explicit answer candidates
- Smaller language models (< 8B parameters) where reasoning boost needed
- Tasks where counterarguments reveal the correct answer
- Bias mitigation in classification tasks
- When chain-of-thought reasoning produces insufficient performance

**Tradeoffs:** 2-3x tokens (generate arguments for all candidates + ranking). Single call. Requires predefined answer candidates. Most effective for small models; diminishing returns for models > 8B parameters. May force larger models to generate convincing arguments for incorrect options.

---

## EmotionPrompt

**Mechanism:** Append psychological emotional stimuli phrases (e.g., "This is very important to my career") to prompts to enhance performance and truthfulness.

**Triggers:**

- Few-shot learning scenarios where small performance gains are valuable
- Tasks requiring truthfulness and factual accuracy
- Generative tasks where quality, truthfulness, and responsibility matter
- When robustness to temperature variations is desired

**Tradeoffs:** Minimal overhead (11-50 tokens per stimulus). Single call. May produce overly deterministic language. Larger gains in few-shot settings vs zero-shot.

---

## Principled Persona Prompting

**Mechanism:** Assign task-aligned expert personas while avoiding irrelevant attributes that degrade performance.

**Triggers:**

- Task requires specialized domain knowledge
- Expertise framing might improve task alignment
- Task benefits from specific perspective or knowledge level

**Anti-patterns (avoid):**

- Adding task-irrelevant attributes like names or preferences
- Using gendered roles when gender is irrelevant
- Simple "You are a helpful assistant" prompts for objective factual tasks

**Tradeoffs:** Minimal overhead (5-20 tokens). Single call. High sensitivity to irrelevant attributes -- irrelevant personas cause 14-59% negative effects across models.

---

## Persona Prompting Ineffectiveness (Anti-pattern)

**Mechanism:** Study finding that adding persona roles to system prompts does not improve and may harm LLM performance on objective tasks.

**Key findings:**

- Do NOT use persona prompting for objective factual questions
- Do NOT add roles like "You are a helpful assistant" expecting performance gains
- Do NOT use speaker-specific roles ("You are a lawyer") for factual accuracy
- Audience-specific prompts marginally better than speaker-specific
- Gender-neutral roles slightly better than gendered roles
- Effects are largely random and unpredictable across 162 roles, 9 LLMs

---

## Decision Guidance

**Question clarity issues:** Use Rephrase and Respond first -- zero-shot, training-free, minimal overhead.

**Need implicit reasoning without explicit CoT:** Use Role-Play Prompting with task-advantaged role.

**Context being ignored for memorized facts:** Use Context-faithful Prompting (opinion-based reframing) with counterfactual demonstrations.

**Multi-perspective synthesis needed:** Use Multi-expert Prompting for diverse expertise, or Argument Generation for smaller models.

**Detailed problem requiring principles:** Use Step-Back Prompting to abstract first, then reason.

**Style/preference alignment:** Use Contrastive In-Context Learning with positive/negative pairs.

**Simple domain expertise:** Use ExpertPrompting for automatic expert identity generation.

**Avoid:** Generic persona prompts on factual tasks -- they provide no benefit and may harm performance.

---

## Composability Notes

**Rephrase and Respond + CoT:** Explicitly complementary. RaR clarifies the question, CoT handles reasoning. Combine by adding "let's think step by step" to RaR prompt.

**Role-Play + Self-Consistency:** Can be combined. Role-play acts as implicit CoT trigger; self-consistency samples diverse reasoning paths.

**Context-faithful + Counterfactual Demonstrations:** Best used together. Opinion-based prompts + counterfactual examples yield largest faithfulness gains.

**ExpertPrompting + Multi-expert:** Multi-expert extends ExpertPrompting by generating multiple identities and aggregating their responses.

**Step-Back + CoT:** Sequential -- abstraction retrieves principles, then standard reasoning applies them.

**Contrastive ICL + Standard Few-shot:** Contrastive replaces standard few-shot; uses same token budget more effectively with positive/negative pairs.

**Argument Generation + Larger Models:** Avoid -- may force convincing arguments for incorrect options. Best for models < 8B parameters.
