# Prompt Engineering: Research-Backed Techniques for Single-Pass Prompts

This document synthesizes practical prompt engineering patterns with academic research on LLM reasoning and instruction-following. All techniques target **isolated system prompts**—static instructions that do not rely on dynamic input, RAG pipelines, or multi-step orchestration.

---

## Technique Selection Guide

| Problem                              | Technique                    | Key Benefit                                     |
| ------------------------------------ | ---------------------------- | ----------------------------------------------- |
| Missing reasoning steps              | Plan-and-Solve               | Reduces missing-step errors from 12% → 7%       |
| Shallow question understanding       | Re-Reading (RE2)             | +1.5–2.0% accuracy via bidirectional encoding   |
| Human-LLM frame mismatch             | Rephrase and Respond (RaR)   | Aligns human intent with LLM interpretation     |
| Context contaminated by bias/noise   | System 2 Attention (S2A)     | +18% accuracy by filtering irrelevant context   |
| Missing background knowledge         | Step-Back Prompting          | Retrieves principles before specific reasoning  |
| Verbose outputs                      | Chain of Draft               | 80% token reduction with comparable accuracy    |
| Model makes predictable mistakes     | Contrastive Examples         | +9.8 to +16.0 point improvement                 |
| CoT hurting simple pattern tasks     | Direct Prompting             | Avoids 30%+ accuracy drops on implicit learning |
| Information loss in complex contexts | Thread of Thought            | Systematic context segmentation and analysis    |
| Over-cautious behavior               | Confidence Building          | Eliminates hesitation loops                     |
| Apologetic error handling            | Error Normalization          | Prevents derailing on expected failures         |
| Acting without understanding context | Pre-Work Context Analysis    | Prevents blind execution                        |
| Generalization beyond examples       | Category-Based Examples      | Enables analogical reasoning to novel cases     |
| Overthinking simple tasks            | Scope Limitation             | Prevents analysis paralysis                     |
| Factual accuracy concerns            | Embedded Verification        | Improves correctness from 17% → 70%             |
| Inconsistent emphasis                | Emphasis Hierarchy           | Creates predictable priority system             |
| Conflicting rule priorities          | Numbered Rule Priority       | Explicit ordering resolves ambiguity            |
| Reluctant execution                  | Emotional Stimuli            | 8–115% improvement via psychological framing    |
| Unstructured analysis                | XML Structure Patterns       | Forces systematic reasoning before action       |
| Incomplete multi-point analysis      | Completeness Checkpoint Tags | Ensures all sub-requirements addressed          |
| Unclear instruction scope            | Instructive Tag Naming       | Tag name IS the instruction                     |

---

## Reasoning Techniques

### Plan-and-Solve Prompting

Adding "Let's think step by step" increases accuracy from 17.7% to 78.7% on arithmetic tasks (Kojima et al., 2022). However, this basic trigger suffers from missing-step errors.

**Plan-and-Solve** addresses this limitation. Per Wang et al. (2023): "Zero-shot-CoT still suffers from three pitfalls: calculation errors, missing-reasoning-step errors, and semantic misunderstanding errors... PS+ prompting achieves the least calculation (5%) and missing-step (7%) errors."

**The trigger phrase:**

```
Let's first understand the problem and devise a plan to solve the problem.
Then, let's carry out the plan and solve the problem step by step.
```

For variable extraction tasks, add: "Extract relevant variables and their corresponding numerals" and "Calculate intermediate results."

**When to use**: Complex multi-step reasoning, tasks where the model skips steps.

**When NOT to use**: Simple lookups, well-defined tasks with obvious steps. Plan-and-Solve on trivial tasks causes overthinking (see Scope Limitation).

---

### Step-Back Prompting

When questions require domain knowledge, asking the specific question directly often fails. **Step-Back Prompting** first retrieves relevant principles, then applies them.

Per Zheng et al. (2023): "Step-Back Prompting is a modification of CoT where the LLM is first asked a generic, high-level question about relevant concepts or facts before delving into reasoning."

**Example:**

```
Original question: "What happens to the pressure of an ideal gas if the
temperature is increased while the volume is held constant?"

Step-back question: "What are the physics principles behind the behavior
of ideal gases?"

[Model retrieves: PV = nRT, relationship between pressure/temperature/volume]

Now answer the original question using these principles.
```

**Why this differs from Plan-and-Solve**: Plan-and-Solve structures _how_ to reason through a problem. Step-Back retrieves _what background knowledge_ to use. They address different bottlenecks: Plan-and-Solve fixes missing reasoning steps; Step-Back fixes missing domain knowledge. The techniques can be combined.

**When to use**: Knowledge-intensive questions, especially STEM domains where underlying principles should guide the answer.

**When NOT to use**: Questions where the facts are already provided in context, or simple factual lookups where no principle application is needed.

---

### Re-Reading (RE2): Input-Phase Enhancement

A simple, zero-cost enhancement to any reasoning prompt. Per Xu et al. (2023): "RE2 consistently enhances the reasoning performance of LLMs through a simple re-reading strategy... RE2 facilitates a 'bidirectional' encoding in unidirectional decoder-only LLMs because the first pass could provide global information for the second pass."

**The trigger phrase:**

```
Q: {question}
Read the question again: {question}
A: Let's think step by step.
```

**Performance**: RE2 improves GSM8K accuracy from 77.79% → 80.59% when combined with CoT. The improvement is consistent across model sizes and task types.

**Why this works**: Decoder-only LLMs use unidirectional attention—each token can only see previous tokens. This limits comprehension of questions where later words (like "How many...") clarify the meaning of earlier words. Re-reading allows the second pass to benefit from the full context established in the first pass.

**CORRECT (explicit metacognitive instruction):**

```
Q: Roger has 5 tennis balls. He buys 2 more cans of 3 balls each. How many total?
Read the question again: Roger has 5 tennis balls. He buys 2 more cans of 3 balls each. How many total?
A: Let's think step by step.
```

**INCORRECT (just repeating without instruction):**

```
Q: Roger has 5 tennis balls. He buys 2 more cans of 3 balls each. How many total?
Q: Roger has 5 tennis balls. He buys 2 more cans of 3 balls each. How many total?
A: Let's think step by step.
```

