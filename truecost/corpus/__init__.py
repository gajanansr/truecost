"""Task corpora: what each subject is measured on.

Two axes, because either one alone is attackable.

**`claim/`** reproduces a tool's own published benchmark — its fixture, its
question, verbatim. This is the number its maintainer cannot call
unrepresentative, because they chose it. Reproducing Portal's benchmark
question #1 against a file 10x their own fixture is what turned a disputed
claim into a settled one.

**`neutral/`** is one versioned task set on pinned real repositories, identical
across subjects, which is the only way to compare tools to each other. It is
also the more attackable of the two — "your tasks don't represent my use case"
is the reply to every bad grade — which is why the `claim/` number is published
beside it.

Every corpus must supply a **control task** on which the subject's mechanism
cannot fire. Controls are the only defence against a corpus written to produce
a conclusion, and they have earned it twice by returning a 0.00 turn change.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from truecost.core.runner import Task


@dataclass(frozen=True)
class Corpus:
    """A built corpus: tasks, plus the shell that restores state between runs."""

    tasks: list[Task]
    reset_command: str
    root: Path
    # Named so a report can say which corpus produced a number.
    axis: str  # "claim" | "neutral"
    source: str = ""  # for claim corpora: the URL of the benchmark reproduced

    def __post_init__(self) -> None:
        if self.axis not in ("claim", "neutral"):
            raise ValueError(f"axis must be 'claim' or 'neutral', got {self.axis!r}")
        if not any(t.task_id == "control" for t in self.tasks):
            raise ValueError(
                f"corpus {self.axis!r} has no 'control' task. A corpus with no task "
                "on which the mechanism cannot fire cannot detect its own bias."
            )


@runtime_checkable
class CorpusBuilder(Protocol):
    """What a corpus module must expose.

    `requires` names packages the corpus needs that truecost does not depend on
    — a subject's own library, for instance. Declared rather than imported at
    module scope, so a missing dependency skips one subject with a clear
    message instead of breaking the CLI for everyone.
    """

    axis: str
    requires: tuple[str, ...]

    def build(self, workdir: Path, settings: Path) -> Corpus: ...


_REGISTRY: dict[str, CorpusBuilder] = {}


def register(subject: str, builder: CorpusBuilder) -> None:
    _REGISTRY[f"{subject}:{builder.axis}"] = builder


def get(subject: str, axis: str) -> CorpusBuilder | None:
    return _REGISTRY.get(f"{subject}:{axis}")


def available(subject: str, axis: str) -> tuple[bool, str]:
    """Can this corpus run here? Returns (ok, reason-if-not)."""
    import importlib.util

    builder = get(subject, axis)
    if builder is None:
        return False, f"no {axis} corpus registered for {subject!r}"
    missing = [m for m in builder.requires if importlib.util.find_spec(m) is None]
    if missing:
        return False, f"{subject}:{axis} needs {', '.join(missing)} installed"
    return True, ""


def load_builtin() -> None:
    """Import the shipped corpora so they register themselves."""
    from truecost.corpus.claim import contextmesh  # noqa: F401
