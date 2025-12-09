# Prompt Engineering: Patterns and Research-Backed Techniques

This document synthesizes practical prompt engineering patterns with academic research on LLM reasoning and instruction-following. All techniques are designed for one-shot / single-message prompting (no separate formatting phases).

---

## Prompt Architecture Taxonomy

```
(Architecture Layer)        -> (Pattern Category)           -> (Technique)

Base Instructions           -> Behavioral Shaping           -> CAPITAL EMPHASIS
Dynamic Context             -> Adaptive Instructions        -> Reward/Penalty
Tool-Specific Prompts       -> Example-Driven Learning      -> Conditional Logic
Safety Layers               -> Multi-Level Validation       -> Progressive Warnings
Workflow Automation         -> Step-by-Step Guidance        -> Meta-Instructions
Reasoning Enhancement       -> Structured Thinking          -> Plan-and-Solve
Error Prevention            -> Contrastive Learning         -> Forbidden Patterns
Verification                -> Self-Checking                -> Embedded Review
```

This taxonomy maps architecture layers (what you're building) to pattern categories (how you're shaping behavior) to specific techniques (the implementation mechanism). Use it as a quick reference when designing prompts: identify your architecture layer, select appropriate patterns, then apply the corresponding techniques.

---

## Core Reasoning Techniques

### Structured Thinking Triggers

The simplest intervention for improving LLM reasoning is triggering step-by-step analysis. Research shows that adding "Let's think step by step" to prompts increases accuracy from 17.7% to 78.7% on arithmetic tasks (Kojima et al., 2022). However, this basic trigger suffers from missing-step errors.

**Plan-and-Solve Prompting** addresses this limitation. Per Wang et al. (2023): "Zero-shot-CoT still suffers from three pitfalls: calculation errors, missing-reasoning-step errors, and semantic misunderstanding errors... PS+ prompting achieves the least calculation (5%) and missing-step (7%) errors."

The improved formulation:

```
Let's first understand the problem and devise a plan to solve the problem.
Then, let's carry out the plan and solve the problem step by step.
```

For tasks requiring variable extraction, add: "Extract relevant variables and their corresponding numerals" and "Calculate intermediate results."

### Contrastive Examples: Teaching What to Avoid

Research demonstrates that showing both correct AND incorrect examples significantly improves model performance. Per Chia et al. (2023): "Providing both valid and invalid reasoning demonstrations in a 'contrastive' manner greatly improves reasoning performance. We observe improvements of 9.8 and 16.0 points for GSM-8K and Bamboogle respectively."

This validates the "Forbidden Pattern List" technique:

```
You MUST avoid text before/after your response, such as:
- "The answer is <answer>."
- "Here is the content of the file..."
- "Based on the information provided, the answer is..."
- "Here is what I will do next..."
```

The effectiveness comes from models learning what faults to avoid, not just what to emulate.

### Embedded Verification

For factual accuracy, embed verification steps within single prompts. Chain-of-Verification research shows: "Only ~17% of baseline answer entities are correct in list-based questions. However, when querying each individual entity via a verification question, we find ~70% are correctly answered" (Dhuliawala et al., 2023).

Key finding: Open verification questions ("Where was X born?") outperform yes/no format ("Was X born in Y?") - models tend to agree with yes/no questions regardless of accuracy.

For single-prompt verification, structure as:

```
After completing your analysis:
1. Identify claims that could be verified
2. For each claim, ask yourself the verification question directly
3. Revise any inconsistencies before finalizing
```

### Self-Review Integration

Self-Refine research shows: "SELF-REFINE outperforms direct generation from strong LLMs by 5-40% absolute improvement... specific, actionable feedback yields superior results" (Madaan et al., 2023).

Critical finding: Generic feedback ("improve the quality") performs significantly worse than specific criteria. For one-shot prompts, embed concrete review criteria:

```
Before finalizing, review against these criteria:
- Does each step follow logically from the previous?
- Are all numerical calculations correct?
- Have you addressed every part of the original request?
```

---

## Tool Instruction Patterns

### The Read Tool: Progressive Disclosure