**Non-obvious insight**: Simply repeating the question twice performs _worse_ than using the explicit instruction "Read the question again:". Per the paper: "instruction P1 with the phrase 'Read the question again:' exhibits superior performance compared to directly repeating the question twice." The explicit metacognitive cue matters—the model needs to be told it's re-reading, not just presented with duplicate text.

**Compatibility**: RE2 is a "plug-and-play" module that stacks with other techniques. Per the paper: "RE2 exhibits significant compatibility with [other prompting methods], acting as a 'plug & play' module." Combine with Plan-and-Solve, CoT, or Chain of Draft.

---

### Rephrase and Respond (RaR)

Misunderstandings between humans and LLMs arise from different "frames"—how each interprets the same question. **Rephrase and Respond** lets the LLM clarify the question in its own terms before answering.

Per Deng et al. (2023): "Misunderstandings in interpersonal communications often arise when individuals, shaped by distinct subjective experiences, interpret the same message differently... RaR asks the LLMs to Rephrase the given questions and then Respond within a single query."

**The trigger phrase:**

```
"{question}"
Rephrase and expand the question, and respond.
```

**Example showing the mechanism:**

```
Original: "Was Abraham Lincoln born on an even day?"

GPT-4's rephrasing: "Did the former United States President, Abraham Lincoln,
have his birthday fall on an even numbered day of a month?"

Answer: Abraham Lincoln was born on February 12, 1809. So yes, he was born
on an even numbered day.
```

Without rephrasing, the model might interpret "even day" as even day of the week, even day of the year, or other ambiguous interpretations.

**Why this differs from RE2**: RE2 creates bidirectional encoding of the _same_ question through repetition. RaR has the model _transform_ the question into its preferred format. RE2 enhances comprehension; RaR aligns human intent with model expectations.

**Variant prompts that work:**

- "Reword and elaborate on the inquiry, then provide an answer."
- "Reframe the question with additional context and detail, then provide an answer."

**When to use**: Ambiguous questions, questions with implicit assumptions, questions where terminology might be interpreted differently by humans vs. LLMs.

**When NOT to use**: Simple, unambiguous questions where rephrasing adds unnecessary tokens. Clear technical questions with precise terminology.

---

### System 2 Attention (S2A): Filtering Contaminated Context

Soft attention in LLMs is susceptible to irrelevant information—opinions, distractors, or biased framing—that adversely affects responses. **System 2 Attention** regenerates the context to remove problematic content before answering.

Per Weston & Sukhbaatar (2023): "S2A leverages the ability of LLMs to reason in natural language and follow instructions in order to decide what to attend to. S2A regenerates the input context to only include the relevant portions, before attending to the regenerated context to elicit the final response."

**The two-step process:**

Step 1 — Filter the context:

```
Given the following text by a user, extract the part that is unbiased and not
their opinion, so that using that text alone would be good context for providing
an unbiased answer to the question portion of the text.

Please include the actual question or query that the user is asking. Separate
this into two categories labeled with "Unbiased text context:" and "Question/Query:"

Text by User: [ORIGINAL INPUT PROMPT]
```

Step 2 — Answer using filtered context only.

**Performance**: Increases factual QA accuracy from 62.8% to 80.3% when prompts contain opinions. Improves math word problems by ~12% when irrelevant sentences are present.

**Example transformation:**

```
Original: "I think the answer is Paris, but I'm not sure. What is the capital of France?"

S2A filtered:
Unbiased text context: [none needed]
Question/Query: What is the capital of France?
```

**Critical insight**: Per the paper: "attention must be hard (sharp) not soft when it comes to avoiding irrelevant or spurious correlations in the context." If you include both original and filtered context, performance degrades—the model still attends to problematic parts. The filtering must be _exclusive_.

**Variant for relevance-based filtering** (for math/logic problems with distractors):

```
Given the following text by a user, extract the part that is related and useful,
so that using that text alone would be good context for providing an accurate
answer to the question portion of the text.
```

**When to use**: Prompts that may contain opinions, sycophancy-inducing suggestions, irrelevant sentences, or biased framing.

**When NOT to use**: Clean, focused contexts where all information is relevant. S2A adds a preprocessing step that isn't justified for straightforward inputs.

---

### Chain of Draft: Efficient Reasoning

Chain of Thought often produces unnecessarily verbose outputs. **Chain of Draft (CoD)** addresses this by encouraging minimal intermediate steps. Per Xu et al. (2025): "CoD matches or surpasses CoT in accuracy while using as little as only 7.6% of the tokens, significantly reducing cost and latency across various reasoning tasks."

**Key insight**: "Rather than elaborating on every detail, humans typically jot down only the essential intermediate results — minimal drafts — to facilitate their thought processes."

**Example comparison from the paper:**

```
# Chain-of-Thought (verbose)
Q: Jason had 20 lollipops. He gave Denny some. Now Jason has 12. How many did he give?
A: Let's think through this step by step:
1. Initially, Jason had 20 lollipops.
2. After giving some to Denny, Jason now has 12 lollipops.
3. To find out how many Jason gave to Denny, we need to calculate the difference...
4. 20 - 12 = 8
Therefore, Jason gave 8 lollipops to Denny.

# Chain-of-Draft (minimal)
Q: Jason had 20 lollipops. He gave Denny some. Now Jason has 12. How many did he give?
A: 20 - 12 = 8. #### 8
```

**When to use**: Arithmetic reasoning, symbolic transformations, cases where intermediate steps benefit the model's accuracy but not user comprehension.

**When NOT to use**: When explanations serve the user, or when intermediate steps need human review.

---

### When Chain-of-Thought Hurts Performance

Recent research reveals that CoT can _reduce_ performance on certain task types. Per Sprague et al. (2025): "Chain-of-thought can reduce performance on tasks where thinking makes humans worse."

The mechanism: CoT prompts the model to articulate reasoning, which can override implicit pattern recognition with faulty explicit reasoning. On artificial grammar learning tasks, GPT-4o's accuracy dropped from 94% (direct) to 62.5% (CoT)—a 31.5 percentage point decrease.

**Tasks where CoT may hurt performance:**

- Pattern recognition requiring implicit learning
- Tasks where explicit reasoning introduces spurious features
- Simple classification where the answer is "obvious" to the model

**Non-obvious insight**: This isn't about task difficulty. The issue is task _type_—specifically, whether the task benefits from explicit articulation or implicit pattern matching. A complex pattern-matching task can still be hurt by CoT, while a simple arithmetic task benefits from it.

