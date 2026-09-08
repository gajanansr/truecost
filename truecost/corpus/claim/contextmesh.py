"""ContextMesh's own benchmark, reproduced.

The self-audit. This is the corpus ContextMesh used to measure itself, run
unchanged, so the first row on the leaderboard is graded by exactly the tasks
its author chose. Anything harsher applied to another subject would be a double
standard; anything softer would make the self-audit worthless.

Four tasks, three of which memory could plausibly help and one it cannot:

- `convention` -- needs a recalled DECISION (settings live in settings.py)
- `deadend`    -- needs a recalled UNRESOLVED_ISSUE (the circular import)
- `backoff`    -- needs a recalled SOLUTION (retries back off exponentially)
- `control`    -- unrelated to anything in memory; the falsification check

The control is the reason this corpus can be trusted. It returned a 0.00 turn
change, which is what a corpus written to flatter its subject cannot do.

Verification greps for the *shape* of the answer, not merely the name. An agent
can write a function called `retry_with_backoff` that retries immediately;
backing off exponentially is the part memory would have supplied, so that is
what the check requires.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from truecost.core.runner import Task
from truecost.corpus import Corpus, register

SOURCE = "https://github.com/gajananrathod/ContextMesh#session-memory--works-conditionally"

FIXTURE_FILES: dict[str, str] = {
    "settings.py": "TIMEOUT_SECONDS = 30\nMAX_CONNECTIONS = 10\n",
    "utils/__init__.py": "",
    "utils/net.py": (
        "import urllib.request\n\n\n"
        "def fetch(url):\n"
        "    return urllib.request.urlopen(url).read()\n"
    ),
    "README.md": "# fixture project\n\nA small project used by the ContextMesh benchmark.\n",
}

# Prior-session memory the agent is expected to recall. Seeded rather than
# accumulated, because "curated, relevant memory" is the condition under which
# ContextMesh claimed a win -- and the condition it must be graded on.
SEED_NODES = [
    {
        "node_type": "DECISION",
        "content": (
            "Decided all tunable settings live in settings.py at the repo root. "
            "Do not create config.py; it was tried and removed."
        ),
        "files": ["settings.py"],
        "importance": 0.9,
    },
    {
        "node_type": "UNRESOLVED_ISSUE",
        "content": (
            "Importing settings at module scope in utils/net.py causes a "
            "circular import. Import it inside the function instead."
        ),
        "files": ["utils/net.py", "settings.py"],
        "importance": 0.9,
    },
    {
        "node_type": "SOLUTION",
        "content": (
            "Retries must back off exponentially (2 ** attempt). A fixed-delay "
            "retry loop was rejected in review for hammering the upstream."
        ),
        "files": ["utils/net.py"],
        "importance": 0.9,
    },
]


@dataclass(frozen=True)
class Fixture:
    root: Path
    seed_db: Path


def _git_init(root: Path) -> None:
    def run(*a: str) -> None:
        subprocess.run(a, cwd=root, capture_output=True, check=True)

    run("git", "init", "-q")
    run("git", "config", "user.email", "audit@truecost.local")
    run("git", "config", "user.name", "truecost")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "fixture baseline")


def _build_fixture(workdir: Path) -> Fixture:
    """Create the fixture repo and a database pre-seeded with prior memory."""
    # Imported here, not at module scope: a missing subject library must skip
    # one corpus with a clear message, not break the CLI for every subject.
    from contextmesh.memory.store import connect, ensure_session
    from contextmesh.store.schema import CREATE_SCHEMA_SQL

    root = (workdir / "project").resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for rel, body in FIXTURE_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)

    # The between-replicate reset is `git checkout && git clean`, which needs a
    # real repo. Without one, files an earlier replicate created survive and
    # the next replicate verifies without the agent doing anything.
    _git_init(root)

    seed_db = (workdir / "seed.db").resolve()
    seed_db.unlink(missing_ok=True)

    con = connect(seed_db)
    try:
        con.executescript(CREATE_SCHEMA_SQL)
        ensure_session(con, "seed-session", str(root))
        for index, node in enumerate(SEED_NODES):
            con.execute(
                "INSERT INTO nodes (node_id, session_id, node_type, content,"
                " files_involved, symbols, confidence, importance, tier,"
                " token_count, created_at, metadata)"
                " VALUES (?, ?, ?, ?, ?, '[]', 1.0, ?, 'warm', 0,"
                " '2026-08-01T00:00:00+00:00', '{}')",
                (
                    f"seed_{index}",
                    "seed-session",
                    node["node_type"],
                    node["content"],
                    json.dumps(node["files"]),
                    node["importance"],
                ),
            )
        con.commit()
    finally:
        con.close()

    return Fixture(root=root, seed_db=seed_db)


def _reset_command(fixture: Fixture, data_dir: Path) -> str:
    """Shell restoring repo and memory to the seeded state before each run."""
    return (
        f"rm -rf {data_dir} && mkdir -p {data_dir} && "
        f"cp {fixture.seed_db} {data_dir}/contextmesh.db && "
        f"git -C {fixture.root} checkout -- . && "
        f"git -C {fixture.root} clean -fdq"
    )


class ContextMeshClaim:
    axis = "claim"
    requires = ("contextmesh",)

    def build(self, workdir: Path, settings: Path) -> Corpus:
        fixture = _build_fixture(workdir)
        data_dir = (workdir / "data").resolve()
        reset = _reset_command(fixture, data_dir)

        common = dict(
            repo=fixture.root,
            settings=settings,
            env={"CONTEXTMESH_DATA_DIR": str(data_dir)},
            setup=reset,
            timeout_s=600,
        )

        tasks = [
            Task(
                task_id="convention",
                prompt=(
                    "Add a tunable for how many times a failed request should be "
                    "retried, defaulting to 3. Follow this project's existing "
                    "conventions. Then reply DONE."
                ),
                verify=("test ! -f config.py && grep -qE '^[A-Z_]*RETR[A-Z_]* *= *3' settings.py"),
                **common,
            ),
            Task(
                task_id="deadend",
                prompt=(
                    "In utils/net.py, add a function `fetch_with_retries(url)` that "
                    "uses the retry count from the settings module. Then reply DONE."
                ),
                verify=(
                    "grep -q 'def fetch_with_retries' utils/net.py && "
                    "! grep -qE '^(from settings|import settings)' utils/net.py"
                ),
                **common,
            ),
            Task(
                task_id="backoff",
                prompt=(
                    "Add a `retry_with_backoff(fn, max_attempts=3)` helper to "
                    "utils/net.py that retries `fn` on failure, following how this "
                    "project has decided retries should behave. Then reply DONE."
                ),
                verify=(
                    "grep -q 'def retry_with_backoff' utils/net.py && "
                    r"grep -qE '(2\s*\*\*|\*\*\s*2|pow\(2)' utils/net.py"
                ),
                **common,
            ),
            Task(
                task_id="control",
                prompt=(
                    "Create a file CHANGELOG.md containing a single line: "
                    "'## 0.1.0 - initial release'. Then reply DONE."
                ),
                verify="grep -q '0.1.0' CHANGELOG.md",
                **common,
            ),
        ]

        return Corpus(
            tasks=tasks,
            reset_command=reset,
            root=fixture.root,
            axis="claim",
            source=SOURCE,
        )


register("contextmesh", ContextMeshClaim())
