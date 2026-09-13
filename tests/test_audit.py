"""The audit pipeline, exercised end to end without spending anything.

The runner is injectable precisely so this file can exist. A project that
audits other people's numbers cannot leave the code that produces its own
numbers untested because running it costs money.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from truecost import audit, corpus, verdict
from truecost.core.runner import Matrix, Task
from truecost.manifest import Arm, Claim, Hook, Pairing, Subject


def _subject(**over) -> Subject:
    defaults = dict(
        name="fake",
        display="FakeTool",
        repo="https://example.invalid/fake",
        mechanism="injection",
        claim=Claim(
            headline="90% fewer tokens", source="s", accounting="token-count", value_pct=-90.0
        ),
        arms={
            "on": Arm(name="on", delivery_marker="FAKE"),
            "off": Arm(name="off", delivery_marker="FAKE", expects_marker=False),
        },
        pairings=(Pairing(treatment="on", control="off", label="FakeTool"),),
    )
    return Subject(**{**defaults, **over})


def _matrix(on_costs=(0.20, 0.21, 0.19), off_costs=(0.30, 0.31, 0.29)) -> Matrix:
    rows = []
    for rep, (on, off) in enumerate(zip(on_costs, off_costs, strict=True), start=1):
        for arm, cost in (("on", on), ("off", off)):
            rows.append(
                {
                    "task_id": "t1",
                    "arm": arm,
                    "replicate": rep,
                    "session_id": f"{arm}{rep}",
                    "verified": True,
                    "turns": 5,
                    "cost_usd": cost,
                    "cli_cost_usd": cost,
                    "billed_input_equivalent": 1000.0,
                    "duration_s": 1.0,
                }
            )
    return Matrix.from_json(json.dumps(rows))


class FakeCorpus:
    axis = "claim"
    requires = ()

    def build(self, workdir: Path, settings: Path):
        tasks = [
            Task(task_id="t1", prompt="p", verify="true", repo=workdir),
            Task(task_id="control", prompt="p", verify="true", repo=workdir),
        ]
        return corpus.Corpus(tasks=tasks, reset_command="true", root=workdir, axis="claim")


@pytest.fixture
def registered(monkeypatch):
    corpus.register("fake", FakeCorpus())
    yield
    corpus._REGISTRY.pop("fake:claim", None)


@pytest.fixture
def delivered(monkeypatch):
    """Treatment reaches the model; control does not."""
    monkeypatch.setattr(audit, "received_marker", lambda result, marker: result.arm == "on")


def _run(subject, tmp_path, matrix=None, **kw):
    return audit.run(
        subject,
        "claim",
        workdir=tmp_path / "work",
        results_dir=tmp_path / "results",
        run_matrix=lambda *a, **k: matrix or _matrix(),
        **kw,
    )


class TestPipeline:
    def test_produces_a_verified_row_with_a_measured_delta(self, registered, delivered, tmp_path):
        out = _run(_subject(), tmp_path)
        (row,) = out.rows
        assert row.status == verdict.VERIFIED
        assert row.measured == "-33.3%"  # 0.20 vs 0.30 mean
        assert row.claim.display == "-90.0%"
        assert row.holds_up is False  # a real saving, nowhere near 90%

    def test_writes_raw_data_that_verify_can_read(self, registered, delivered, tmp_path):
        out = _run(_subject(), tmp_path)
        raw = json.loads(out.results_path.read_text())
        assert isinstance(raw, list) and len(raw) == 6
        assert {r["arm"] for r in raw} == {"on", "off"}
        # Delivery must survive the file: transcripts do not outlive the machine.
        assert all("delivered" in r for r in raw)
        assert {r["delivered"] for r in raw if r["arm"] == "on"} == {True}

    def test_filename_carries_subject_and_axis(self, registered, delivered, tmp_path):
        out = _run(_subject(), tmp_path)
        assert audit.FILENAME.match(out.results_path.name)
        assert out.results_path.name.startswith("fake__claim__")

    def test_rows_rebuild_from_the_saved_file(self, registered, delivered, tmp_path):
        out = _run(_subject(), tmp_path)
        subject = _subject()
        (rebuilt,) = audit.load_rows(out.results_path, {"fake": subject})
        assert rebuilt.status == verdict.VERIFIED
        assert rebuilt.measured == out.rows[0].measured

    def test_inherited_files_are_not_rendered_as_verdicts(self, tmp_path):
        legacy = tmp_path / "shunt.json"
        legacy.write_text("[]")
        assert audit.load_rows(legacy, {}) == []


class TestRefusals:
    def test_unregistered_corpus_raises_before_spending(self, tmp_path):
        with pytest.raises(audit.AuditError, match="no claim corpus registered"):
            _run(_subject(), tmp_path)

    def test_missing_executable_names_the_arm_and_refuses(self, registered, tmp_path):
        subject = _subject(
            arms={
                "on": Arm(
                    name="on", requires=("definitely-not-installed",), delivery_marker="FAKE"
                ),
                "off": Arm(name="off", delivery_marker="FAKE", expects_marker=False),
            }
        )
        with pytest.raises(audit.AuditError, match="definitely-not-installed"):
            _run(subject, tmp_path)


class TestHonesty:
    def test_undelivered_treatment_is_invalid_not_a_null_result(
        self, registered, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(audit, "received_marker", lambda r, m: False)
        (row,) = _run(_subject(), tmp_path).rows
        assert row.status == verdict.INVALID
        assert row.measured == "—"

    def test_marker_in_the_control_is_invalid(self, registered, monkeypatch, tmp_path):
        """Treatment leaking into the baseline. It happened in 2 of 9 runs."""
        monkeypatch.setattr(audit, "received_marker", lambda r, m: True)
        (row,) = _run(_subject(), tmp_path).rows
        assert row.status == verdict.INVALID
        assert "control" in row.reason

    def test_unobservable_arm_is_unverified_never_verified(self, registered, tmp_path):
        subject = _subject(
            arms={
                "on": Arm(name="on"),  # no marker: a proxy tool
                "off": Arm(name="off", expects_marker=False),
            }
        )
        (row,) = _run(subject, tmp_path).rows
        assert row.status == verdict.UNVERIFIED

    def test_void_subject_publishes_invalid_with_its_reason(self, registered, delivered, tmp_path):
        subject = _subject(void_reason="control mode is broken upstream")
        (row,) = _run(subject, tmp_path).rows
        assert row.status == verdict.INVALID
        assert row.reason == "control mode is broken upstream"

    def test_no_significant_difference_reads_as_no_effect(self, registered, delivered, tmp_path):
        flat = _matrix(on_costs=(0.30, 0.28, 0.32), off_costs=(0.29, 0.31, 0.30))
        (row,) = _run(_subject(), tmp_path, matrix=flat).rows
        assert row.measured == "no effect"
        assert row.holds_up is False

    def test_single_replicate_cannot_produce_a_headline(self, registered, delivered, tmp_path):
        one = _matrix(on_costs=(0.20,), off_costs=(0.30,))
        out = _run(_subject(), tmp_path, matrix=one)
        assert not audit.comparison_is_publishable(out.rows[0].comparison)
        assert out.rows[0].interval == ""


class TestHookSettings:
    """A hook-based subject delivers its treatment through `claude --settings`.

    The audit passed that path to the CLI and never created the file. Every one
    of 52 runs died with "Settings file not found" -- 0 turns, $0.00, and the
    verdict correctly read INVALID rather than a confident null.
    """

    def test_settings_file_is_written_for_a_hook_subject(self, registered, delivered, tmp_path):
        subject = _subject(hook=Hook(command="my-hook", events=("UserPromptSubmit",)))
        out = _run(subject, tmp_path)
        settings = tmp_path / "work" / "settings.json"
        assert settings.exists(), "claude --settings was pointed at a file nothing wrote"
        body = json.loads(settings.read_text())
        # The hook is wrapped in a shim so invocations and output size are
        # recorded: "ran and emitted nothing" and "never ran" call for opposite
        # conclusions and are otherwise indistinguishable.
        registered = body["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        assert registered.endswith("hook-shim.sh")
        shim = tmp_path / "work" / "hook-shim.sh"
        assert shim.exists() and shim.stat().st_mode & 0o111
        assert "my-hook" in shim.read_text()
        assert out.rows

    def test_host_auto_memory_is_disabled(self, registered, delivered, tmp_path):
        """The host's own recall competes with the tool under test.

        Measured: 15 of 15 sessions in an earlier attempt carried a Claude Code
        AutoMem attachment in every arm, so the control was not memory-free.
        """
        subject = _subject(hook=Hook(command="my-hook", events=("UserPromptSubmit",)))
        _run(subject, tmp_path)
        body = json.loads((tmp_path / "work" / "settings.json").read_text())
        assert body["autoMemoryEnabled"] is False

    def test_every_declared_event_is_registered(self, registered, delivered, tmp_path):
        subject = _subject(hook=Hook(command="my-hook", events=("UserPromptSubmit", "SessionEnd")))
        _run(subject, tmp_path)
        body = json.loads((tmp_path / "work" / "settings.json").read_text())
        assert set(body["hooks"]) == {"UserPromptSubmit", "SessionEnd"}

    def test_subject_without_a_hook_writes_no_settings(self, registered, delivered, tmp_path):
        """A proxy-based tool needs no hook, and must not get an empty one."""
        _run(_subject(), tmp_path)
        assert not (tmp_path / "work" / "settings.json").exists()


class TestPartialSaves:
    """A long, billed run must not lose everything when it dies.

    The first real self-audit was killed by memory pressure at 45 of 52
    sessions. save() only ran at the end, so every one of those billed sessions
    produced nothing. Results are now persisted as they arrive.
    """

    def test_partial_file_survives_a_run_that_dies_midway(self, registered, delivered, tmp_path):
        results_dir = tmp_path / "results"

        def dying_runner(tasks, replicates=3, arms=None, model=None, on_result=None):
            for result in _matrix().results[:2]:
                on_result(result)
            raise KeyboardInterrupt("killed, as the real run was")

        with pytest.raises(KeyboardInterrupt):
            audit.run(
                _subject(),
                "claim",
                workdir=tmp_path / "work",
                results_dir=results_dir,
                run_matrix=dying_runner,
            )
        partial = results_dir / audit.partial_filename("fake", "claim")
        assert partial.exists(), "billed runs were lost"
        assert len(json.loads(partial.read_text())) == 2

    def test_partial_is_removed_once_the_run_finishes(self, registered, delivered, tmp_path):
        out = _run(_subject(), tmp_path)
        partial = tmp_path / "results" / audit.partial_filename("fake", "claim")
        assert out.results_path.exists()
        assert not partial.exists()