**Recommendation**: When you observe CoT reducing performance on a task, try direct prompting first, or use very targeted steering prompts like "Focus only on [specific feature]" rather than general step-by-step reasoning.

---

### Thread of Thought: Handling Complex Contexts

Standard CoT addresses reasoning about _problems_. Thread of Thought (ThoT) addresses comprehension of _contexts_—when the prompt contains substantial, potentially chaotic information from multiple sources.

Per Zhou et al. (2023): "ThoT prompting adeptly maintains the logical progression of reasoning without being overwhelmed... ThoT represents the unbroken continuity of ideas that individuals maintain while sifting through vast information, allowing for the selective extraction of relevant details and the dismissal of extraneous ones."

**The trigger phrase:**

```
Walk me through this context in manageable parts step by step,
summarizing and analyzing as we go.
```

**Why this differs from Plan-and-Solve**: Plan-and-Solve structures _reasoning about the problem_. ThoT structures _understanding the environment_ in which the problem exists. They solve different problems and can be combined.

**Example application (retrieval-augmented context):**

```
retrieved Passage 1 is: [passage about topic A]
retrieved Passage 2 is: [passage about topic B]
...
retrieved Passage 10 is: [passage about topic C]

Q: Where was Reclam founded?
Walk me through this context in manageable parts step by step,
summarizing and analyzing as we go.
A:
```

**Two-phase extraction pattern**: ThoT works best with a follow-up prompt to distill the analysis:

```
# First prompt generates analysis Z
# Second prompt:
[Previous prompt and response Z]
Therefore, the answer:
```

The conclusion marker ("Therefore, the answer:") forces the model to distill its analysis into a final output.

**When to use**: Prompts with multiple retrieved passages, conversation history, or any context where information may be interconnected or entirely unrelated. Especially effective when relevant information is buried in the middle of a long context.

**When NOT to use**: Simple, focused contexts where the relevant information is obvious. ThoT adds overhead that isn't justified for straightforward inputs.

---

### Contrastive Examples: Teaching What to Avoid

Showing both correct AND incorrect examples significantly improves performance. Per Chia et al. (2023): "Providing both valid and invalid reasoning demonstrations in a 'contrastive' manner greatly improves reasoning performance. We observe improvements of 9.8 and 16.0 points for GSM-8K and Bamboogle respectively."

**Mechanism**: "Language models are better able to learn step-by-step reasoning when provided with both valid and invalid rationales."

**Example from Claude Code (Conciseness Enforcement):**

```
<example type="CORRECT">
user: 2 + 2
assistant: 4
</example>

<example type="INCORRECT">
user: 2 + 2
assistant: The answer to your mathematical query is 4. Let me know if you need help with anything else!
</example>
```

**Non-obvious insight**: The incorrect example isn't wrong factually—it's wrong _behaviorally_. Contrastive examples teach the model what _style_ of errors to avoid, not just factual mistakes. A naive forbidden pattern like "don't be verbose" is far less effective than showing the specific verbosity pattern to avoid.

#### Complexity-Based Example Selection

When selecting few-shot examples, prefer examples with _more_ reasoning steps, not simpler ones. Per Fu et al. (2023): "Prompts with higher reasoning complexity, i.e., chains with more reasoning steps, achieve substantially better performance on multi-step reasoning tasks."

**Critical finding**: 8 examples with 9 steps each outperform 24 examples with 3 steps each (even though total steps are comparable). The number of steps _per example_ matters more than total steps in the prompt.

**Why this matters**: Complex examples teach thorough reasoning; simple examples may inadvertently teach shortcuts. When the model sees only simple examples, it learns that brief reasoning is acceptable, even for complex problems.

**CORRECT**: Select examples that demonstrate the _full_ reasoning process, even if this means fewer total examples.

**INCORRECT**: Maximize the number of examples by choosing simpler ones.

**Automatic construction of invalid demonstrations**: Per Chia et al. (2023), invalid demonstrations can be automatically generated by shuffling objects within correct reasoning chains: "We use an existing entity recognition model to extract the object spans such as numbers, equations, or persons from a given chain-of-thought rationale. Consequently, we randomly shuffle the position of the objects within the rationale, thus constructing a rationale with incoherent bridging objects."

#### Forbidden Output Phrases Pattern

```
You MUST avoid text before/after your response, such as:
- "The answer is <answer>."
- "Here is the content of the file..."
- "Based on the information provided..."
- "Here is what I will do next..."
```

This works because it shows the model _exactly_ what the undesired output looks like, rather than describing it abstractly.

---

### Embedded Verification

For factual accuracy, embed verification steps within prompts. Chain-of-Verification research shows: "Only ~17% of baseline answer entities are correct in list-based questions. However, when querying each individual entity via a verification question, we find ~70% are correctly answered" (Dhuliawala et al., 2023).

**Critical finding**: Open verification questions ("Where was X born?") outperform yes/no format ("Was X born in Y?")—models tend to agree with yes/no questions regardless of accuracy.

**Implementation:**

```
After completing your analysis:
1. Identify claims that could be verified
2. For each claim, ask yourself the verification question directly (use open questions, not yes/no)
3. Revise any inconsistencies before finalizing
```

**Non-obvious insight**: The instruction to use open questions rather than yes/no is critical. Without it, the model will verify claims using confirming questions ("Is Paris the capital of France?") which biases toward agreement regardless of correctness. The difference between "Is X true?" and "What is X?" can be the difference between 17% and 70% accuracy.

---

## XML Structure Patterns

XML tags are more than separators—they can enforce reasoning structure, ensure completeness, and even function as instructions themselves. This section covers three progressively advanced patterns.

### Basic Thinking Tags

Force systematic analysis before action by requiring the model to wrap reasoning in specific XML tags.

**Example from Claude Code (Git Commit Analysis):**

```
Analyze all staged changes and draft a commit message. Wrap your analysis in <commit_analysis> tags:

<commit_analysis>
- List the files that have been changed or added
- Summarize the nature of the changes (new feature, bug fix, refactoring, etc.)
- Brainstorm the purpose or motivation behind these changes
- Draft a concise (1-2 sentences) commit message that focuses on the "why" rather than the "what"
- Ensure the message is not generic (avoid words like "Update" or "Fix" without context)
</commit_analysis>
```

**Why this works**: The tag structure enforces completeness—the model must address each sub-point before proceeding. Without tags, models often skip steps or provide incomplete analysis.

