# QR Scripts

## Invisible Knowledge

### QR Iteration Blindness

QR scripts NEVER know what iteration they are on. This is **intentional**:

- Prevents confirmation bias ("surely this is fixed by now")
- Each review is a fresh, unbiased assessment
- Progressive de-escalation happens in gate steps, NOT in QR

The `--qr-iteration` flag is used by the orchestrator (planner.py, executor.py)
to control gate filtering. QR scripts do not receive or use this flag.

**Why this matters**: If QR knew it was on iteration 5, it might unconsciously
relax standards or skip checks. By keeping QR iteration-blind, we ensure
consistent quality assessment regardless of how many times we've looped.
