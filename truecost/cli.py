"""truecost — audit a token-savings claim against what it actually bills.

Four commands:

    truecost subjects              what is under audit, and what each claims
    truecost audit <subject>       run the measurement
    truecost report                the leaderboard
    truecost verify                every published row has its raw data

`verify` exists because the project's central promise is that any row can be
reproduced from this repository alone. A promise nothing checks is a slogan, so
CI runs it on every push.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from truecost import __version__, audit, corpus, manifest, verdict

# The audit's data — subjects and published results — lives in the repository,
# not in the installed package. `pipx install truecost` gives you the CLI; the
# rows it audits come from a clone. So the data root is discovered from the
# working directory rather than from the package's own location, which resolves
# to site-packages once installed and finds nothing.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def find_data_root(start: Path | None = None) -> Path | None:
    """Nearest ancestor of `start` holding a subjects/ directory."""
    base = (start or Path.cwd()).resolve()
    for candidate in (base, *base.parents):
        if (candidate / "subjects").is_dir():
            return candidate
    # Editable install or a checkout invoked from elsewhere.
    if (PACKAGE_ROOT / "subjects").is_dir():
        return PACKAGE_ROOT
    return None


def _resolve_dir(explicit: Path | None, name: str) -> Path:
    if explicit is not None:
        return explicit
    root = find_data_root()
    if root is None:
        sys.exit(
            f"no {name}/ directory found here or in any parent.\n"
            "truecost audits the data in its repository, so run it from a clone:\n"
            "  git clone https://github.com/gajanansr/truecost && cd truecost\n"
            f"or point at one explicitly with --{name}-dir."
        )
    return root / name


def _load_subjects(directory: Path) -> dict[str, manifest.Subject]:
    if not directory.is_dir():
        sys.exit(f"no subjects directory at {directory}")
    return manifest.load_all(directory)


def cmd_subjects(args: argparse.Namespace) -> int:
    subjects = _load_subjects(args.subjects_dir)
    if not subjects:
        print("No subjects declared. Add a TOML file to subjects/.")
        return 0

    corpus.load_builtin()
    for name, s in subjects.items():
        print(f"{s.display}  ({s.mechanism})")
        print(f"  claims    {s.claim.display} — {s.claim.headline}")
        print(f"  measures  {manifest.ACCOUNTING[s.claim.accounting]}")
        print(f"  source    {s.claim.source}")
        for axis in ("claim", "neutral"):
            ok, why = corpus.available(name, axis)
            print(f"  {axis:<9} {'ready' if ok else why}")
        unverifiable = s.unverifiable_arms()
        if unverifiable:
            print(f"  note      delivery unverifiable for: {', '.join(unverifiable)}")
        if s.void_reason:
            print(f"  VOID      {s.void_reason}")
        print()
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    subjects = _load_subjects(args.subjects_dir)
    subject = subjects.get(args.subject)
    if subject is None:
        sys.exit(f"unknown subject {args.subject!r}; known: {', '.join(sorted(subjects))}")

    corpus.load_builtin()
    ok, why = corpus.available(subject.name, args.axis)

    print(f"auditing {subject.display} on the {args.axis} corpus")
    print(f"  claim:      {subject.claim.display} ({subject.claim.headline})")
    print(f"  measures:   {manifest.ACCOUNTING[subject.claim.accounting]}")
    print(f"  arms:       {', '.join(sorted(subject.arms))}")
    for pairing in subject.pairings:
        print(f"  pairing:    {pairing.treatment} vs {pairing.control} — {pairing.label}")
        if pairing.rationale:
            print(f"              {pairing.rationale}")
    print(f"  replicates: {args.replicates}")
    print(f"  corpus:     {'ready' if ok else why}")
    if subject.void_reason:
        print(f"  VOID:       {subject.void_reason}")

    # The plan prints either way: a dry run exists to be inspected, and an
    # unavailable corpus is part of what you want to see.
    if args.dry_run:
        print("\n--dry-run: nothing executed. Remove it to spend real tokens.")
        return 0
    if not ok:
        sys.exit(f"cannot run: {why}")

    data_root = args.subjects_dir.parent
    workdir = args.workdir or (data_root / ".audit-work" / f"{subject.name}-{args.axis}")
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"\nworkdir: {workdir}\nthis spends real tokens; every replicate is a billed session\n")

    def progress(result) -> None:
        state = "ok" if result.verified else ("ERROR" if result.cli_error else "unverified")
        # flush: an audit runs for an hour or more, and stdout is block-buffered
        # whenever it is not a terminal. Without this, `truecost audit > log`
        # shows nothing at all until the run ends -- so a run failing on its
        # first session looks identical to one working perfectly.
        print(
            f"  {result.task_id:<12} {result.arm:<20} r{result.replicate}  "
            f"{result.turns:>3} turns  ${result.cost_usd:.4f}  {state}",
            flush=True,
        )

    try:
        outcome = audit.run(
            subject,
            args.axis,
            workdir=workdir,
            results_dir=args.results_dir,
            replicates=args.replicates,
            model=args.model,
            on_result=progress,
        )
    except audit.AuditError as exc:
        sys.exit(f"cannot run: {exc}")

    for note in outcome.skipped:
        print(f"skipped: {note}")
    print("\n" + verdict.render(outcome.rows))
    print(f"\nraw data: {outcome.results_path}")
    return 0


def _load_results(directory: Path) -> list[tuple[Path, dict]]:
    """Published results only.

    pathlib's glob matches dotfiles, unlike a shell glob, so an in-flight
    `.<subject>__<axis>.partial.json` would otherwise be read back as a finished
    measurement -- and `verify` would accept it, since a partial has the same
    shape as a complete one.
    """
    out = []
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("."):
            continue
        try:
            out.append((path, json.loads(path.read_text())))
        except json.JSONDecodeError as exc:
            print(f"unreadable: {path.name}: {exc}", file=sys.stderr)
    return out


def cmd_report(args: argparse.Namespace) -> int:
    results = _load_results(args.results_dir)
    if not results:
        print("No results yet. Run `truecost audit <subject>`.")
        return 0
    if args.json:
        print(json.dumps({p.name: r for p, r in results}, indent=2))
        return 0

    subjects = _load_subjects(args.subjects_dir)
    rows, legacy = [], []
    for path, _ in results:
        found = audit.load_rows(path, subjects)
        (rows.extend(found) if found else legacy.append(path.name))

    print(verdict.render(rows) if rows else "No rows rendered yet.")
    if legacy:
        # Raw data from before this CLI existed. Republished as data, not
        # re-rendered as verdicts -- a number is only as good as the run that
        # produced it, and these predate delivery being recorded per row.
        print(
            f"\n{len(legacy)} inherited result file(s) not rendered as rows "
            "(pre-CLI raw data; see docs/ROADMAP.md):"
        )
        for name in legacy:
            print(f"  {name}")
    return 0


# Fields without which a published row cannot be traced back to the runs that
# produced it. `verified` is here because a run that gave up early looks cheap,
# and a cost with no success flag beside it is not a result.
REQUIRED_RUN_FIELDS = ("arm", "task_id", "replicate", "cost_usd", "turns", "verified")


def _check_result_file(path: Path, data: object) -> list[str]:
    """A result file must be a list of run records, each independently traceable."""
    if not isinstance(data, list):
        return [f"{path.name}: expected a list of run records, got {type(data).__name__}"]
    if not data:
        return [f"{path.name}: no runs"]

    problems = []
    for index, run in enumerate(data):
        if not isinstance(run, dict):
            problems.append(f"{path.name}[{index}]: run is not an object")
            continue
        missing = [f for f in REQUIRED_RUN_FIELDS if f not in run]
        if missing:
            problems.append(f"{path.name}[{index}]: missing {', '.join(missing)}")
    # Arms are what a pairing compares. One arm cannot be paired against itself.
    arms = {r.get("arm") for r in data if isinstance(r, dict)}
    if len(arms) < 2:
        problems.append(
            f"{path.name}: only arm(s) {sorted(a for a in arms if a)} present; "
            "a paired comparison needs at least two"
        )
    return problems


def cmd_verify(args: argparse.Namespace) -> int:
    """Integrity gate. Run in CI on every push."""
    problems: list[str] = []

    subjects = _load_subjects(args.subjects_dir)
    corpus.load_builtin()

    for name, s in subjects.items():
        for p in s.pairings:
            for side in (p.treatment, p.control):
                if side not in s.arms:
                    problems.append(f"{name}: pairing {p.label!r} names unknown arm {side!r}")
        # A control that expects its own marker present is not a control.
        for p in s.pairings:
            control = s.arms.get(p.control)
            if control is not None and control.verifiable and control.expects_marker:
                problems.append(
                    f"{name}: control arm {p.control!r} expects its delivery marker to be "
                    "present; a control must assert absence or treatment leakage goes undetected"
                )
        if s.claim.accounting == "unstated" and not s.claim.quoted:
            problems.append(
                f"{name}: claim accounting is 'unstated' and no quote is recorded. "
                "Quote the source so readers can judge what the number counted."
            )

    for path, data in _load_results(args.results_dir):
        problems.extend(_check_result_file(path, data))

    if problems:
        print(f"{len(problems)} integrity problem(s):\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"OK: {len(subjects)} subject(s), {len(_load_results(args.results_dir))} result file(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="truecost", description=__doc__.split("\n")[0])
    parser.add_argument("--version", action="version", version=f"truecost {__version__}")
    parser.add_argument("--subjects-dir", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("subjects", help="list tools under audit").set_defaults(func=cmd_subjects)

    audit_p = sub.add_parser("audit", help="measure one subject")
    audit_p.add_argument("subject")
    audit_p.add_argument("--axis", choices=("claim", "neutral"), default="claim")
    audit_p.add_argument("--replicates", type=int, default=3)
    audit_p.add_argument("--model", default=None, help="override the model under test")
    audit_p.add_argument("--workdir", type=Path, default=None, help="where fixtures are built")
    audit_p.add_argument("--dry-run", action="store_true", help="print the plan, spend nothing")
    audit_p.set_defaults(func=cmd_audit)

    rep = sub.add_parser("report", help="render the leaderboard")
    rep.add_argument("--json", action="store_true")
    rep.set_defaults(func=cmd_report)

    sub.add_parser("verify", help="check every published row is reproducible").set_defaults(
        func=cmd_verify
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.subjects_dir = _resolve_dir(args.subjects_dir, "subjects")
    args.results_dir = _resolve_dir(args.results_dir, "results")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
