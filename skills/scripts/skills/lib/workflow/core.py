"""Data-driven workflow architecture.

Pure data-driven Workflow/StepDef architecture where:
- Workflows are frozen dataclasses with embedded callables
- Transitions are explicit via next: dict[Outcome, str]
- Parameters use Annotated[T, Arg(...)] on handlers
- Step context passes runtime state between steps
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, Callable, get_args, get_origin, get_type_hints

from .types import Dispatch, QRStatus


class Outcome(str, Enum):
    """Step execution outcomes for explicit transition routing."""

    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"
    ITERATE = "iterate"
    DEFAULT = "_default"


@dataclass(frozen=True)
class Arg:
    """Parameter metadata for Annotated[T, Arg(...)] on handlers."""

    description: str = ""
    default: Any = inspect.Parameter.empty
    min: int | float | None = None
    max: int | float | None = None
    choices: tuple[str, ...] | None = None
    required: bool = False


@dataclass
class StepContext:
    """Runtime context passed to handlers."""

    step_id: str
    workflow_params: dict[str, Any]
    step_state: dict[str, Any]


@dataclass(frozen=True)
class StepDef:
    """Step definition with explicit transitions."""

    id: str
    title: str
    actions: list[str]
    handler: Callable[[StepContext], tuple[Outcome, dict]] | Dispatch | None = None
    next: dict[Outcome, str | None] = field(default_factory=dict)
    on_error: str | None = None
    phase: str | None = None


class Workflow:
    """Data-driven workflow with embedded step definitions."""

    _module_path: str | None = None

    def __init__(
        self,
        name: str,
        *steps: StepDef,
        entry_point: str | None = None,
        description: str = "",
        validate: bool = True,
    ):
        ids = [s.id for s in steps]
        if dupes := [x for x in ids if ids.count(x) > 1]:
            raise ValueError(f"Duplicate step IDs: {set(dupes)}")

        self.name = name
        self.description = description
        self.steps = {s.id: s for s in steps}
        self._step_order = [s.id for s in steps]
        self.entry_point = entry_point or steps[0].id
        self._params: dict[str, list[dict]] = {}

        if validate:
            self._validate()

    def _validate(self):
        """Validate workflow structure."""
        # 1. Entry point exists
        if self.entry_point not in self.steps:
            raise ValueError(f"entry_point '{self.entry_point}' not in steps")

        # 2. All transition targets exist
        for step in self.steps.values():
            for outcome, target in step.next.items():
                if target is not None and target not in self.steps:
                    raise ValueError(
                        f"Step '{step.id}' -> '{target}': target not found"
                    )

        # 3. At least one terminal step
        terminals = [s for s in self.steps.values() if None in s.next.values()]
        if not terminals:
            raise ValueError("No terminal step (next -> None)")

        # 3.5. Non-terminal steps must have handlers
        for step in self.steps.values():
            is_terminal = None in step.next.values()
            if not is_terminal and step.handler is None:
                raise ValueError(
                    f"Step '{step.id}' has no handler but is not terminal "
                    f"(next={step.next}). Non-terminal steps must have handlers."
                )

        # 4. All steps reachable from entry_point
        visited = set()
        queue = [self.entry_point]
        while queue:
            sid = queue.pop(0)
            if sid in visited or sid is None:
                continue
            visited.add(sid)
            step = self.steps[sid]
            queue.extend(t for t in step.next.values() if t)
            if step.on_error:
                queue.append(step.on_error)
        unreachable = set(self.steps.keys()) - visited
        if unreachable:
            raise ValueError(f"Unreachable steps: {unreachable}")

        # 5. Extract params from handlers
        for step in self.steps.values():
            if callable(step.handler) and not isinstance(step.handler, Dispatch):
                self._params[step.id] = self._extract_params(step.handler)

    def _extract_params(self, fn: Callable) -> list[dict]:
        """Extract Arg metadata from handler signature."""
        params = []
        try:
            hints = get_type_hints(fn, include_extras=True)
        except Exception:
            hints = {}

        sig = inspect.signature(fn)
        for pname, param in sig.parameters.items():
            if pname in ("self", "ctx", "context"):
                continue

            hint = hints.get(pname, Any)
            arg = Arg()
            type_name = "Any"

            if get_origin(hint) is Annotated:
                args = get_args(hint)
                type_name = getattr(args[0], "__name__", str(args[0]))
                for meta in args[1:]:
                    if isinstance(meta, Arg):
                        arg = meta
                        break
            elif hasattr(hint, "__name__"):
                type_name = hint.__name__

            has_default = param.default is not inspect.Parameter.empty
            default_value = param.default if has_default else arg.default
            if default_value is inspect.Parameter.empty:
                default_value = None
            params.append(
                {
                    "name": pname,
                    "type": type_name,
                    "description": arg.description,
                    "min": arg.min,
                    "max": arg.max,
                    "choices": list(arg.choices) if arg.choices else None,
                    "required": arg.required if not has_default else False,
                    "default": default_value,
                }
            )
        return params

    def run(self, params: dict, start_step: str | None = None) -> dict:
        """Execute workflow from start_step."""
        ctx = StepContext(
            step_id=start_step or self.entry_point,
            workflow_params=params,
            step_state={},
        )

        while ctx.step_id is not None:
            step = self.steps[ctx.step_id]

            if step.handler is None:
                # No handler = output step, return context
                return {"step": ctx.step_id, "state": ctx.step_state}

            if isinstance(step.handler, Dispatch):
                # QR gate dispatch - handled by caller
                return {"dispatch": step.handler, "step": ctx.step_id}

            try:
                outcome, next_state = step.handler(ctx)
                ctx.step_state.update(next_state)
            except Exception as e:
                if step.on_error:
                    ctx.step_id = step.on_error
                    ctx.step_state["_error"] = str(e)
                    continue
                raise

            ctx.step_id = step.next.get(outcome) or step.next.get(Outcome.DEFAULT)

        return {"completed": True, "state": ctx.step_state}

    @property
    def total_steps(self) -> int:
        return len(self.steps)