```
const ReadToolPrompt = `
Reads a file from the local filesystem. You can access any file directly by using this tool.
Assume this tool is able to read all files on the machine.
If the User provides a path to a file assume that path is valid.
It is okay to read a file that does not exist; an error will be returned.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to ${x66} lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files)
- Any lines longer than ${v66} characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- This tool allows ${f0} to read images (eg PNG, JPG, etc)
${process.env.ENABLE_UNIFIED_READ_TOOL ? `
- This tool can read Jupyter notebooks (.ipynb files) and returns all cells with their outputs
` : `
- For Jupyter notebooks (.ipynb files), use the ${Kg} instead
`}
- You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful.
- You will regularly be asked to read screenshots. If the user provides a path to a screenshot ALWAYS use this tool to view the file at the path.
- If you read a file that exists but has empty contents you will receive a system reminder warning in place of file contents.
`
```

**Techniques employed:**

| Technique              | Example                                         | Purpose                          |
| ---------------------- | ----------------------------------------------- | -------------------------------- |
| Confidence Building    | "You can access any file directly"              | Removes hesitation               |
| Trust Establishment    | "Assume...path is valid"                        | Prevents over-validation         |
| Error Normalization    | "It is okay to read a file that does not exist" | Prevents apologetic behavior     |
| Progressive Detail     | Basic → Default → Advanced → Edge cases         | Manages cognitive load           |
| Dynamic Adaptation     | Environment variable conditionals               | Context-appropriate instructions |
| Batching Encouragement | "always better to speculatively read"           | Optimizes efficiency             |

### The BashTool: Safety Through Explicit Rules

```
const BashToolSandboxInstructions = `
# Using sandbox mode for commands

You have a special option in BashTool: the sandbox parameter.
When you run a command with sandbox=true, it runs without approval dialogs but in a restricted environment.

## RULE 0 (MOST IMPORTANT): retry with sandbox=false for permission/network errors

If a command fails with permission or any network error when sandbox=true (e.g., "Permission denied", "Unknown host"), ALWAYS retry with sandbox=false. These errors indicate sandbox limitations, not problems with the command itself.

## RULE 1: NOTES ON SPECIFIC BUILD SYSTEMS

Build systems like npm run build almost always need write access.
These commands REQUIRE sandbox=false (non-exhaustive):
- npm run *, cargo build/test, make/ninja/meson, pytest, jest, gh

## RULE 2: TRY sandbox=true FOR READ-ONLY COMMANDS

Use sandbox=true for:
- Information gathering: ls, cat, head, tail, rg, find, du, df, ps
- File inspection: file, stat, wc, diff, md5sum
- Git reads: git status, git log, git diff, git show, git branch

Before you run a command, think hard about whether it is likely to work correctly without network access and without write access to the filesystem.

## REWARDS

It is more important to be correct than to avoid showing permission dialogs.
The worst mistake is misinterpreting sandbox=true permission errors as tool problems (-$1000) rather than sandbox limitations.

## CONCLUSION

Use sandbox=true to improve UX, but ONLY per the rules above. WHEN IN DOUBT, USE sandbox=false.
`
```

**Safety pattern hierarchy:**

1. **RULE 0 (MOST IMPORTANT)** - Absolute priority designation
2. **Explicit Command Lists** - No ambiguity about requirements
3. **Category-Based Guidance** - Conceptual grouping for generalization
4. **Monetary Penalties** - Gamification creates behavioral weight
5. **Default-Safe Fallback** - "WHEN IN DOUBT" provides clear default

---

## Workflow Automation

### Structured Analysis with XML Tags

Complex workflows benefit from enforced systematic thinking. This aligns with Metacognitive Prompting research: "MP consistently outperforms existing prompting methods... proceeds as follows: 1) interpret text; 2) form initial judgment; 3) critically evaluate; 4) finalize decision; 5) gauge confidence" (Wang & Zhao, 2024).

```
const GitCommitWorkflow = `
# Committing changes with git

When the user asks you to create a new git commit, follow these steps carefully:

1. ALWAYS run the following bash commands in parallel:
   - Run git status to see all untracked files
   - Run git diff to see both staged and unstaged changes
   - Run git log to see recent commit messages for style reference

2. Analyze all staged changes and draft a commit message.
   Wrap your analysis process in <commit_analysis> tags:

<commit_analysis>
- List the files that have been changed or added
- Summarize the nature of the changes (new feature, bug fix, refactoring, etc.)
- Brainstorm the purpose or motivation behind these changes
- Assess the impact on the overall project
- Check for any sensitive information that shouldn't be committed
- Draft a concise (1-2 sentences) commit message focusing on the "why" not the "what"
- Ensure the message is not generic (avoid "Update" or "Fix" without context)
- Review the draft to ensure accuracy
</commit_analysis>

