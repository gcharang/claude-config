# Code Quality Guidelines

Prompts for LLM agents detecting code smells. Organized by cognitive mode:

| File                               | Cognitive Mode                       |
| ---------------------------------- | ------------------------------------ |
| `01-naming-and-types.md`           | "Do names and types express intent?" |
| `02-structure-and-composition.md`  | "Is this well-structured?"           |
| `03-patterns-and-idioms.md`        | "Is this idiomatic?"                 |
| `04-repetition-and-consistency.md` | "Is this DRY and consistent?"        |
| `05-documentation-and-tests.md`    | "Is this documented and tested?"     |
| `06-module-and-dependencies.md`    | "Are boundaries clean?"              |
| `07-cross-file-consistency.md`     | "Is this consistent across files?"   |
| `08-codebase-patterns.md`          | "What patterns are emerging?"        |

## Applicability Matrix

| Group                       | Design Review | Diff Review | Codebase Review | Refactor Design | Refactor Code |
| --------------------------- | :-----------: | :---------: | :-------------: | :-------------: | :-----------: |
| 01 Naming & Types           |      Yes      |     Yes     |       Yes       |       Yes       |      Yes      |
| 02 Structure & Composition  |      Yes      |     Yes     |       Yes       |       Yes       |      Yes      |
| 03 Patterns & Idioms        |      No       |     Yes     |       Yes       |       No        |      Yes      |
| 04 Repetition & Consistency |      No       |     Yes     |       Yes       |       No        |      Yes      |
| 05 Documentation & Tests    |      No       |     Yes     |       Yes       |       No        |      Yes      |
| 06 Module & Dependencies    |      Yes      |     No      |       Yes       |       Yes       |      Yes      |
| 07 Cross-file Consistency   |      Yes      |     No      |       Yes       |       Yes       |      Yes      |
| 08 Codebase Patterns        |      No       |     No      |       Yes       |       No        |      Yes      |

**Phase definitions**:

- **Design Review**: Evaluating Code Intent before diffs exist
- **Diff Review**: Evaluating proposed code changes in plan
- **Codebase Review**: Evaluating code after implementation
- **Refactor Design**: Analyzing architecture/intent quality in existing code
- **Refactor Code**: Analyzing implementation quality in existing code

## Format Rationale

Each document has a primer followed by numbered categories:

```markdown
<!-- applicable_phases: design_review, diff_review, ... -->

# [Group Name]

[PRIMER: core question, what to look for, threshold]

<design-mode>...</design-mode>
<code-mode>...</code-mode>

---

## 1. Category Name

<principle>
Abstract rule unifying all examples. Stated first to prime generalization.
</principle>

Detect: Detection question framing the evaluation lens.

<grep-hints>
Terms that sometimes indicate issues (starting points, not definitive):
`pattern1`, `pattern2`
</grep-hints>

<violations>
Illustrative patterns (not exhaustive) -- similar violations exist:

[severity] Category label

- Example with "e.g." prefix
- Open-ended: "Any X that causes Y"
  </violations>

<exceptions>
Boundary cases with principle-based test.
</exceptions>

<threshold>
Severity bar for flagging.
</threshold>
```

### Why This Works

| Feature                           | Mechanism                                               |
| --------------------------------- | ------------------------------------------------------- |
| Primer first                      | Establishes cognitive mode before categories            |
| `<principle>` first per category  | Primacy effect -- early content shapes interpretation   |
| "starting points, not definitive" | Hedging breaks literal anchoring                        |
| "e.g.," prefix                    | Signals exemplification vs enumeration                  |
| Open-ended escape hatch           | Keeps violation list unbounded                          |
| XML semantic markers              | Structure for LLM; transparent to line-range extraction |

## Integration

Skills extract sections by line range (regex: `^## \d+\. (.+)$`). Content within sections is free-form -- parser extracts raw text, LLM interprets structure.

### Skill Prompt Additions

Wrap extracted blocks with:

```
<interpretation>
Examples illustrate a PRINCIPLE, not exhaustive checklist.
Detect ANY violation of the principle, including unlisted patterns.
</interpretation>
```

Add analogical prompting after block:

```
GENERALIZATION:
Before searching, identify 2-3 OTHER patterns violating the SAME principle.
Search for BOTH listed exemplars AND self-generated patterns.
```

This triggers domain-specific recall, enabling transfer beyond listed examples.

---

## Invisible Knowledge: Design Decisions

### Why 8 Documents?

These documents are organized by **cognitive mode** -- what the evaluator is
looking at and how they reason about it. This enables:

1. **Focused agents**: the refactor skill gives each explore sub-agent one category: the lines from its `## N.` heading to the next heading. The primer and mode blocks are not part of that slice.

2. **Whole-document review**: agents whose Convention References name `code-quality/CLAUDE.md` read whole documents, choosing them by its applicability table.

### Why Split Categories?

Three categories (Zombie Code, Naming Consistency, Error Pattern Consistency)
have both file-scope and codebase-scope variants. These are split because:

- **File-scope**: Checkable on individual diffs. Used by Diff Review.
- **Codebase-scope**: Requires full codebase view. Used by Codebase Review/Refactor.

Asking a Diff Review agent to find codebase-wide issues is impossible; asking a
Refactor agent to ignore codebase-wide patterns wastes its capabilities.

Split assignments:

| Category                  | File Scope                                        | Codebase Scope                               |
| ------------------------- | ------------------------------------------------- | -------------------------------------------- |
| Zombie Code               | Group 03 (commented blocks, unreachable branches) | Group 08 (0-reference exports, dead modules) |
| Naming Consistency        | Group 01 (same file, different names)             | Group 07 (cross-module drift)                |
| Error Pattern Consistency | Group 04 (within-class inconsistency)             | Group 07 (cross-abstraction-level)           |

### Design vs Code Facets

Each document has two evaluation modes:

- **Design-mode**: For evaluating Code Intent at Design Review. Checks whether
  the proposed design exhibits the smell, based on description alone.

- **Code-mode**: For evaluating actual code at Diff Review, Codebase Review,
  or Refactor. Checks whether the implementation exhibits the smell.

### Which Agents Use Which Documents?

Consumers: `skills/scripts/skills/refactor/refactor.py` (one category per sub-agent) and the agents whose Convention References name `code-quality/CLAUDE.md` (whole documents).

### Machine-Parseable Metadata

Each document contains applicability metadata in an HTML comment at line 1:

```markdown
<!-- applicable_phases: design_review, diff_review, codebase_review, refactor_design, refactor_code -->
```

This approach was chosen for several reasons:

1. **No external dependencies**: HTML comments can be parsed with stdlib regex,
   avoiding dependencies on YAML/TOML parsers or frontmatter libraries.

2. **Invisible to readers**: The metadata doesn't clutter the visible document
   structure, keeping the primer as the first visible content.

3. **Single source of truth**: The evaluation mode (design vs code) is derived
   from the phase: a design-mode phase reads `<design-mode>` content, a
   code-mode phase reads `<code-mode>` content.

`skills/scripts/skills/refactor/refactor.py` (`parse_documents`) reads this comment.
