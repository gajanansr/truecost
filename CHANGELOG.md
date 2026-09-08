# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Because this project publishes measurements, one extra rule applies: **a
published row that is later withdrawn or corrected is recorded here, with the
reason.** A number that quietly changes is worse than one that was never
published.

## [Unreleased]

### Added
- Measurement core extracted from ContextMesh's benchmark harness: cache-aware
  billing (`core/costs.py`), transcript parsing, paired statistics, delivery
  verification, and the arm abstraction.
- Subject manifests: a tool under audit is declared in `subjects/*.toml`, with
  its claim, the claim's source, and what that number measures.
- `truecost verify`, an integrity gate run in CI: rejects a control arm that
  expects its own delivery marker, and a claim with unstated accounting and no
  supporting quote.
- Two-axis corpus protocol (`claim/` and `neutral/`), requiring a control task.
- Verdict layer distinguishing `VERIFIED`, `UNVERIFIED`, and `INVALID`, with
  `no effect` as a first-class outcome.
- Subject manifests for ContextMesh, RTK, Portal's read-shunt, and Headroom.

### Notes on inherited results
- Results carried over from ContextMesh's `bench/` are published unchanged in
  `results/`, including the ones unfavourable to ContextMesh itself.
- The Headroom comparison is published as **INVALID** and is not a measurement
  of Headroom. Its `--no-optimize` control still compacts tool schemas
  (`anthropic.py:2782`), so both arms compressed. Reported upstream.

[Unreleased]: https://github.com/gajananrathod/truecost/compare/main...HEAD