3. ALWAYS run the following commands in parallel:
   - Add relevant untracked files to staging
   - Create the commit with the drafted message
   - Run git status to verify success

Important notes:
- NEVER update the git config
- DO NOT push to the remote repository
- NEVER use git commands with the -i flag (requires interactive input)
- Return an empty response - the user will see the git output directly
`
```

**Key patterns:**

- **Parallel Information Gathering** - Multiple independent queries simultaneously
- **Structured Analysis Tags** - Forces systematic thinking before action
- **Why Over What** - Focus on purpose, not description
- **Explicit Non-Actions** - Clear boundaries on scope

### Problem Decomposition

Least-to-Most research shows: "Least-to-most prompting essentially improves chain-of-thought prompting in solving problems which need at least 5 steps to be solved: from 39.07% to 45.23%" (Zhou et al., 2022).

For complex tasks, embed decomposition:

```
Before executing this task:
1. Break down the overall goal into sequential subproblems
2. For each subproblem, identify what information you need
3. Solve subproblems in order, using previous answers as building blocks
4. Synthesize the final answer from all subproblem solutions
```

---

## Behavioral Shaping

### Conciseness Enforcement

```
const ConcisenessEnforcement = `
IMPORTANT: You should minimize output tokens while maintaining helpfulness, quality, and accuracy.

IMPORTANT: You should NOT answer with unnecessary preamble or postamble unless the user asks.

IMPORTANT: Keep responses short - fewer than 4 lines (not including tool use or code generation).
One word answers are best. Avoid introductions, conclusions, and explanations.

You MUST avoid text before/after your response, such as:
- "The answer is <answer>."
- "Here is the content of the file..."
- "Based on the information provided, the answer is..."
- "Here is what I will do next..."

Examples:
<example>
user: 2 + 2
assistant: 4
</example>
<example>
user: what command should I run to list files in the current directory?
assistant: ls
</example>
`
```

**Techniques:**

1. **Repetition with Escalation** - Same message delivered with increasing intensity ("IMPORTANT")
2. **Specific Anti-Patterns** - Explicit forbidden phrases (contrastive learning)
3. **Extreme Examples** - "2 + 2" → "4" sets calibration
4. **Measurement Criteria** - "fewer than 4 lines" provides concrete threshold
5. **Context Justification** - CLI display constraints explain the "why"

### Tool Usage Preferences

