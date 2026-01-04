---
name: doc-sync
description: Synchronizes CLAUDE.md navigation indexes and README.md architecture docs across a repository. Use when asked to "sync docs", "update CLAUDE.md files", "ensure documentation is in sync", "audit documentation", or when documentation maintenance is needed after code changes.
---

# Doc Sync

Maintains the CLAUDE.md navigation hierarchy and README.md invisible knowledge
docs across a repository. This skill is self-contained and performs all
documentation work directly.

## Core Principles

**Self-contained documentation**: All code-adjacent documentation (CLAUDE.md,
README.md) must be self-contained. Do NOT reference external authoritative
sources (doc/ directories, wikis, external documentation). If knowledge exists
in an authoritative source, it must be summarized locally. Duplication is
acceptable; the maintenance burden is the cost of locality.

**CLAUDE.md = pure index**: CLAUDE.md files are navigation aids only. They
contain WHAT is in the directory and WHEN to read each file. All explanatory
content (architecture, decisions, invariants) belongs in README.md.

**README.md = invisible knowledge**: README.md files capture knowledge NOT
visible from reading source code. If ANY invisible knowledge exists for a
directory, README.md is required.

## Scope Resolution

Determine scope FIRST:

| User Request                                            | Scope                                     |
| ------------------------------------------------------- | ----------------------------------------- |
| "sync docs" / "update documentation" / no specific path | REPOSITORY-WIDE                           |
| "sync docs in src/validator/"                           | DIRECTORY: src/validator/ and descendants |
| "update CLAUDE.md for parser.py"                        | FILE: single file's parent directory      |

For REPOSITORY-WIDE scope, perform a full audit. For narrower scopes, operate only within the specified boundary.

## CLAUDE.md Format Specification

### Index Format

Use tabular format with What and When columns:

```markdown
## Files

| File        | What                           | When to read                              |
| ----------- | ------------------------------ | ----------------------------------------- |
| `cache.rs`  | LRU cache with O(1) operations | Implementing caching, debugging evictions |
| `errors.rs` | Error types and Result aliases | Adding error variants, handling failures  |

## Subdirectories

| Directory   | What                          | When to read                              |
| ----------- | ----------------------------- | ----------------------------------------- |
| `config/`   | Runtime configuration loading | Adding config options, modifying defaults |
| `handlers/` | HTTP request handlers         | Adding endpoints, modifying request flow  |
```

### Column Guidelines

- **File/Directory**: Use backticks around names: `cache.rs`, `config/`
- **What**: Factual description of contents (nouns, not actions)
- **When to read**: Task-oriented triggers using action verbs (implementing, debugging, modifying, adding, understanding)
- At least one column must have content; empty cells use `-`

### Trigger Quality Test

Given task "add a new validation rule", can an LLM scan the "When to read" column and identify the right file?

### ROOT vs SUBDIRECTORY CLAUDE.md

**ROOT CLAUDE.md:**

```markdown
# [Project Name]

[One sentence: what this is]

## Files

| File | What | When to read |
| ---- | ---- | ------------ |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |

## Build

[Copy-pasteable command]

## Test

[Copy-pasteable command]

## Development

[Setup instructions, environment requirements, workflow notes]
```

**SUBDIRECTORY CLAUDE.md:**

```markdown
# [directory-name]/

## Files

| File | What | When to read |
| ---- | ---- | ------------ |

## Subdirectories

| Directory | What | When to read |
| --------- | ---- | ------------ |
```

**Critical constraint:** ALL CLAUDE.md files (including subdirectories) are PURE
INDEX. No prose, no overview sections beyond one sentence, no architectural
explanations. Those belong in README.md.

## README.md Specification

### Creation Criteria (Invisible Knowledge Test)

Create README.md when the directory contains ANY invisible knowledge -- knowledge
NOT visible from reading the code:

