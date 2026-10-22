# arxiv-to-md

Convert arXiv papers (TeX source) to clean, LLM-consumable markdown.

## Architecture

`main.py` prints the orchestrator's steps; its `build_next_command` is the step map.
Step 2 prints one `convert.py` command per paper, which the main session runs in
parallel Bash calls; `convert.py` converts the paper without a model and writes the
Markdown file. Step 3 dispatches the `arxiv-latex-reviewer` agent (`agents/arxiv-latex-reviewer.md`:
Read and Edit only) for each file in which the converter flagged LaTeX left outside
math and code; the agent definition holds the repair rules and the dispatch prompt
holds the path and line numbers. Step 4 re-scans the reviewed files and reports that
scan, not the reviewers' replies.

## Usage

Single paper:

```
Convert arxiv.org/abs/2503.05179 to markdown
```

Multiple papers:

```
Convert these papers to markdown: 2503.05179, 2401.12345, 2312.09876
```

## Prerequisites

- pandoc 2.15 or later on PATH (`brew install pandoc` or equivalent); `convert.py` runs it with `--sandbox`
- Python 3.11.4 or later, for tarfile's extraction filters

## Invisible Knowledge

**Why a script converts and a model only reviews:**

Every conversion step but two has one correct result for a given input. A model
running them re-typed the whole paper through Write, and two verification steps
existed to catch what the re-typing dropped. `convert.py` writes pandoc's output after
deterministic cleaning, so nothing is re-typed. Judgment remains for LaTeX that pandoc
left in the text, which the review sub-agent repairs, and for choosing the main file
among several `\documentclass` files, which `convert.py` reports with the candidates'
paths for the main session to pass back as `--main-tex`.

**Why the review is a sub-agent:**

The Edit tool needs the file read first, and a converted paper runs to tens of
thousands of tokens; a sub-agent keeps that reading out of the orchestrator's context.
It runs on Opus; whether Sonnet suffices for a local rewrite of the flagged lines has
not been measured.

**Why step 1 discovers from folder metadata:**

Users often invoke this skill from a directory containing paper-related files
(PDFs, .bib files, READMEs with arXiv links). Discovering IDs from context
reduces friction and avoids user having to manually extract IDs they've already
referenced elsewhere.

**Handoff minimalism:**

The review sub-agent receives one file path and the numbers of its flagged lines. It has no Bash tool and treats the paper's text as data. It doesn't know how many papers are being processed or what the
orchestrator does with its reply.