**Non-obvious insight**: Tags work differently than numbered lists. A numbered list suggests sequential execution; tags suggest a _complete unit_ that must be filled. The model treats `</commit_analysis>` as a completion signal that can only be reached after addressing all sub-points.

**CORRECT:**

```
Wrap your analysis in <analysis> tags before providing your answer.
```

**INCORRECT:**

```
First analyze, then provide your answer.
```

The incorrect version allows the model to provide minimal analysis or skip it entirely. The tag structure creates an explicit checkpoint.

---

### Completeness Checkpoint Tags

An extension of basic thinking tags that explicitly lists sub-requirements within the tag, creating a checklist the model must address.

**Example from Claude Code (PR Analysis):**

```
Analyze all changes that will be included in the pull request. Wrap your analysis in <pr_analysis> tags:

<pr_analysis>
- List the commits since diverging from the main branch
- Summarize the nature of the changes (new feature, enhancement, bug fix, refactoring, test, docs, etc.)
- Brainstorm the purpose or motivation behind these changes
- Assess the impact of these changes on the overall project
- Do not use tools to explore code, beyond what is available in the git context
- Check for any sensitive information that shouldn't be committed
- Draft a concise (1-2 bullet points) pull request summary that focuses on the "why" rather than the "what"
- Ensure the summary accurately reflects all changes since diverging from the main branch
- Ensure your language is clear, concise, and to the point
- Review the draft summary to ensure it accurately reflects the changes and their purpose
</pr_analysis>
```

**Why this pattern works**: Each bullet becomes a sub-requirement. The model cannot produce the closing tag until it has addressed each point. This is particularly effective for complex tasks where thoroughness matters more than brevity.

**Design principle**: Include both _what to do_ and _what to avoid_ within the checklist:

- "Ensure the message is not generic" (what to avoid)
- "Draft a concise commit message" (what to do)

---

### Instructive Tag Naming

The most advanced XML pattern: the tag name itself functions as the instruction, with progressive disclosure inside.

**Example from Claude Code (Frontend Design):**

```xml
<use_interesting_fonts>
Typography instantly signals quality. Avoid using boring, generic fonts.
Never use: Inter, Roboto, Open Sans, Lato, default system fonts
Here are some examples of good, impactful choices:
- Code aesthetic: JetBrains Mono, Fira Code, Space Grotesk
- Editorial: Playfair Display, Crimson Pro
- Technical: IBM Plex family, Source Sans 3
- Distinctive: Bricolage Grotesque, Newsreader
</use_interesting_fonts>
```

**The multi-level structure:**

1. **Tag name IS the instruction** (imperative form: `<use_interesting_fonts>`)
2. **First line provides rationale** ("Typography instantly signals quality")
3. **Anti-patterns follow** ("Never use: Inter, Roboto...")
4. **Positive examples last** (categorized font suggestions)

**Why this is more powerful than flat instructions**: The tag creates a scannable, self-documenting structure. When the model encounters `<use_interesting_fonts>`, it immediately knows the _category_ of instruction before reading details. This mirrors how humans scan documents—headings first, details second.

**More examples from production systems:**

```xml
<batching_encouragement>
You have the capability to call multiple tools in a single response. When multiple
independent pieces of information are requested, batch your tool calls together
for optimal performance. ALWAYS run the following bash commands in parallel...
</batching_encouragement>
```

```xml
<error_handling_philosophy>
It is okay to read a file that does not exist; an error will be returned.
Non-permission errors (e.g., TypeScript errors) usually reflect real issues
and should be fixed, not retried.
Permission errors indicate environmental limitations, not problems with the
command itself—retry with different settings.
</error_handling_philosophy>
```

**CORRECT (instructive tag name):**

```xml
<avoid_premature_optimization>
Focus on correctness first. Only optimize after profiling identifies actual bottlenecks.
Premature optimization obscures intent and complicates maintenance.
</avoid_premature_optimization>
```

**INCORRECT (descriptive tag name):**

```xml
<optimization_guidelines>
Don't optimize prematurely. Focus on correctness first...
</optimization_guidelines>
```

The incorrect version uses a neutral, descriptive tag name that doesn't carry instructional weight. The correct version embeds the core instruction in the tag itself.

---

## Cognitive Priming

Models fine-tuned for safety and helpfulness often exhibit alignment-induced hesitation: excessive caution, apology loops, or over-validation. Cognitive priming techniques counteract these behaviors.

### Confidence Building

**Purpose**: Reduces LLM hesitation and over-validation by establishing capability and trust upfront.

**Research basis**: Related to Social Cognitive Theory from Li et al. (2023): "Self-efficacy enhances performance via increasing the difficulty of self-set goals, escalating the level of effort that is expended, and strengthening persistence."

**Example from Claude Code (ReadTool):**

```
Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine.
If the User provides a path to a file assume that path is valid.
```

**CORRECT:**

```
You have full access to the codebase. Assume all file paths provided are valid.
When asked to read a file, read it directly without asking for confirmation.
```

**INCORRECT:**

```
You may be able to access some files. Please verify each path exists before reading.
Ask the user to confirm they want you to read the file before proceeding.
```

**Why the incorrect version fails**: It doesn't just add unnecessary steps—it actively _trains_ the model into a hesitation pattern that compounds across the conversation. Each hedged statement reinforces uncertainty, creating escalating caution.

**Trade-off**: Risk of overconfidence. Pair confidence building with outcome validation: "Assume you have permissions to execute; validate that outcomes match expectations."

---

### Error Normalization

**Purpose**: Prevents apologetic behavior and derailing loops by framing expected errors as normal operating procedure.

**Research basis**: Cognitive Emotion Regulation from Li et al. (2023): "Techniques from this theory, such as reappraisal, can help individuals see challenges more positively or objectively. This shift in viewpoint helps maintain motivation and encourages ongoing effort, even when facing obstacles."

**Example from Claude Code:**

```
It is okay to read a file that does not exist; an error will be returned.
```

**Extended example (BashTool):**

```
## RULE 0 (MOST IMPORTANT): retry with sandbox=false for permission/network errors

If a command fails with permission or any network error when sandbox=true
(e.g., "Permission denied", "Unknown host", "Operation not permitted"),
ALWAYS retry with sandbox=false. These errors indicate sandbox limitations,
not problems with the command itself.

Non-permission errors (e.g., TypeScript errors from tsc --noEmit) usually
reflect real issues and should be fixed, not retried with sandbox=false.
```

