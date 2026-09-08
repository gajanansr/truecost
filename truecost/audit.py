"""Run one subject's audit end to end.

The orchestration the CLI is too thin to hold: build the corpus, register the
subject's arms, run the matrix, check delivery, and turn each pairing into a
row.

Two decisions here are load-bearing.

**The runner is injectable.** `run` takes the function that executes the
matrix, so the whole pipeline can be tested without spending a cent. A test
suite that cannot exercise the code which produces published numbers is the
same gap this project audits other people for.

**Delivery is persisted per run.** Whether a treatment reached the model is
determined from the session transcript, and transcripts do not survive the
machine that produced them. If the verdict could not be rebuilt from the saved
rows, every republished row would silently downgrade to UNVERIFIED. So each
saved row carries its own `delivered` flag.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from truecost import corpus as corpus_mod
from truecost import verdict
from truecost.core.report import Comparison, compare, received_marker
from truecost.core.runner import Matrix, preflight_arms, register_arms, register_inert_env
from truecost.core.runner import run_matrix as _default_run_matrix
from truecost.manifest import Pairing, Subject
from truecost.verdict import Row

# results/<subject>__<axis>__<YYYY-MM-DD>.json
FILENAME = re.compile(
    r"^(?P<subject>[^_]+)__(?P<axis>claim|neutral)__(?P<date>\d{4}-\d{2}-\d{2})\.json$"
)


class AuditError(RuntimeError):
    """The audit cannot run. Raised before anything is executed or billed."""


@dataclass(frozen=True)
class AuditResult:
    subject: Subject
    axis: str
    rows: list[Row]
    matrix: Matrix
    results_path: Path | None = None
    skipped: tuple[str, ...] = ()


def _delivered(result, marker: str | None) -> bool | None:
    """Did this run's treatment reach the model? None when unobservable."""
    if marker is None:
        return None
    return received_marker(result, marker)


def _pairing_delivery(
    subject: Subject,
    pairing: Pairing,
    delivery: dict[tuple[str, str, int], bool | None],
) -> tuple[bool, bool]:
    """(treatment delivered, control clean) for one pairing.

    A control is "clean" when its marker is *absent*. That direction is the one
    that catches treatment leaking into a baseline, which happened in 2 of 9
    runs before this check existed.
    """
    treatment_arm = subject.arms[pairing.treatment]
    if not treatment_arm.verifiable:
        return True, True  # nothing to check; the row will read UNVERIFIED

    def flags(arm: str) -> list[bool]:
        return [v for (_task, a, _rep), v in delivery.items() if a == arm and v is not None]

    treatment_flags = flags(pairing.treatment)
    control_flags = flags(pairing.control)
    delivered = bool(treatment_flags) and all(treatment_flags)
    control_clean = not any(control_flags)
    return delivered, control_clean


def _rows_for(
    subject: Subject,
    matrix: Matrix,
    delivery: dict[tuple[str, str, int], bool | None],
    metric: str = "cost_usd",
) -> list[Row]:
    rows = []
    for pairing in subject.pairings:
        comparison = compare(
            matrix, metric=metric, baseline=pairing.control, treatment=pairing.treatment
        )
        delivered, control_clean = _pairing_delivery(subject, pairing, delivery)
        # A subject with a known-broken control publishes INVALID with its
        # reason rather than a number. Deleting the row instead would be a
        # retraction nobody sees.
        reason = subject.void_reason
        if reason:
            control_clean = False
        rows.append(
            verdict.build(
                subject,
                pairing,
                comparison,
                delivery_ok=delivered,
                control_clean=control_clean,
                reason=reason,
            )
        )
    return rows


def results_filename(subject: str, axis: str, on: date | None = None) -> str:
    return f"{subject}__{axis}__{(on or date.today()).isoformat()}.json"


def save(matrix: Matrix, delivery: dict, path: Path) -> Path:
    """Write run rows, each carrying whether its treatment was delivered.

    Rows stay a flat list so `truecost verify` reads audits and the inherited
    ContextMesh results with the same code path.
    """
    import json

    rows = []
    for result in matrix.results:
        row = result.row()
        row["delivered"] = delivery.get((result.task_id, result.arm, result.replicate))
        rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n")
    return path


def run(
    subject: Subject,
    axis: str,
    workdir: Path,
    results_dir: Path,
    replicates: int = 3,
    model: str | None = None,
    settings: Path | None = None,
    run_matrix=_default_run_matrix,
    on_result=None,
) -> AuditResult:
    """Measure one subject. Raises AuditError before spending anything."""
    corpus_mod.load_builtin()
    ok, why = corpus_mod.available(subject.name, axis)
    if not ok:
        raise AuditError(why)

    register_arms(subject.arms)
    register_inert_env(subject.inert_env)

    # An arm whose executable is absent is skipped and named, never silently
    # dropped -- a missing tool that looks like a null result is the failure
    # mode this project exists to catch.
    runnable, skipped = [], []
    for name, arm in subject.arms.items():
        available, reason = arm.available()
        (runnable if available else skipped).append(name if available else reason)

    for pairing in subject.pairings:
        for side in (pairing.treatment, pairing.control):
            if side not in runnable:
                raise AuditError(
                    f"pairing {pairing.label!r} needs arm {side!r}, which is unavailable: "
                    + "; ".join(skipped)
                )

    problems = preflight_arms(subject.preflight, cwd=workdir)
    if problems:
        raise AuditError("; ".join(problems))

    builder = corpus_mod.get(subject.name, axis)
    assert builder is not None  # availability was checked above
    built = builder.build(workdir, settings or workdir / "settings.json")

    matrix = run_matrix(
        built.tasks, replicates=replicates, arms=runnable, model=model, on_result=on_result
    )

    delivery: dict[tuple[str, str, int], bool | None] = {}
    for result in matrix.results:
        marker = subject.arms[result.arm].delivery_marker
        delivery[(result.task_id, result.arm, result.replicate)] = _delivered(result, marker)

    path = save(matrix, delivery, results_dir / results_filename(subject.name, axis))
    return AuditResult(
        subject=subject,
        axis=axis,
        rows=_rows_for(subject, matrix, delivery),
        matrix=matrix,
        results_path=path,
        skipped=tuple(skipped),
    )


def load_rows(path: Path, subjects: dict[str, Subject]) -> list[Row]:
    """Rebuild published rows from a saved audit.

    Returns [] for a file that does not follow the audit naming convention --
    the inherited ContextMesh results are raw data from before this CLI existed
    and are republished as data, not re-rendered as verdicts.
    """
    import json

    match = FILENAME.match(path.name)
    if match is None:
        return []
    subject = subjects.get(match["subject"])
    if subject is None:
        return []

    raw = json.loads(path.read_text())
    matrix = Matrix.from_json(json.dumps(raw))
    delivery = {
        (r["task_id"], r["arm"], r["replicate"]): r.get("delivered")
        for r in raw
        if isinstance(r, dict)
    }
    return _rows_for(subject, matrix, delivery)


def comparison_is_publishable(c: Comparison) -> bool:
    """A single run can never produce a headline."""
    return c.pairs >= 2