- Planning decisions (from Decision Log during implementation)
- Business context (why the product works this way)
- Architectural rationale (why this structure)
- Trade-offs made (what was sacrificed for what)
- Invariants (rules that must hold but aren't in types)
- Historical context (why not alternatives)
- Performance characteristics (non-obvious efficiency properties)
- Multiple components interact through non-obvious contracts
- The directory's structure encodes domain knowledge
- Failure modes or edge cases aren't apparent from reading individual files
- "Rules" developers must follow that aren't enforced by compiler/linter

**README.md is required if ANY of the above exist.** The trigger is semantic
(presence of invisible knowledge), not structural (file count, complexity).

**DO NOT create README.md when:**

- The directory is purely organizational with no decisions behind its structure
- All knowledge is visible from reading source code
- You'd only be restating what code already shows

### Content Test

For each sentence in README.md, ask: "Could a developer learn this by reading the source files?"

- If YES: delete the sentence
- If NO: keep it

README.md earns its tokens by providing INVISIBLE knowledge: the reasoning behind the code, not descriptions of the code.

### README.md Structure

```markdown
# [Component Name]

## Overview

[One paragraph: what problem this solves, high-level approach]

## Architecture

[How sub-components interact; data flow; key abstractions]

## Design Decisions

[Tradeoffs made and why; alternatives considered]

## Invariants

[Rules that must be maintained; constraints not enforced by code]
```

## Workflow

### Phase 1: Discovery

Map directories requiring CLAUDE.md verification:

```bash
# Find all directories (excluding .git, node_modules, __pycache__, etc.)
find . -type d \( -name .git -o -name node_modules -o -name __pycache__ -o -name .venv -o -name target -o -name dist -o -name build \) -prune -o -type d -print
```

For each directory in scope, record:

1. Does CLAUDE.md exist?
2. If yes, does it have the required table-based index structure?
3. What files/subdirectories exist that need indexing?

### Phase 2: Audit

For each directory, check for drift and misplaced content:

```
<audit_check dir="[path]">
CLAUDE.md exists: [YES/NO]
Has table-based index: [YES/NO]
Files in directory: [list]
Files in index: [list]
Missing from index: [list]
Stale in index (file deleted): [list]
Triggers are task-oriented: [YES/NO/PARTIAL]
Contains misplaced content: [YES/NO] (architecture/design docs that belong in README.md)
README.md exists: [YES/NO]
README.md warranted: [YES/NO] (invisible knowledge present?)
</audit_check>
```

### Phase 3: Content Migration

**Critical:** If CLAUDE.md contains content that does NOT belong there, migrate it:

Content that MUST be moved from CLAUDE.md to README.md:

- Architecture explanations or diagrams
- Design decision documentation
- Component interaction descriptions
- Overview sections with prose (beyond one sentence)
- Invariants or rules documentation
- Any "why" explanations beyond simple triggers
- Key Invariants sections
- Dependencies sections (explanatory -- index can note dependencies exist)
- Constraints sections
- Purpose sections with prose (beyond one sentence)
- Any bullet-point lists explaining rationale

**Test:** If removing the section leaves CLAUDE.md as just a tabular index with
a one-sentence overview, the removed content belonged in README.md.

Migration process:

1. Identify misplaced content in CLAUDE.md
2. Create or update README.md with the architectural content
3. Strip CLAUDE.md down to pure index format
4. Add README.md to the CLAUDE.md index table

### Phase 4: Index Updates

For each directory needing work:

**Creating/Updating CLAUDE.md:**

1. Use the appropriate template (ROOT or SUBDIRECTORY)
2. Populate tables with all files and subdirectories
3. Write "What" column: factual content description
4. Write "When to read" column: action-oriented triggers
5. If README.md exists, include it in the Files table

**Creating README.md (when invisible knowledge exists):**

1. Verify invisible knowledge exists (semantic trigger, not structural)
2. Document architecture, design decisions, invariants, tradeoffs
3. Apply the content test: remove anything visible from code
4. Keep as concise as possible while capturing all invisible knowledge
5. Must be self-contained: do not reference external authoritative sources

### Phase 5: Verification

After all updates complete, verify:

1. Every directory in scope has CLAUDE.md
2. All CLAUDE.md files use table-based index format (pure navigation)
3. No drift remains (files <-> index entries match)
4. No misplaced content in CLAUDE.md (all prose moved to README.md)
5. README.md files are indexed in their parent CLAUDE.md
6. All CLAUDE.md files contain only: one-sentence overview + tabular index
7. README.md exists wherever invisible knowledge was identified
8. README.md files are self-contained (no external authoritative references)

## Output Format

```
## Doc Sync Report

### Scope: [REPOSITORY-WIDE | directory path]

### Changes Made
- CREATED: [list of new CLAUDE.md files]
- UPDATED: [list of modified CLAUDE.md files]
- MIGRATED: [list of content moved from CLAUDE.md to README.md]
- CREATED: [list of new README.md files]
- FLAGGED: [any issues requiring human decision]

### Verification
- Directories audited: [count]
- CLAUDE.md coverage: [count]/[total] (100%)
- CLAUDE.md format: [count] pure index / [count] needed migration
- Drift detected: [count] entries fixed
- Content migrations: [count] (prose moved to README.md)
- README.md files: [count] (wherever invisible knowledge exists)
- Self-contained: [YES/NO] (no external authoritative references)
```

## Exclusions

DO NOT create CLAUDE.md for:

- Generated files directories (dist/, build/, compiled outputs)
- Vendored dependencies (node_modules/, vendor/, third_party/)
- Git internals (.git/)
- IDE/editor configs (.idea/, .vscode/ unless project-specific settings)
- **Stub directories** (contain only `.gitkeep` or no code files) - these do not
  require CLAUDE.md until code is added

DO NOT index (skip these files in CLAUDE.md):

- Generated files (_.generated._, compiled outputs)
- Vendored dependency files

DO index:

- Hidden config files that affect development (.eslintrc, .env.example, .gitignore)
- Test files and test directories
- Documentation files (including README.md)

## Anti-Patterns

### Index Anti-Patterns

**Too vague (matches everything):**

```markdown
| `config/` | Configuration | Working with configuration |
```

**Content description instead of trigger:**

```markdown
| `cache.rs` | Contains the LRU cache implementation | - |
```

**Missing action verb:**

```markdown
| `parser.py` | Input parsing | Input parsing and format handling |
```

### Correct Examples

```markdown
| `cache.rs` | LRU cache with O(1) get/set | Implementing caching, debugging misses, tuning eviction |
| `config/` | YAML config parsing, env overrides | Adding config options, changing defaults, debugging config loading |
```

## When NOT to Use This Skill

- Single file documentation (inline comments, docstrings) - handle directly
- Code comments - handle directly
- Function/module docstrings - handle directly
- This skill is for CLAUDE.md/README.md synchronization specifically

## Reference

For additional trigger pattern examples, see `references/trigger-patterns.md`.
