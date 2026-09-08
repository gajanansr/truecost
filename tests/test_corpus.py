"""A corpus with no control task cannot detect its own bias."""

from __future__ import annotations

from pathlib import Path

import pytest

from truecost import corpus
from truecost.core.runner import Task


def _task(task_id: str) -> Task:
    return Task(task_id=task_id, prompt="p", verify="true", repo=Path("."))


def test_corpus_requires_a_control_task():
    with pytest.raises(ValueError, match="no 'control' task"):
        corpus.Corpus(tasks=[_task("real")], reset_command="true", root=Path("."), axis="claim")


def test_corpus_accepts_a_task_set_with_a_control():
    built = corpus.Corpus(
        tasks=[_task("real"), _task("control")],
        reset_command="true",
        root=Path("."),
        axis="claim",
    )
    assert len(built.tasks) == 2


def test_axis_must_be_claim_or_neutral():
    with pytest.raises(ValueError, match="axis must be"):
        corpus.Corpus(tasks=[_task("control")], reset_command="true", root=Path("."), axis="vibes")


def test_builtin_corpora_register_themselves():
    corpus.load_builtin()
    assert corpus.get("contextmesh", "claim") is not None


def test_missing_subject_library_skips_one_corpus_not_the_cli():
    corpus.load_builtin()
    ok, why = corpus.available("contextmesh", "claim")
    if not ok:
        assert "contextmesh" in why  # names what is missing, does not raise


def test_unregistered_corpus_reports_rather_than_raises():
    ok, why = corpus.available("nonesuch", "claim")
    assert not ok
    assert "no claim corpus registered" in why
