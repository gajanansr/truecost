"""Benchmark arms, including third-party context tools.

No tool in this category publishes a reproducible, cache-aware measurement.
This module defines the unit of comparison so any of them can be measured on
equal terms. Subjects are declared in `subjects/*.toml`, never here: a core
that hardcodes the tools it audits cannot be trusted to audit them.

An arm is everything that distinguishes one condition from another:

- `env`            environment overlay (how ContextMesh's own arms work)
- `command_prefix` wrapper argv, e.g. ("headroom", "wrap") or ("rtk",)
- `settings`       a `claude --settings` file, for hook-based tools
- `setup`/`teardown` shell run once around the arm, for tools needing a proxy

## On honesty about third-party arms

Delivery verification is the check that separates "this feature does not help"
from "this feature never ran"; it has already rescued three runs here. For
ContextMesh we verify delivery by finding an injected block in the session
transcript. For a third-party tool that compresses in a proxy, there may be no
transcript-visible evidence at all.

So each arm declares `delivery_marker` when its effect is observable and
`None` when it is not. An arm with no marker is not silently trusted: the
report labels it UNVERIFIED, and any conclusion drawn from it is weaker than
one drawn from a verified arm. Publishing a comparison that quietly assumes a
competitor's tool was active would be the same error this harness exists to
prevent, pointed at someone else.

Nothing here installs anything. Unavailable arms are skipped and named.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Arm:
    """One condition under test."""

    name: str
    env: dict[str, str] = field(default_factory=dict)
    command_prefix: tuple[str, ...] = ()
    settings: Path | None = None
    # Extra argv appended to the `claude` invocation, e.g. --mcp-config for a
    # tool the agent calls rather than one that injects behind its back.
    extra_args: tuple[str, ...] = ()
    setup: str | None = None
    teardown: str | None = None
    # Executables that must be on PATH for this arm to run at all.
    requires: tuple[str, ...] = ()
    # A string whose presence in the session transcript proves the arm's
    # treatment actually reached the model. None means unverifiable -- see the
    # module docstring.
    delivery_marker: str | None = None
    # Whether the marker is *expected* to be present. Control arms expect
    # absence, which is how treatment leaking into a baseline gets caught.
    expects_marker: bool = True
    notes: str = ""

    @property
    def verifiable(self) -> bool:
        return self.delivery_marker is not None

    def missing_requirements(self) -> list[str]:
        return [exe for exe in self.requires if shutil.which(exe) is None]

    def available(self) -> tuple[bool, str]:
        missing = self.missing_requirements()
        if missing:
            return False, f"{self.name}: not installed ({', '.join(missing)})"
        return True, ""


# ── Registry ────────────────────────────────────────────────────────────────
#
# Empty by design. Subjects are loaded from `subjects/*.toml` via
# truecost.manifest and registered through truecost.core.runner.register_arms,
# which owns both this table and the env-only view run_once validates against.

ALL_ARMS: dict[str, Arm] = {}


def resolve(name: str) -> Arm:
    try:
        return ALL_ARMS[name]
    except KeyError:
        known = ", ".join(sorted(ALL_ARMS)) or "(none registered)"
        raise ValueError(f"unknown arm {name!r}; known arms: {known}") from None


def check_availability(names: list[str]) -> tuple[list[str], list[str]]:
    """Split requested arms into (runnable, skipped-with-reason)."""
    runnable, skipped = [], []
    for name in names:
        arm = resolve(name)
        ok, reason = arm.available()
        (runnable if ok else skipped).append(name if ok else reason)
    return runnable, skipped


def run_arm_hook(
    command: str | None,
    cwd: Path,
    timeout: int = 300,
    env_overlay: dict[str, str] | None = None,
) -> tuple[int, str]:
    """Run an arm's setup/teardown shell.

    `env_overlay` is how a subject holds unrelated tools inert during its own
    setup. It is passed in rather than hardcoded, because a core that knows the
    name of any particular tool has taken a side.
    """
    if not command:
        return 0, ""
    import os

    env = dict(os.environ, **(env_overlay or {}))
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, (proc.stdout + proc.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        return 124, f"arm setup timed out after {timeout}s"
