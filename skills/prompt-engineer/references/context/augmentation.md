# Context Augmentation Techniques

Context augmentation addresses the problem of missing or insufficient information
in prompts. When models lack the knowledge or examples needed to reason
correctly, augmentation techniques retrieve, generate, or select additional
context to bridge the gap. Use these techniques when the model produces
incorrect answers due to knowledge gaps, when few-shot performance is unstable,
or when compositional generalization fails.

---

## KATE: Similarity-Based Example Selection

**Mechanism:** Retrieve in-context examples semantically similar to the test
input using k-nearest neighbors in embedding space.

**When to use:**

- Few-shot performance varies wildly across runs
- Random example selection produces inconsistent results
- Test inputs have semantically similar examples in the training pool

**Implementation:**

1. Encode training examples and test input using a sentence encoder (RoBERTa,
   SBERT)
2. Retrieve k nearest neighbors by Euclidean distance or cosine similarity
3. Order examples from most to least similar (closest to test input last)
4. Optionally fine-tune encoder on task-related data (NLI, STS) for better
   retrieval

**Tradeoffs:**

- Token overhead: k examples x average example length
- Requires embedding index over training set (O(n) storage)
- Fine-tuned encoders improve results but add training cost
- Fails when no similar examples exist (compositional splits)

**Source:** Liu et al. 2021, "What Makes Good In-Context Examples for GPT-3?"

---

## Generated Knowledge Prompting

**Mechanism:** Generate background knowledge from a language model, then prepend
it to the question before inference.

**When to use:**

- Model lacks domain knowledge for commonsense reasoning
- No appropriate knowledge base exists for retrieval
- Questions require implicit world knowledge

**Implementation:**

1. Write 5 question-knowledge demonstration pairs for the task
2. Prompt GPT-3 (or similar) with demonstrations + new question
3. Sample M=20 knowledge statements with nucleus sampling (p=0.5)
4. For each statement, compute inference model's answer confidence
5. Select answer with highest confidence across all knowledge-augmented prompts

**Tradeoffs:**

- Token overhead: M statements x (knowledge length + question length) per
  inference
- API cost: separate generation call + M inference calls
- Quality degrades with smaller knowledge generators (needs 6.7B+ parameters)
- Knowledge can be wrong -- 17% non-factual statements in evaluation

**Source:** Liu et al. 2022, "Generated Knowledge Prompting for Commonsense
Reasoning"

---

## Diverse Demonstrations (Cover-LS)

**Mechanism:** Select demonstrations that collectively cover the structural
elements (local structures) needed in the output, rather than maximizing
similarity to input.

**When to use:**

- Compositional generalization: test outputs combine structures not seen
  together in training
- Similarity-based retrieval returns repetitive, structurally-similar examples
- Structured output tasks (semantic parsing, code generation)

**Implementation:**

1. Train auxiliary model to predict output structures from input
2. Extract candidate local structures (sub-trees) from beam predictions
3. Greedily select examples that cover uncovered structures, largest first
4. Use retriever to pick similar examples among those containing target
   structure
5. When fine-tuning: use noisy/random demonstrations at train time to prevent
   over-copying

**Tradeoffs:**

- Complexity: requires auxiliary model for structure prediction
- Token overhead: similar to KATE (k demonstrations)
- Fails when auxiliary model cannot predict any correct structures (0-shot
  splits)
- Simpler fallback: Cover-Utt covers input words instead of output structures

**Source:** Levy et al. 2024, "Diverse Demonstrations Improve In-context
Compositional Generalization"

---

## Decision Guidance: Choosing a Technique

| Problem Trigger                                 | Recommended Technique       |
| ----------------------------------------------- | --------------------------- |
| Inconsistent few-shot performance               | KATE (similarity retrieval) |
| Missing commonsense/domain knowledge            | Generated Knowledge         |
| Compositional generalization failure            | Diverse Demonstrations      |
| No training examples available                  | Generated Knowledge         |
| Structured output (parsing, code)               | Diverse Demonstrations      |
| Simple classification/QA with good example pool | KATE                        |

**Decision tree:**

1. Do you have a pool of labeled examples?
   - No -> Generated Knowledge Prompting
   - Yes -> Continue
2. Does the task require novel composition of known structures?
   - Yes -> Diverse Demonstrations (Cover-LS or Cover-Utt)
   - No -> KATE
3. Is structure prediction feasible with an auxiliary model?
   - Yes -> Cover-LS
   - No -> Cover-Utt or KATE

---

## Composability Notes

**KATE + Generated Knowledge:** Can combine retrieval-based examples with
generated knowledge statements. Place knowledge before examples in prompt.

**KATE + Diverse Demonstrations:** Use similarity retrieval as the retriever
component within Cover-LS. The paper defaults to BM25, but SBERT works well.

**Generated Knowledge + Fine-tuning:** Knowledge statements can augment training
data, not just inference prompts. Generate knowledge for training examples to
amplify signal.

**Cover-LS + Fine-tuning:** Critical insight: use noisier/simpler demonstrations
at training time (Cover-LS_1 with random retrieval) than at test time (full
Cover-LS with BM25). This prevents over-copying.

**All techniques:** Order matters. Place most relevant/similar content closest
to the test input (last in prompt). Exception: Cover-LS showed reverse order
(most similar first) works slightly better on some datasets -- experiment with
ordering.
