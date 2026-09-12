"""The integrity gate. CI runs this on every push, so it must actually bite."""

from __future__ import annotations

from pathlib import Path

import pytest

from truecost import cli

RESULTS = Path(__file__).resolve().parent.parent / "results"
SUBJECTS = Path(__file__).resolve().parent.parent / "subjects"


def test_shipped_results_and_subjects_pass_verify():
    assert cli.main(["--results-dir", str(RESULTS), "--subjects-dir", str(SUBJECTS), "verify"]) == 0


def test_run_missing_required_fields_is_rejected():
    problems = cli._check_result_file(
        Path("x.json"), [{"arm": "on", "task_id": "t", "replicate": 1}]
    )
    assert any("missing cost_usd, turns, verified" in p for p in problems)


def test_single_arm_file_is_rejected():
    """A file with one arm cannot support a paired comparison."""
    run = {
        "arm": "on",
        "task_id": "t",
        "replicate": 1,
        "cost_usd": 1.0,
        "turns": 2,
        "verified": True,
    }
    problems = cli._check_result_file(Path("x.json"), [run])
    assert any("needs at least two" in p for p in problems)


def test_two_arms_with_all_fields_passes():
    runs = [
        {"arm": a, "task_id": "t", "replicate": 1, "cost_usd": 1.0, "turns": 2, "verified": True}
        for a in ("on", "off")
    ]
    assert cli._check_result_file(Path("x.json"), runs) == []


def test_non_list_result_is_rejected():
    problems = cli._check_result_file(Path("x.json"), {"runs": []})
    assert any("expected a list" in p for p in problems)


def test_empty_result_file_is_rejected():
    assert cli._check_result_file(Path("x.json"), []) == ["x.json: no runs"]


def test_verify_rejects_a_control_that_expects_its_own_marker(tmp_path):
    """A control asserting marker PRESENCE cannot detect treatment leakage."""
    (tmp_path / "bad.toml").write_text(
        '[subject]\nname="bad"\nrepo="r"\nmechanism="injection"\n'
        '[claim]\nheadline="h"\nsource="s"\naccounting="total"\nvalue_pct=-50.0\n'
        '[[arm]]\nname="on"\ndelivery_marker="M"\n'
        '[[arm]]\nname="off"\ndelivery_marker="M"\nexpects_marker=true\n'
        '[[pairing]]\ntreatment="on"\ncontrol="off"\nlabel="L"\n'
    )
    code = cli.main(["--subjects-dir", str(tmp_path), "--results-dir", str(RESULTS), "verify"])
    assert code == 1


def test_verify_rejects_unstated_accounting_without_a_quote(tmp_path):
    (tmp_path / "bad.toml").write_text(
        '[subject]\nname="bad"\nrepo="r"\nmechanism="compression"\n'
        '[claim]\nheadline="h"\nsource="s"\naccounting="unstated"\nvalue_pct=-50.0\n'
    )
    assert cli.main(["--subjects-dir", str(tmp_path), "--results-dir", str(RESULTS), "verify"]) == 1


def test_subjects_command_runs(capsys):
    assert cli.main(["--subjects-dir", str(SUBJECTS), "subjects"]) == 0
    out = capsys.readouterr().out
    assert "ContextMesh" in out
    assert "VOID" in out  # Headroom's void reason is printed, not hidden


def test_dry_run_prints_the_plan_even_when_the_corpus_is_missing(capsys):
    """A dry run exists to be inspected; an unavailable corpus is part of that."""
    code = cli.main(["--subjects-dir", str(SUBJECTS), "audit", "rtk", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "no claim corpus registered" in out
    assert "nothing executed" in out
    assert "rtk vs off" in out  # the pairing is visible before any spend


def test_real_run_refuses_when_the_corpus_is_missing():
    """Without --dry-run, a missing corpus must stop before anything executes."""
    with pytest.raises(SystemExit, match="no claim corpus registered"):
        cli.main(["--subjects-dir", str(SUBJECTS), "audit", "rtk"])


def test_unknown_subject_exits_with_known_list():
    with pytest.raises(SystemExit, match="unknown subject"):
        cli.main(["--subjects-dir", str(SUBJECTS), "audit", "nonesuch"])


class TestDataRootDiscovery:
    """`pipx install truecost` then `truecost subjects` must not look in site-packages.

    The audit's data lives in the repository, not the wheel. Resolving it from
    the package's own location finds site-packages/subjects, which never exists.
    """

    def test_finds_root_from_within_the_repo(self):
        assert cli.find_data_root(SUBJECTS) == SUBJECTS.parent

    def test_finds_root_from_a_nested_directory(self):
        assert cli.find_data_root(SUBJECTS.parent / "truecost" / "core") == SUBJECTS.parent

    def test_returns_none_outside_any_checkout(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli, "PACKAGE_ROOT", tmp_path / "nowhere")
        assert cli.find_data_root(tmp_path) is None

    def test_missing_root_exits_with_actionable_guidance(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli, "PACKAGE_ROOT", tmp_path / "nowhere")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            cli.main(["subjects"])
        assert "run it from a clone" in str(exc.value)

    def test_explicit_dir_wins_over_discovery(self, tmp_path):
        assert cli._resolve_dir(tmp_path, "subjects") == tmp_path


def test_in_flight_partials_are_not_read_as_results(tmp_path):
    """pathlib's glob matches dotfiles; a partial has the same shape as a result."""
    (tmp_path / ".fake__claim.partial.json").write_text(
        '[{"arm":"on","task_id":"t","replicate":1,"cost_usd":1.0,"turns":2,"verified":true}]'
    )
    (tmp_path / "real__claim__2026-01-01.json").write_text(
        '[{"arm":"on","task_id":"t","replicate":1,"cost_usd":1.0,"turns":2,"verified":true},'
        ' {"arm":"off","task_id":"t","replicate":1,"cost_usd":2.0,"turns":3,"verified":true}]'
    )
    loaded = [p.name for p, _ in cli._load_results(tmp_path)]
    assert loaded == ["real__claim__2026-01-01.json"]
