# Roadmap

Two phases. Phase 1 must be complete and published before Phase 2 begins:
auditing other people's tools with a rig that has never been run end to end
would be exactly the failure this project exists to criticise.

## Phase 1 — the rig, proved on ourselves

**Status: in progress.**

- [x] Measurement core extracted and made subject-agnostic
- [x] Subject manifests (`subjects/*.toml`) with claim and accounting
- [x] `claim/` corpus protocol, with a mandatory control task
- [x] Verdict layer: `VERIFIED` / `UNVERIFIED` / `INVALID`, `no effect`
- [x] `truecost verify` integrity gate, enforced in CI
- [x] ContextMesh `claim/` corpus, ported unchanged
- [ ] `truecost audit` wired to `run_matrix` end to end
- [ ] `truecost report` rendering rows from `results/`
- [ ] The ContextMesh self-audit re-run under the new CLI and published

The deliverable is a working auditor and one honest verdict against its own
author's tool.

## Phase 2 — the leaderboard

Each subject lands independently, under [`DISCLOSURE.md`](DISCLOSURE.md).
Notification dates and windows are tracked in
[`DISCLOSURE_LOG.md`](DISCLOSURE_LOG.md); the repository stays private until
every third-party window has closed.

- [ ] `neutral/` corpus on pinned real repositories
- [ ] RTK — manifest written; largest subject on the board
- [ ] Portal shunt — already measured, needs re-running under the new CLI
- [ ] Headroom — blocked on a valid control; currently `INVALID`

## Not planned

- A hosted site. The README is the leaderboard.
- Auditing claims about latency or quality rather than cost.
- Non-Claude-Code clients. Stated as a limitation rather than fixed.
- Accepting a maintainer's own numbers in place of measuring.
