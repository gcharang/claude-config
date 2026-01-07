# CLAUDE.md

## Overview

Workflow orchestration framework: typed domain model, XML/text formatters, CLI utilities for multi-step agent scripts.

## Index

| File/Directory       | Contents                                                  | Read When                                          |
| -------------------- | --------------------------------------------------------- | -------------------------------------------------- |
| `types.py`           | Domain types: AgentRole, Routing, Dispatch, Step, QRState | Adding workflow, understanding type contracts      |
| `formatters/`        | XML and text output formatters                            | Generating step output, debugging format issues    |
| `formatters/xml.py`  | 26 XML formatters for structured workflow output          | Working with planner/refactor XML output           |
| `formatters/text.py` | Plain text formatters for simple skills                   | Working with problem-analysis/decision-critic      |
| `cli.py`             | Argument parsing, mode_main entry point                   | Creating new workflow script, debugging CLI args   |
| `README.md`          | Architecture, data flow, design decisions                 | Understanding framework design, migration planning |