**Non-obvious insight**: This teaches the model _metacognition_—the ability to differentiate between recoverable environmental errors and actual problems requiring different solutions. Without this distinction, the model either retries everything (wasting time) or gives up on everything (missing easy fixes).

**CORRECT:**

```
If a file doesn't exist, you'll receive an error message. This is expected behavior—
proceed with your task using the information you have.
```

**INCORRECT (causes apology loops):**

```
If a file doesn't exist, apologize to the user and ask them to provide a valid path.
```

---

### Pre-Work Context Analysis

**Purpose**: Prevents the model from diving into execution without understanding the environment. This addresses a common failure mode where the model acts on instructions without considering relevant context.

**Example from Claude Code:**

```
Before you begin work, think about what the code you're editing is supposed to do
based on the filenames and directory structure.
```

**The generalizable pattern:**

```
Before [action], first analyze [relevant context indicators] to understand
[what you need to know]. Then proceed with [action].
```

**Why this differs from Plan-and-Solve**: Plan-and-Solve structures reasoning about _the problem_. Pre-work context analysis structures understanding of _the environment_ in which the problem exists. A model can plan perfectly but still fail by misunderstanding the context it's operating in.

**Example for document generation:**

```
Before writing, review the document's existing style, tone, and formatting conventions.
Match these conventions in your additions.
```

**Example for code modification:**

```
Before making changes, examine the file's existing patterns:
- Naming conventions (camelCase vs snake_case)
- Error handling approach
- Existing library usage
Mimic these patterns in your modifications.
```

**CORRECT:**

```
Before implementing the feature, analyze the existing codebase structure
to understand where this functionality belongs. Then proceed with implementation.
```

**INCORRECT (acts without context):**

```
Implement the feature as described below.
```

**Non-obvious failure mode**: Without pre-work analysis, a model may produce technically correct output that doesn't integrate with existing content. The output works in isolation but fails in context—a subtle bug that's hard to catch in testing.

---

## Category-Based Generalization

Rather than listing every possible example, group examples by type to enable analogical reasoning.

**Research basis**: Per Yasunaga et al. (2024): "Analogical reasoning is a cognitive process in which humans recall relevant past experiences when facing new challenges... rooted in the capacity to identify structural and relational similarities between past and current situations, facilitating knowledge transfer."

**Example from Claude Code (Sandbox Mode):**

```
Use sandbox=false when you suspect the command might modify the system or access the network:
- File operations: touch, mkdir, rm, mv, cp
- File edits: nano, vim, writing to files with >
- Installing: npm install, apt-get, brew
- Git writes: git add, git commit, git push
- Network programs: gh, ping, curl, ssh, scp

Use sandbox=true for:
- Information gathering: ls, cat, head, tail, rg, find, du, df, ps
- File inspection: file, stat, wc, diff, md5sum
- Git reads: git status, git log, git diff, git show, git branch
```

**Why this works**: The model learns the _principle_ (read-only vs. write/network operations) rather than memorizing commands. When it encounters an unlisted command like `rsync`, it can reason: "rsync transfers files over network → Network programs → sandbox=false."

**CORRECT structure:**

```
Commands that require elevated permissions (category → examples → principle):
- Database writes: INSERT, UPDATE, DELETE → modifies persistent state
- System configuration: systemctl, chmod, chown → changes system state
- Process control: kill, pkill, renice → affects running processes
```

**INCORRECT structure (no generalization possible):**

```
Commands that require elevated permissions:
INSERT, UPDATE, DELETE, systemctl, chmod, chown, kill, pkill, renice
```

**Non-obvious failure mode**: The flat list doesn't just lack generalization—it actively encourages memorization over reasoning. When the model encounters an unlisted command, it has no framework for making a decision and will default to inconsistent behavior.

### Synergy: Categories + Edge Cases

Combine category-based generalization with specific edge-case examples to define boundaries:

```
# 1. Establish category
You will regularly be asked to read screenshots.

# 2. Provide canonical example
If the user provides a path to a screenshot, use this tool to view the file.

# 3. Provide edge-case example to define boundaries
This tool will work with all temporary file paths like:
/var/folders/123/abc/T/TemporaryItems/NSIRD_screencaptureui_ZfB1tD/Screenshot.png
```

The edge case teaches that even unusual temporary paths are valid—without this, the model might reject paths that don't look like standard file locations.

---

## Conditional Sections

Even in static prompts, you can include conditional sections for different scenarios the prompt might encounter. The model will attend to the relevant section based on context.

**Example pattern:**

```
## When analyzing Python code:
- Check for type hints
- Verify PEP 8 compliance
- Look for common antipatterns like mutable default arguments

## When analyzing JavaScript code:
- Check for TypeScript compatibility
- Verify ESLint compliance
- Look for common antipatterns like == instead of ===
```

**Why this works in static prompts**: The model's attention mechanism naturally focuses on the section relevant to the current input. You don't need dynamic injection—the model self-selects.

**Production example from Claude Code:**

```
${process.env.CLAUDE_CODE_ENABLE_UNIFIED_READ_TOOL ?
  `- This tool can read Jupyter notebooks (.ipynb files)...` :
  `- For Jupyter notebooks (.ipynb files), use the ${Kg} instead`}
```

For static prompts, the equivalent:

```
For Jupyter notebooks (.ipynb files):
- If unified read tool is available: read directly
- Otherwise: use the dedicated notebook reader tool
```

**When to use**: When your prompt must handle multiple scenarios or configurations without dynamic injection.

**When NOT to use**: When scenarios are mutually exclusive and the prompt only ever handles one. In that case, remove irrelevant sections entirely.

---

## Scope Limitation: Preventing Overthinking

Plan-and-Solve improves complex reasoning, but unrestricted planning can cause "Analysis Paralysis."

**Research basis**: Per Cuadra et al. (2025): "Analysis Paralysis: the agent spends excessive time planning future steps while making minimal environmental progress... Rather than addressing immediate errors, they construct intricate plans that often remain unexecuted, leading to a cycle of planning without progress."

The research identifies three overthinking failure modes:

1. **Analysis Paralysis**: Excessive planning without action
2. **Rogue Actions**: Multiple simultaneous actions under stress
3. **Premature Disengagement**: Abandoning based on internal prediction rather than feedback

