"""Turn a measurement into a publishable row.

One rule governs this module: a row must never be more confident than the
evidence under it. Three things can go wrong, and each has a distinct status
because collapsing them is how bad numbers get published.

- `INVALID` — the measurement did not happen. Delivery verification failed, or
  a control arm was receiving the treatment. This is not a result about the
  tool; it is a result about the run, and it is printed rather than discarded.
  Nine results were rejected this way before they became claims, including an
  88% "win" that was entirely cache ordering.
- `UNVERIFIED` — the run happened, but the treatment's arrival could not be
  confirmed. A tool that compresses inside a proxy may leave no
  transcript-visible evidence at all. The number is real and weaker, and saying
  so is the difference between an audit and a press release.
- `VERIFIED` — delivery confirmed on the treatment arm and confirmed absent on
  the control.

`NO EFFECT` is a first-class outcome, not a failure to find one. A 95% interval
spanning zero means the tool did not measurably change cost on these tasks, and
that is a finding worth publishing.
"""

from __future__ import annotations

from dataclasses import dataclass

from truecost.core.report import Comparison
from truecost.manifest import Claim, Pairing, Subject

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
INVALID = "INVALID"


@dataclass(frozen=True)
class Row:
    """One published line: what was claimed, what was measured, how much to trust it."""

    subject: str
    label: str
    claim: Claim
    comparison: Comparison
    status: str
    # Present when the tool's own accounting differs from ours, e.g. a delegate
    # whose tokens the published claim never counted. This gap is the finding.
    their_accounting_pct: float | None = None
    reason: str = ""

    @property
    def measured(self) -> str:
        if self.status == INVALID:
            return "—"
        if not self.comparison.significant:
            return "no effect"
        pct = self.comparison.percent_change
        return f"{pct:+.1f}%" if pct is not None else "—"

    @property
    def interval(self) -> str:
        if self.status == INVALID or self.comparison.pairs < 2:
            return ""
        base = self.comparison.baseline_mean
        if not base:
            return ""
        lo = 100.0 * self.comparison.ci_low / base
        hi = 100.0 * self.comparison.ci_high / base
        return f"[{min(lo, hi):+.1f}, {max(lo, hi):+.1f}]"

    @property
    def holds_up(self) -> bool | None:
        """Did the published claim survive? None when we cannot say."""
        if self.status == INVALID or not self.comparison.significant:
            return None if self.status == INVALID else False
        pct = self.comparison.percent_change
        return None if pct is None else self.claim.covers(pct)


def build(
    subject: Subject,
    pairing: Pairing,
    comparison: Comparison,
    delivery_ok: bool,
    control_clean: bool,
    their_accounting_pct: float | None = None,
    reason: str = "",
) -> Row:
    """Assemble one row, choosing the weakest status the evidence supports."""
    treatment = subject.arms[pairing.treatment]

    if not control_clean:
        status, why = INVALID, reason or "control arm received the treatment"
    elif not treatment.verifiable:
        status, why = (
            UNVERIFIED,
            reason or (f"{treatment.name}: effect is not observable in the transcript"),
        )
    elif not delivery_ok:
        status, why = INVALID, reason or "treatment was never delivered to the model"
    else:
        status, why = VERIFIED, reason

    return Row(
        subject=subject.display,
        label=pairing.label,
        claim=subject.claim,
        comparison=comparison,
        status=status,
        their_accounting_pct=their_accounting_pct,
        reason=why,
    )


def render(rows: list[Row], width: int = 96) -> str:
    """The leaderboard, as published in the README."""
    if not rows:
        return "No rows. Run `truecost audit <subject>` first."

    head = f"{'SUBJECT':<16}{'CLAIMED':>14}{'MEASURED':>12}  {'95% CI':<20}{'N':>4}  STATUS"
    out = [head, "─" * width]

    for row in rows:
        n = row.comparison.pairs
        out.append(
            f"{row.subject:<16}{row.claim.display:>14}{row.measured:>12}  "
            f"{row.interval:<20}{n:>4}  {row.status}"
        )
        if row.their_accounting_pct is not None:
            note = f"their accounting ({row.claim.accounting})"
            out.append(f"{'':<16}{note:>14}{row.their_accounting_pct:>+11.1f}%")
        if row.reason:
            out.append(f"{'':<16}↳ {row.reason}")

    out.append("─" * width)
    survived = [r for r in rows if r.holds_up is True]
    failed = [r for r in rows if r.holds_up is False]
    unknown = [r for r in rows if r.holds_up is None]
    out.append(
        f"{len(survived)} claim(s) reproduced, {len(failed)} did not, "
        f"{len(unknown)} could not be assessed."
    )
    unverified = [r.subject for r in rows if r.status == UNVERIFIED]
    if unverified:
        out.append("Weaker evidence (delivery unverifiable): " + ", ".join(sorted(set(unverified))))
    return "\n".join(out)
