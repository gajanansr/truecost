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

from truecost import __version__, corpus, manifest
from truecost.core.runner import register_arms, register_inert_env

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBJECTS_DIR = REPO_ROOT / "subjects"
RESULTS_DIR = REPO_ROOT / "results"


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
    if not ok:
        sys.exit(f"cannot run: {why}")

    register_arms(subject.arms)
    register_inert_env(subject.inert_env)

    runnable, skipped = subject.arms, []
    for note in skipped:
        print(f"skipped: {note}")

    print(f"auditing {subject.display} on the {args.axis} corpus")
    print(f"  claim:   {subject.claim.display} ({subject.claim.headline})")
    print(f"  arms:    {', '.join(sorted(runnable))}")
    print("  pairing: " + "; ".join(f"{p.treatment} vs {p.control}" for p in subject.pairings))
    print(f"  replicates: {args.replicates}")

    if args.dry_run:
        print("\n--dry-run: nothing executed. Remove it to spend real tokens.")
        return 0

    print(
        "\nNot yet wired to run_matrix: Phase 1 ships the rig and the ContextMesh\n"
        "self-audit. See docs/ROADMAP.md. Use --dry-run to inspect the plan."
    )
    return 1


def _load_results(directory: Path) -> list[tuple[Path, dict]]:
    out = []
    for path in sorted(directory.glob("*.json")):
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
    print(f"truecost {__version__} — {len(results)} result file(s) in {args.results_dir.name}/\n")
    for path, _ in results:
        print(f"  {path.name}")
    print(
        "\nRendering rows requires Phase 1 completion (see docs/ROADMAP.md);\n"
        "raw data is published here regardless, which is the part that matters."
    )
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
    parser.add_argument("--subjects-dir", type=Path, default=SUBJECTS_DIR)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("subjects", help="list tools under audit").set_defaults(func=cmd_subjects)

    audit = sub.add_parser("audit", help="measure one subject")
    audit.add_argument("subject")
    audit.add_argument("--axis", choices=("claim", "neutral"), default="claim")
    audit.add_argument("--replicates", type=int, default=3)
    audit.add_argument("--dry-run", action="store_true", help="print the plan, spend nothing")
    audit.set_defaults(func=cmd_audit)

    rep = sub.add_parser("report", help="render the leaderboard")
    rep.add_argument("--json", action="store_true")
    rep.set_defaults(func=cmd_report)

    sub.add_parser("verify", help="check every published row is reproducible").set_defaults(
        func=cmd_verify
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
