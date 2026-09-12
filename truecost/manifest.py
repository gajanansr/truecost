"""Subject manifests: a tool under audit, declared as data.

Adding a subject must not require writing Python. If it did, the set of tools
this project is willing to measure would be limited by how much code someone
felt like writing, and the easiest tools to audit would be the ones whose
maintainers were least likely to object.

A manifest carries three things the core deliberately does not know:

- **The claim.** What the tool published, where, and — critically — what that
  number measures. `accounting = "parent-only"` is the difference between
  Portal's -90% and the -10.9% that showed up once the delegate was billed.
- **The arms.** Environment overlays, wrapper argv, settings files, and
  setup/teardown, plus whether each arm's treatment is observable at all.
- **The pairings.** Which control isolates which mechanism. A tool compared
  against the wrong baseline produces a number that is confidently wrong.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from truecost.core.arms import Arm
from truecost.core.runner import PreflightProbe

# What a published claim actually counted. The audit reports its own total
# alongside the tool's accounting, and the gap between them is often the
# entire finding.
ACCOUNTING = {
    "total": "all models billed",
    "parent-only": "primary model only; delegated work not counted",
    "token-count": "raw token count, cache classes not priced",
    "unstated": "the source does not say",
}

MECHANISMS = {"injection", "compression", "delegation", "retrieval", "other"}


@dataclass(frozen=True)
class Claim:
    """A published savings claim, as its author stated it."""

    headline: str
    source: str
    accounting: str = "unstated"
    quoted: str = ""
    # Single value, or a range when the claim is stated as one ("60-90%").
    # Negative means a cost reduction, matching the sign of a measured delta.
    value_pct: float | None = None
    range_pct: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.accounting not in ACCOUNTING:
            raise ValueError(
                f"unknown accounting {self.accounting!r}; "
                f"expected one of {', '.join(sorted(ACCOUNTING))}"
            )
        if self.value_pct is None and self.range_pct is None:
            raise ValueError(f"claim {self.headline!r} states no number to test")

    @property
    def display(self) -> str:
        if self.range_pct is not None:
            lo, hi = self.range_pct
            return f"{lo:+.0f}..{hi:+.0f}%"
        return f"{self.value_pct:+.1f}%"

    def covers(self, measured_pct: float) -> bool:
        """Does the measured result fall inside what was claimed?"""
        if self.range_pct is not None:
            lo, hi = self.range_pct
            return min(lo, hi) <= measured_pct <= max(lo, hi)
        assert self.value_pct is not None
        return abs(measured_pct - self.value_pct) <= abs(self.value_pct) * 0.1


@dataclass(frozen=True)
class Hook:
    """How a subject's treatment reaches the model.

    A hook-based tool is delivered through `claude --settings`, which *adds*
    hooks for one invocation without touching the user's global configuration.
    The audit generates that settings file; declaring the command here rather
    than hardcoding it keeps the core free of any particular tool's name.

    `command` must be on PATH. Omit the whole section for a subject that needs
    no hook -- a proxy-based tool must not be handed an empty one.
    """

    command: str
    events: tuple[str, ...] = ("UserPromptSubmit",)

    def settings(self) -> dict:
        return {
            "hooks": {
                event: [{"matcher": "*", "hooks": [{"type": "command", "command": self.command}]}]
                for event in self.events
            }
        }


@dataclass(frozen=True)
class Pairing:
    """One comparison: a treatment against the control that isolates it."""

    treatment: str
    control: str
    label: str
    rationale: str = ""


@dataclass(frozen=True)
class Subject:
    """A tool under audit."""

    name: str
    display: str
    repo: str
    mechanism: str
    claim: Claim
    arms: dict[str, Arm]
    pairings: tuple[Pairing, ...]
    # Environment that makes this subject inert, so other subjects' setup and
    # verify commands never trip it.
    inert_env: dict[str, str] = field(default_factory=dict)
    preflight: PreflightProbe | None = None
    # How the treatment is delivered, when it is delivered by a hook.
    hook: Hook | None = None
    # Set when a prior published run was withdrawn, with the reason. Printed on
    # every report: a void result that quietly disappears is a retracted claim.
    void_reason: str = ""
    notes: str = ""

    @property
    def bills_second_model(self) -> bool:
        """Delegation moves work to another model, so both sides need billing."""
        return self.mechanism == "delegation"

    def unverifiable_arms(self) -> list[str]:
        return sorted(n for n, a in self.arms.items() if not a.verifiable)


def _arm_from_toml(raw: dict) -> Arm:
    return Arm(
        name=raw["name"],
        env=raw.get("env", {}),
        command_prefix=tuple(raw.get("command_prefix", ())),
        settings=Path(raw["settings"]) if raw.get("settings") else None,
        extra_args=tuple(raw.get("extra_args", ())),
        setup=raw.get("setup"),
        teardown=raw.get("teardown"),
        requires=tuple(raw.get("requires", ())),
        delivery_marker=raw.get("delivery_marker"),
        expects_marker=raw.get("expects_marker", True),
        notes=raw.get("notes", ""),
    )


def load(path: Path) -> Subject:
    """Parse one `subjects/*.toml`."""
    raw = tomllib.loads(path.read_text())
    meta, claim_raw = raw["subject"], raw["claim"]

    mechanism = meta.get("mechanism", "other")
    if mechanism not in MECHANISMS:
        raise ValueError(
            f"{path.name}: unknown mechanism {mechanism!r}; "
            f"expected one of {', '.join(sorted(MECHANISMS))}"
        )

    rng = claim_raw.get("range_pct")
    claim = Claim(
        headline=claim_raw["headline"],
        source=claim_raw["source"],
        accounting=claim_raw.get("accounting", "unstated"),
        quoted=claim_raw.get("quoted", ""),
        value_pct=claim_raw.get("value_pct"),
        range_pct=(float(rng[0]), float(rng[1])) if rng else None,
    )

    arms = {a["name"]: _arm_from_toml(a) for a in raw.get("arm", [])}
    pairings = tuple(
        Pairing(
            treatment=p["treatment"],
            control=p["control"],
            label=p["label"],
            rationale=p.get("rationale", ""),
        )
        for p in raw.get("pairing", [])
    )

    for p in pairings:
        for side in (p.treatment, p.control):
            if side not in arms:
                raise ValueError(f"{path.name}: pairing {p.label!r} names unknown arm {side!r}")

    hook_raw = raw.get("hook")
    hook = (
        Hook(
            command=hook_raw["command"],
            events=tuple(hook_raw.get("events", ("UserPromptSubmit",))),
        )
        if hook_raw
        else None
    )

    pre = raw.get("preflight")
    probe = (
        PreflightProbe(
            binary=pre["binary"],
            silencing_vars=tuple(pre.get("silencing_vars", ())),
            event=pre.get("event", "UserPromptSubmit"),
        )
        if pre
        else None
    )

    return Subject(
        name=meta["name"],
        display=meta.get("display", meta["name"]),
        repo=meta["repo"],
        mechanism=mechanism,
        claim=claim,
        arms=arms,
        pairings=pairings,
        inert_env=raw.get("inert_env", {}),
        preflight=probe,
        hook=hook,
        void_reason=meta.get("void_reason", ""),
        notes=meta.get("notes", ""),
    )


def load_all(directory: Path) -> dict[str, Subject]:
    """Load every manifest in `subjects/`, sorted by name."""
    subjects = {}
    for path in sorted(directory.glob("*.toml")):
        subject = load(path)
        if subject.name in subjects:
            raise ValueError(f"duplicate subject name {subject.name!r} in {path.name}")
        subjects[subject.name] = subject
    return subjects