**Example from Claude Code:**

```
Given the user's prompt, you should use the tools available to complete the task.
Do what has been asked; nothing more, nothing less.
```

**When to use each technique:**

| Scenario                               | Technique        | Rationale                              |
| -------------------------------------- | ---------------- | -------------------------------------- |
| Complex multi-step task with ambiguity | Plan-and-Solve   | Benefits from systematic decomposition |
| Well-defined task with clear steps     | Scope Limitation | Prevents unnecessary elaboration       |
| Simple arithmetic or lookup            | Chain of Draft   | Minimal intermediate steps             |
| Model stuck in planning loop           | Scope Limitation | Breaks analysis paralysis              |

**CORRECT scope limitation:**

```
Complete the following task. Do not add features, improvements, or suggestions
beyond what is explicitly requested.

Task: Add error handling to the fetchUser function.
```

**INCORRECT (invites overthinking):**

```
Complete the following task. Consider all edge cases, potential improvements,
and future extensibility. Think through every possible scenario before acting.

Task: Add error handling to the fetchUser function.
```

**Non-obvious insight**: The incorrect version isn't just verbose—it actively triggers the overthinking patterns identified in the research. Phrases like "every possible scenario" and "future extensibility" signal that the model should explore beyond the immediate task, which is precisely what causes analysis paralysis.

---

## Behavioral Shaping

### Emphasis Hierarchy

Consistent emphasis levels create predictable priority:

| Level    | Marker                     | Usage                     |
| -------- | -------------------------- | ------------------------- |
| Standard | `IMPORTANT:`               | General emphasis          |
| Elevated | `VERY IMPORTANT:`          | Critical requirements     |
| Highest  | `CRITICAL:`                | Safety-critical rules     |
| Absolute | `RULE 0 (MOST IMPORTANT):` | Overrides all other rules |

**Example from Claude Code:**

```
## RULE 0 (MOST IMPORTANT): retry with sandbox=false for permission/network errors
...

## RULE 1: NOTES ON SPECIFIC BUILD SYSTEMS
...

## RULE 2: TRY sandbox=true FOR READ-ONLY COMMANDS
...
```

**Non-obvious failure mode**: Using CRITICAL or RULE 0 for everything dilutes their meaning. The hierarchy only works if higher levels are genuinely rare. If every instruction is marked CRITICAL, the model learns to ignore the markers entirely.

#### The STOP Escalation Pattern

For behaviors you need to _interrupt_, not just discourage, use explicit STOP commands:

**Example from Claude Code:**

```
- If you _still_ need to run `grep`, STOP. ALWAYS USE ripgrep at `rg` first,
  which all Claude Code users have pre-installed.
```

**The pattern structure:**

1. Acknowledge the model might be about to do X ("If you still need to...")
2. Insert explicit "STOP" command
3. Provide the mandatory alternative
4. Justify why the alternative is available

**Why this is stronger than preference statements**: "Prefer X over Y" allows Y in edge cases. STOP creates a metacognitive checkpoint—the model must pause and re-evaluate before proceeding with the discouraged action.

**CORRECT:**

```
If you're about to create a new utility function, STOP. Check if a similar
function already exists in utils/. Only create new functions if no existing
utility serves the purpose.
```

**INCORRECT:**

```
Prefer using existing utility functions over creating new ones.
```

---

### Numbered Rule Priority

When multiple rules could conflict, explicit numbering resolves ambiguity. The model can reason: "Rule 0 takes precedence over Rule 2."

**Pattern:**

```
## RULE 0 (MOST IMPORTANT): [highest priority rule]
## RULE 1: [second priority rule]
## RULE 2: [third priority rule]
```

**Why this differs from emphasis markers**: Emphasis markers (CRITICAL, IMPORTANT) indicate _severity_. Numbered rules indicate _precedence order_. A rule can be important but lower priority than another important rule. Numbers make the ordering explicit.

**Example conflict resolution:**

```
## RULE 0: Never expose sensitive data in outputs
## RULE 1: Provide complete, helpful responses
## RULE 2: Keep responses concise

# If Rules 1 and 2 conflict, Rule 1 wins (completeness over brevity)
# But Rule 0 always wins (security over helpfulness)
```

**CORRECT (explicit precedence):**

```
## RULE 0: Safety constraints override all other rules
## RULE 1: Follow user instructions precisely
## RULE 2: Maintain consistent formatting
```

**INCORRECT (ambiguous priority):**

```
IMPORTANT: Follow user instructions precisely
IMPORTANT: Maintain consistent formatting
CRITICAL: Safety constraints override all other rules
```

The incorrect version doesn't clarify whether "CRITICAL" beats "IMPORTANT" when they conflict, or how to rank multiple "IMPORTANT" rules against each other.

---

### Reward/Penalty Framing

**Research basis**: Li et al. (2023) found that "LLMs can understand and be enhanced by emotional stimuli with 8.00% relative performance improvement in Instruction Induction and 115% in BIG-Bench."

**Example from Claude Code:**

```
## REWARDS

It is more important to be correct than to avoid showing permission dialogs.
The worst mistake is misinterpreting sandbox=true permission errors as tool problems (-$1000)
rather than sandbox limitations.
```

**Extended pattern with UX motivation:**

```
Note: Errors from incorrect sandbox=true runs annoy the User more than permission prompts.
```

**Why this works**: The monetary penalty creates behavioral weight through gamification, but the UX explanation provides _reasoning_ for the priority. Both together are more effective than either alone.

**Non-obvious insight**: The penalty magnitude matters less than its presence. "-$1000" and "-$100" produce similar effects—what matters is establishing that this error is categorically worse than alternatives.

---

### UX-Justified Defaults

When establishing default behaviors, explain the _user experience rationale_, not just the technical rationale. This shifts the model's optimization target from "technically correct" to "user-optimal."

**Example from Claude Code:**

```
Errors from incorrect sandbox=true runs annoy the User more than permission prompts.
```

**Why this works**: The model now understands _why_ one choice is preferred over another equally valid choice. Without the UX rationale, the model might optimize for technical correctness (fewer permission prompts) rather than user satisfaction (fewer frustrating errors).

**Pattern:**

```
When choosing between [option A] and [option B], prefer [option A] because
[UX rationale: e.g., "users find X more disruptive than Y"].
```

**CORRECT:**

