#!/usr/bin/env python3
"""Phase-parameterized QR fix runner.

One runner for the QR phases that have a fix route (shared.routing.WORK_PHASES);
--phase selects which phase's fix content (prompts/fix.FIX_CONTENT) drives the
shared fix_dispatch_step. The control flow and step-1 load factor into
prompts/fix, so this file only wires --phase to its content. The work-phase routers reach it via
shared.routing.WORK_PHASES["*"]["qr_fix"].
"""

from skills.planner.quality_reviewer.prompts.fix import fix_dispatch_step, get_fix_content


def get_step_guidance(step: int, module_path: str, **kwargs) -> dict:
    phase = kwargs["phase"]
    state_dir = kwargs.get("state_dir", "")
    return fix_dispatch_step(step, phase, module_path, get_fix_content(phase), state_dir)


if __name__ == "__main__":
    from skills.planner.quality_reviewer.qr_verify_base import fix_main

    fix_main(
        __file__,
        get_step_guidance,
        "QR-Fix: Targeted repair for a QR phase's failures (--phase selects)",
    )