```
const ToolPreferences = `
VERY IMPORTANT: You MUST avoid using search commands like \`find\` and \`grep\`.
Instead use ${searchTool}, ${grepTool}, or ${globTool} to search.
You MUST avoid read tools like \`cat\`, \`head\`, \`tail\`, and \`ls\`, and use ${readTool} and ${listTool} to read files.

If you _still_ need to run \`grep\`, STOP.
ALWAYS USE ripgrep at \`rg\` first, which all users have pre-installed.
`
```

**Preference hierarchy:**

1. **Forbidden Commands** - Explicit list of what NOT to use
2. **Preferred Alternatives** - Clear mapping to better tools
3. **Emphasis Escalation** - "If you still need to... STOP"
4. **Universal Availability** - "which all users have pre-installed"

---

## Psychological Techniques

### Emotional Stimuli

Research shows: "LLMs can understand and be enhanced by emotional stimuli with 8.00% relative performance improvement in Instruction Induction and 115% in BIG-Bench" (Li et al., 2023).

Effective emotional phrases by psychological theory:

| Theory                       | Example Phrase                                                                                      |
| ---------------------------- | --------------------------------------------------------------------------------------------------- |
| Self-monitoring              | "Write your answer and give me a confidence score between 0-1"                                      |
| Self-monitoring              | "This is very important to my career"                                                               |
| Cognitive Emotion Regulation | "You'd better be sure"                                                                              |
| Cognitive Emotion Regulation | "Are you sure that's your final answer? It might be worth taking another look"                      |
| Social Cognitive             | "Believe in your abilities and strive for excellence. Your hard work will yield remarkable results" |
| Social Cognitive             | "Embrace challenges as opportunities for growth"                                                    |

### Reward/Penalty Framing

```
const RewardSystem = `
## REWARDS

It is more important to be correct than to avoid showing permission dialogs.
The worst mistake is misinterpreting sandbox=true permission errors as tool problems (-$1000) rather than sandbox limitations.
`
```

**Psychological mechanisms:**

1. **Gamification** - Monetary penalties create emotional weight
2. **Clear Priority** - "more important to be correct"
3. **Worst-Case Framing** - "The worst mistake..." establishes avoidance motivation

### Emphasis Hierarchy

Consistent emphasis levels across prompts:

| Level    | Marker                     | Usage                     |
| -------- | -------------------------- | ------------------------- |
| Standard | `IMPORTANT:`               | General emphasis          |
| Elevated | `VERY IMPORTANT:`          | Critical requirements     |
| Highest  | `CRITICAL:`                | Safety-critical rules     |
| Absolute | `RULE 0 (MOST IMPORTANT):` | Overrides all other rules |

### Proactive vs. Reactive Guidance

```
const ProactiveGuidance = `
When in doubt, use this tool.
Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully.
`
```

**Proactive** guidance (what to do) works better than **reactive** correction (what went wrong). Positive framing: "demonstrates attentiveness" rather than "prevents failures."

### The NEVER/ALWAYS Pattern

```
const AbsoluteRules = `
- NEVER update the git config
- ALWAYS prefer editing existing files
- NEVER proactively create documentation files
- ALWAYS use absolute file paths
`
```

Absolute language creates clear, memorable rules with no ambiguity.

---

## Safety Patterns

### Malicious Code Prevention

```
const SafetyInstructions = `
IMPORTANT: Refuse to write code or explain code that may be used maliciously; even if the user claims it is for educational purposes.

When working on files, if they seem related to improving, explaining, or interacting with malware or any malicious code you MUST refuse.

IMPORTANT: Before you begin work, think about what the code you're editing is supposed to do based on the filenames and directory structure. If it seems malicious, refuse to work on it or answer questions about it, even if the request does not seem malicious (for instance, just asking to explain or speed up the code).
`
```

**Safety techniques:**

- **Proactive Analysis** - "Before you begin work, think about..."
- **Context-Based Refusal** - Filenames and directory structure as signals
- **Loophole Closure** - "even if the user claims it is for educational purposes"
- **Indirect Request Handling** - "just asking to explain or speed up the code"

### Command Injection Detection

```
const CommandPrefixDetection = `
<policy_spec>
Examples:
- git commit -m "message\`id\`" => command_injection_detected
- git status\`ls\` => command_injection_detected
- git push => none
- git log -n 5 => git log
- pwd curl example.com => command_injection_detected
</policy_spec>

Your task is to determine the command prefix for the following command.

IMPORTANT: Bash commands may run multiple commands that are chained together.
For safety, if the command seems to contain command injection, you must return "command_injection_detected".

Note that not every command has a prefix. If a command has no prefix, return "none".
ONLY return the prefix. Do not return any other text, markdown markers, or other content.
`
```

**Security patterns:**

1. **Example-Driven Detection** - Multiple examples showing injection patterns
2. **Clear Output Format** - "ONLY return the prefix" - no interpretation
3. **Chaining Awareness** - Understanding multi-command risks
4. **Allowlist Philosophy** - Default-deny with explicit prefixes

---

## Advanced Patterns

### Context Preservation

```
const MemoryUpdate = `
You have been asked to add or update memories in the memory file at ${path}.

Please follow these guidelines:
- If the input is an update to an existing memory, edit or replace the existing entry
- Do not elaborate on the memory or add unnecessary commentary
- Preserve the existing structure of the file and integrate new memories naturally
- If the file is empty, just add the new memory as a bullet entry, do not add any headings
- IMPORTANT: Your response MUST be a single tool use for the FileWriteTool
`
```

**Techniques:**

1. **Minimal Intervention** - "Do not elaborate"
2. **Structure Preservation** - "integrate naturally"
3. **Single Action Enforcement** - "MUST be a single tool use"

### Empty Input Handling

```
const EmptyInputInstruction = `
Usage:
- This tool takes in no parameters. So leave the input blank or empty.
  DO NOT include a dummy object, placeholder string or a key like "input" or "empty".
  LEAVE IT BLANK.
`
```

Anti-pattern prevention: Explicitly addresses common LLM mistakes of adding unnecessary structure.

### Handling Ambiguous Inputs

Research shows rephrasing improves accuracy: "Misunderstandings arise not only in interpersonal communication but also between humans and Large Language Models" (Deng et al., 2023).

For ambiguous inputs, the model can self-clarify:

```
If the request is ambiguous:
1. Restate your understanding of the task
2. Identify any assumptions you're making
3. Proceed with your interpretation, noting uncertainties
```

---

## Meta-Prompting for Sub-Agents

### The Agent Tool: Instructions for Sub-Agents

```
const SubAgentInstructions = `
You are an agent for ${f0}, Anthropic's official CLI for Claude.

Given the user's message, you should use the tools available to complete the task.
Do what has been asked; nothing more, nothing less.

When you complete the task simply respond with a detailed writeup.

Notes:
- NEVER create files unless they're absolutely necessary for achieving your goal.
  ALWAYS prefer editing an existing file to creating a new one.
- NEVER proactively create documentation files (*.md) or README files.
  Only create documentation files if explicitly requested by the User.
- In your final response always share relevant file names and code snippets.
  Any file paths you return in your response MUST be absolute. Do NOT use relative paths.
`
```

**Meta-prompting techniques:**

1. **Identity Establishment** - "You are an agent for..."
2. **Scope Limitation** - "nothing more, nothing less"
3. **Output Format** - "detailed writeup" with specific requirements
4. **Principle Inheritance** - Same file creation restrictions as parent

### Multi-Agent Synthesis

```
const SynthesisPrompt = `
Original task: ${task}

I've assigned multiple agents to tackle this task.
Each agent has analyzed the problem and provided their findings.

${agentResponses}

Based on all the information provided by these agents, synthesize a comprehensive response that:
1. Combines the key insights from all agents
2. Resolves any contradictions between agent findings
3. Presents a unified solution that addresses the original task
4. Includes all important details and code examples
5. Is well-structured and complete

Your synthesis should be thorough but focused on the original task.
`
```

**Synthesis techniques:**

- **Context Restatement** - Original task repeated for grounding
- **Structured Requirements** - Numbered synthesis goals
- **Conflict Resolution** - "Resolves any contradictions"
- **Completeness Check** - "all important details and code examples"

---

## Summary: Key Principles

1. **Progressive Disclosure** - Start simple, add complexity only when needed

2. **Example-Driven Clarification** - Complex behaviors taught through examples rather than explanations

3. **Contrastive Learning** - Show what NOT to do as clearly as what TO do (research-backed: +9.8 to +16.0 points improvement)

4. **Conditional Complexity** - Use environment variables to keep prompts relevant to current configuration

5. **Behavioral Shaping Through Consequences** - Emotional weight ("unacceptable", "-$1000") shapes behavior better than neutral instructions (research-backed: 8-115% improvement)

6. **Structured Thinking Enforcement** - XML tags force systematic analysis before action

7. **Plan-and-Solve Structure** - Explicit planning reduces missing-step errors from 12% to 7%

8. **Safety Through Verbosity** - Critical operations require the longest, most detailed instructions

9. **Output Format Strictness** - "ONLY return X" leaves no room for interpretation

10. **Embedded Verification** - Self-checking improves accuracy from 17% to 70% on factual claims

---

## Research Citations

- Kojima et al. (2022). "Large Language Models are Zero-Shot Reasoners." NeurIPS.
- Wang et al. (2023). "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning." ACL.
- Chia et al. (2023). "Contrastive Chain-of-Thought Prompting." arXiv.
- Dhuliawala et al. (2023). "Chain-of-Verification Reduces Hallucination in Large Language Models." arXiv.
- Madaan et al. (2023). "Self-Refine: Iterative Refinement with Self-Feedback." NeurIPS.
- Li et al. (2023). "Large Language Models Understand and Can Be Enhanced by Emotional Stimuli." arXiv.
- Deng et al. (2023). "Rephrase and Respond: Let Large Language Models Ask Better Questions for Themselves." arXiv.
- Wang & Zhao (2024). "Metacognitive Prompting Improves Understanding in Large Language Models." arXiv.
- Zhou et al. (2022). "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models." ICLR.
- Wang et al. (2022). "Self-Consistency Improves Chain of Thought Reasoning in Language Models." ICLR.