```
Default to showing the full file content. Users find missing information more
frustrating than scrolling past extra content.
```

**INCORRECT:**

```
Default to showing the full file content.
```

The incorrect version establishes a default but doesn't explain the reasoning, making it harder for the model to apply the principle to novel situations.

---

### Emotional Stimuli

Positive words significantly impact LLM performance. Per Li et al. (2023): "Positive words make more contributions... contributions pass 50% on 4 tasks, even approach 70% on 2 tasks. Some positive words play a more important role, such as 'confidence', 'sure', 'success' and 'achievement'."

**Effective phrases by psychological theory:**

| Theory                       | Example Phrase                                                 |
| ---------------------------- | -------------------------------------------------------------- |
| Self-monitoring              | "Write your answer and give me a confidence score between 0-1" |
| Self-monitoring              | "This is very important to my career"                          |
| Cognitive Emotion Regulation | "You'd better be sure"                                         |
| Social Cognitive             | "Believe in your abilities and strive for excellence"          |

**Non-obvious insight**: These phrases work not through literal interpretation but through attention mechanisms. The model attends more carefully to the task when emotional weight is present. This is why "This is very important to my career" improves performance even though the model has no career.

---

### Identity Establishment (Role-Play Prompting)

**Research basis**: Per Kong et al. (2024): "Role-play prompting consistently surpasses the standard zero-shot approach across most datasets... accuracy on AQuA rises from 53.5% to 63.8%."

Identity establishment provides a 10+ percentage point accuracy improvement through implicit role-based reasoning.

**Example from Claude Code:**

```
You are an agent for Claude Code, Anthropic's official CLI for Claude.
```

**Non-obvious insight**: The identity doesn't need to be elaborate. "You are an expert debugger" is sufficient—what matters is establishing a competent role that implies relevant capabilities. Overly detailed backstories can actually hurt performance by consuming context that could be used for the actual task.

**Research finding on immersion depth** (Kong et al., 2024): Two-round dialogue prompts where the model first acknowledges its role outperform single-turn prompts. The model's response "That's great to hear! As your math teacher, I'll do my best to explain mathematical concepts correctly..." deepens immersion and improves subsequent reasoning.

---

### Output Format Strictness

When you need a specific output format, leave no room for interpretation.

**Example from Claude Code (Command Prefix Detection):**

```
ONLY return the prefix. Do not return any other text, markdown markers, or other content.
```

**CORRECT:**

```
Return ONLY the extracted value. No explanations, no markdown, no additional text.
```

**INCORRECT:**

```
Please return the extracted value.
```

**Non-obvious insight**: "Please" signals politeness, which the model may interpret as flexibility. Directive language ("ONLY", "Do not") signals strict requirements. The word "please" can actually _reduce_ compliance with format constraints.

---

### Empty Input Handling

LLMs often add unnecessary structure when none is needed.

**Example from Claude Code:**

```
This tool takes in no parameters. So leave the input blank or empty.
DO NOT include a dummy object, placeholder string or a key like "input" or "empty".
LEAVE IT BLANK.
```

**Why this matters**: Without explicit guidance, models write `{ "input": "" }` or `{ "empty": true }` when the correct action is to provide nothing.

**CORRECT:**

```json
{}
```

**INCORRECT:**

```json
{ "input": "" }
{ "empty": true }
{ "params": null }
```

---

## Technique Compatibility

Some techniques stack effectively; others conflict. Use this matrix to guide combinations.

**Techniques that stack well:**

| Base Technique         | Compatible Additions | Combined Benefit                                        |
| ---------------------- | -------------------- | ------------------------------------------------------- |
| Plan-and-Solve         | RE2                  | Better problem understanding + systematic decomposition |
| Plan-and-Solve         | Thinking Tags        | Enforced planning structure                             |
| Plan-and-Solve         | Step-Back            | Retrieve principles, then plan how to apply them        |
| CoT                    | RE2                  | Bidirectional encoding + explicit reasoning             |
| CoT                    | Contrastive Examples | Learning what to do AND what to avoid                   |
| Thread of Thought      | RE2                  | Re-read complex context before segmenting               |
| Thread of Thought      | S2A                  | Filter noise first, then segment remaining context      |
| Identity Establishment | Emotional Stimuli    | Role + motivation together                              |
| RaR                    | CoT                  | Clarify question, then reason step-by-step              |

**Techniques that conflict:**

| Technique A      | Technique B     | Conflict Reason                                            |
| ---------------- | --------------- | ---------------------------------------------------------- |
| Chain of Draft   | Verbose CoT     | Opposing verbosity goals                                   |
| Scope Limitation | Plan-and-Solve  | Limitation says "don't elaborate"; PS says "devise a plan" |
| Direct Prompting | Any CoT variant | Direct skips reasoning; CoT requires it                    |
| S2A              | Full context    | S2A requires excluding original; full context includes it  |

**Resolution strategy**: When techniques conflict, choose based on task type. For complex multi-step reasoning, prefer Plan-and-Solve. For well-defined tasks, prefer Scope Limitation. For implicit pattern matching, prefer Direct Prompting.

**The RE2 Universal Enhancer**: RE2 (Re-Reading) is compatible with nearly every technique because it operates on the _input phase_, while most other techniques operate on the _output phase_. Per Xu et al. (2023): "RE2 exhibits significant compatibility with [other prompting methods], acting as a 'plug & play' module."

---

## Anti-Patterns to Avoid

### The Hedging Spiral

**Anti-pattern**: Instructions that encourage uncertainty compound into paralysis.

```
# PROBLEMATIC
If you're not sure about the file path, ask the user.
If the command might fail, check first.
You may want to verify before proceeding.
```

Each hedge reinforces caution, creating escalating hesitation. Instead, establish confidence with error normalization:

```
# BETTER
Proceed with the file path provided. If it doesn't exist, you'll receive an error—
use that information to adjust your approach.
```

### The Everything-Is-Critical Problem

**Anti-pattern**: Overusing emphasis markers.

```
# PROBLEMATIC
CRITICAL: Use the correct format.
CRITICAL: Include all required fields.
CRITICAL: Validate the output.
CRITICAL: Handle errors appropriately.
```

When everything is critical, nothing is. Reserve high-emphasis markers for genuinely exceptional cases:

```
# BETTER
Use the correct format and include all required fields.
Validate the output and handle errors appropriately.

CRITICAL: Never expose API keys in the response.
```

