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
- `truecost audit` wired end to end: builds the corpus, registers the subject's
  arms, runs the preflight probe, executes the matrix, checks delivery per run,
  and writes raw data to `results/<subject>__<axis>__<date>.json`. The runner is
  injectable, so the pipeline that produces published numbers is itself tested
  without spending anything.
- Delivery is persisted per run. Transcripts do not survive the machine that
  produced them, so without this every republished row would silently downgrade
  to `UNVERIFIED`.
- `truecost report` renders rows from saved audits. Inherited pre-CLI results
  are republished as raw data and explicitly not re-rendered as verdicts.

### Corrected
- **A published figure was wrong.** The amplification table claimed +16,870 extra
  billed tokens for the RepoMap injection. No committed result file reproduces
  it — the personalised run gives +15,678 and the alphabetical run +17,473. The
  figure was inherited from ContextMesh's README and could not be regenerated
  from the data shipped beside it. The table now carries only figures that
  `scripts/amplification.py` reproduces from `results/`, and names the file
  behind each one. The conclusion is unchanged; one number was not checkable and
  is now.

### Fixed
- `pipx install truecost && truecost subjects` looked for `site-packages/subjects`
  and failed. The audit's data lives in the repository, not the wheel, so the
  data root is now discovered from the working directory. Found by installing
  the built wheel and running it outside a checkout.
- `release.yml` ran only on `v*` tags, so the first execution of any change to it
  was the run that published to PyPI. Build, `twine check`, and the artifact
  round-trip now run on every push and pull request; only `publish` is tagged.

### Notes on inherited results
- Results carried over from ContextMesh's `bench/` are published unchanged in
  `results/`, including the ones unfavourable to ContextMesh itself.
- The Headroom comparison is published as **INVALID** and is not a measurement
  of Headroom. Its `--no-optimize` control still compacts tool schemas
  (`anthropic.py:2782`), so both arms compressed. Reported upstream.

[Unreleased]: https://github.com/gajanansr/truecost/compare/main...HEAD
