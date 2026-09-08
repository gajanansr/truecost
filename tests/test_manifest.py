"""Manifest loading, and the invariants that keep a row honest."""

from __future__ import annotations

from pathlib import Path

import pytest

from truecost import manifest

SUBJECTS = Path(__file__).resolve().parent.parent / "subjects"


def test_every_shipped_subject_parses():
    subjects = manifest.load_all(SUBJECTS)
    assert set(subjects) == {"contextmesh", "headroom", "portal-shunt", "rtk"}


def test_pairings_only_name_declared_arms():
    for subject in manifest.load_all(SUBJECTS).values():
        for pairing in subject.pairings:
            assert pairing.treatment in subject.arms
            assert pairing.control in subject.arms


def test_control_arms_expect_marker_absence():
    """The direction that catches treatment leaking into a baseline.

    It leaked into 2 of 9 baseline runs before this check existed.
    """
    for subject in manifest.load_all(SUBJECTS).values():
        for pairing in subject.pairings:
            control = subject.arms[pairing.control]
            if control.verifiable:
                assert not control.expects_marker, (
                    f"{subject.name}: control {pairing.control!r} expects its marker present"
                )


def test_unstated_accounting_requires_a_quote():
    for subject in manifest.load_all(SUBJECTS).values():
        if subject.claim.accounting == "unstated":
            assert subject.claim.quoted, f"{subject.name}: unstated accounting with no quote"


def test_delegation_subjects_bill_both_models():
    portal = manifest.load(SUBJECTS / "portal-shunt.toml")
    assert portal.mechanism == "delegation"
    assert portal.bills_second_model


def test_claim_rejects_unknown_accounting():
    with pytest.raises(ValueError, match="unknown accounting"):
        manifest.Claim(headline="x", source="y", accounting="vibes", value_pct=-10.0)


def test_claim_must_state_a_number():
    """A claim with no number cannot be tested, so it cannot be published."""
    with pytest.raises(ValueError, match="states no number"):
        manifest.Claim(headline="faster somehow", source="y", accounting="total")


def test_range_claim_covers_inside_and_rejects_outside():
    claim = manifest.Claim(
        headline="60-90%", source="y", accounting="token-count", range_pct=(-90.0, -60.0)
    )
    assert claim.covers(-75.0)
    assert not claim.covers(-10.9)
    assert not claim.covers(+5.0)
    assert claim.display == "-90..-60%"


def test_point_claim_allows_ten_percent_tolerance():
    claim = manifest.Claim(headline="90%", source="y", accounting="parent-only", value_pct=-90.0)
    assert claim.covers(-85.0)  # within 10% of the claimed value
    assert not claim.covers(-10.9)  # the Portal result


def test_unverifiable_arms_are_reported():
    rtk = manifest.load(SUBJECTS / "rtk.toml")
    assert rtk.unverifiable_arms() == ["off", "rtk"]


def test_duplicate_subject_names_rejected(tmp_path):
    body = (SUBJECTS / "rtk.toml").read_text()
    (tmp_path / "a.toml").write_text(body)
    (tmp_path / "b.toml").write_text(body)
    with pytest.raises(ValueError, match="duplicate subject name"):
        manifest.load_all(tmp_path)


def test_pairing_naming_unknown_arm_rejected(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text(
        '[subject]\nname="bad"\nrepo="r"\nmechanism="other"\n'
        '[claim]\nheadline="h"\nsource="s"\naccounting="total"\nvalue_pct=-1.0\n'
        '[[arm]]\nname="on"\n'
        '[[pairing]]\ntreatment="on"\ncontrol="ghost"\nlabel="L"\n'
    )
    with pytest.raises(ValueError, match="unknown arm 'ghost'"):
        manifest.load(path)
