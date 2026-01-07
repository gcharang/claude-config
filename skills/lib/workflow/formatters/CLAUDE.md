# formatters/

XML and text output formatters for workflow scripts.

## Files

| File      | What                                    | When to read                                  |
| --------- | --------------------------------------- | --------------------------------------------- |
| `xml.py`  | 26 XML formatters for structured output | Working with planner/refactor XML output      |
| `text.py` | Plain text formatters for simple skills | Working with problem-analysis/decision-critic |

## Key Functions

| Function                 | What                           | When to read                                   |
| ------------------------ | ------------------------------ | ---------------------------------------------- |
| `format_qr_file_output`  | QR sub-agent minimal output    | Debugging QR gate routing, premature fix issue |
| `format_post_qr_routing` | Dispatch step routing guidance | Understanding QR->gate step flow               |
| `format_gate_actions`    | Gate step action generation    | Understanding fix vs pass routing              |

## Invisible Knowledge

See `lib/workflow/README.md` "Invisible Knowledge" section for turn boundary isolation constraint. Key insight: `format_qr_file_output()` includes `<orchestrator_action>` block because guidance in dispatch step output is forgotten after sub-agent returns.