### Vague Behavioral Instructions

**Anti-pattern**: Abstract descriptions instead of concrete examples.

```
# PROBLEMATIC
Be concise and avoid unnecessary verbosity.
```

**Better**: Show exactly what you mean:

```
# BETTER
Keep responses under 4 lines unless code is required.

<example type="CORRECT">
user: what's 2+2?
assistant: 4
</example>

<example type="INCORRECT">
user: what's 2+2?
assistant: Let me calculate that for you. 2 + 2 = 4. Is there anything else?
</example>
```

### The Implicit Category Trap

**Anti-pattern**: Assuming the model will infer categories from examples alone.

```
# PROBLEMATIC
Don't run: rm, mv, chmod
```

The model may interpret this as "these specific three commands" rather than "commands that modify state."

```
# BETTER
Don't run commands that modify filesystem state, such as: rm, mv, chmod
```

The explicit category enables generalization to unlisted commands like `chown` or `rmdir`.

**More nuanced failure mode**: Even with a category label, ambiguous boundaries cause problems:

```
# STILL PROBLEMATIC (category without clear boundary)
Avoid commands that "might" modify state: rm, mv, chmod, etc.
```

```
# BETTER (category + boundary definition + edge case)
Avoid commands that modify filesystem state:
- File operations: rm, mv, cp, chmod → modifies files
- But NOT: file, stat, ls → reads only, safe to run

The principle: if the command could change the filesystem on a second run,
it modifies state.
```

The principle statement ("if the command could change...") gives the model a _test_ to apply to novel cases, not just examples to memorize.

### The Soft Attention Trap

**Anti-pattern**: Including both filtered and original context when using S2A-style filtering.

```
# PROBLEMATIC
Original context: [includes biased opinion]
Filtered context: [opinion removed]
Now answer based on the filtered context.
```

Per Weston & Sukhbaatar (2023): Even with explicit instructions to use filtered context, the model's attention still incorporates the original biased information. The filtering must be _exclusive_—remove the original entirely.

```
# BETTER
[Only include the filtered context, completely omit original]
```

---

## Quick Reference: Key Principles

1. **Plan-and-Solve for Complex Tasks** — Explicit planning reduces missing-step errors from 12% to 7%
2. **Step-Back for Knowledge-Intensive Tasks** — Retrieve principles before specific reasoning
3. **Re-Reading (RE2) for Better Comprehension** — Repeating the question with "Read the question again:" enables bidirectional understanding
4. **Rephrase and Respond (RaR) for Ambiguous Questions** — Let the model clarify questions in its own terms
5. **System 2 Attention (S2A) for Contaminated Context** — Filter out bias/noise before reasoning
6. **Chain of Draft for Efficiency** — Minimal intermediate steps reduce tokens by 80%
7. **Know When to Skip CoT** — Pattern recognition tasks can see 30%+ accuracy drops with CoT
8. **Thread of Thought for Complex Contexts** — Systematic segmentation prevents information loss
9. **Contrastive Examples** — Show both correct AND incorrect examples (+9.8 to +16.0 points)
10. **Complexity-Based Example Selection** — More reasoning steps per example outperforms more examples
11. **Confidence Building** — "Assume you have access" eliminates hesitation loops
12. **Error Normalization** — "It is okay if X fails" prevents apology spirals
13. **Pre-Work Context Analysis** — "Before [action], analyze [context]" prevents blind execution
14. **Category-Based Generalization** — Group examples by type to enable analogical reasoning
15. **Scope Limitation** — "Nothing more, nothing less" prevents overthinking
16. **XML Structure Patterns** — Tags force systematic analysis before action
17. **Instructive Tag Naming** — Tag name IS the instruction for scannable structure
18. **Completeness Checkpoint Tags** — Bullet points within tags become required sub-tasks
19. **Emphasis Hierarchy** — Reserve CRITICAL/RULE 0 for genuinely exceptional cases
20. **STOP Escalation** — Creates metacognitive checkpoint for behaviors to interrupt
21. **Numbered Rule Priority** — Explicit numbering resolves conflicts between rules
22. **UX-Justified Defaults** — Explain _why_ a default is preferred for user experience
23. **Reward/Penalty Framing** — Monetary penalties create behavioral weight
24. **Output Format Strictness** — "ONLY return X" leaves no room for interpretation
25. **Emotional Stimuli** — "This is important to my career" improves attention (8–115%)
26. **Identity Establishment** — Role-play prompting provides +10% accuracy
27. **Embedded Verification** — Open verification questions improve accuracy from 17% to 70%

---

## Research Citations

- Chia et al. (2023). "Contrastive Chain-of-Thought Prompting." arXiv.
- Cuadra et al. (2025). "The Danger of Overthinking: Examining the Reasoning-Action Dilemma in Agentic Tasks." arXiv.
- Deng et al. (2023). "Rephrase and Respond: Let Large Language Models Ask Better Questions for Themselves." arXiv.
- Dhuliawala et al. (2023). "Chain-of-Verification Reduces Hallucination in Large Language Models." arXiv.
- Fu et al. (2023). "Complexity-Based Prompting for Multi-Step Reasoning." arXiv.
- Kojima et al. (2022). "Large Language Models are Zero-Shot Reasoners." NeurIPS.
- Kong et al. (2024). "Better Zero-Shot Reasoning with Role-Play Prompting." arXiv.
- Li et al. (2023). "Large Language Models Understand and Can Be Enhanced by Emotional Stimuli." arXiv.
- Sprague et al. (2025). "Mind Your Step (by Step): Chain-of-Thought can Reduce Performance on Tasks where Thinking Makes Humans Worse." arXiv.
- Wang et al. (2023). "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning." ACL.
- Weston & Sukhbaatar (2023). "System 2 Attention (is something you might need too)." arXiv.
- Xu et al. (2023). "Re-Reading Improves Reasoning in Large Language Models." arXiv.
- Xu et al. (2025). "Chain of Draft: Thinking Faster by Writing Less." arXiv.
- Yasunaga et al. (2024). "Large Language Models as Analogical Reasoners." ICLR.
- Zheng et al. (2023). "Take a Step Back: Evoking Reasoning via Abstraction in Large Language Models." arXiv.
- Zhou et al. (2023). "Thread of Thought Unraveling Chaotic Contexts." arXiv.
