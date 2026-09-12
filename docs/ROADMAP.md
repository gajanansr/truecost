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
- [x] `truecost audit` wired to `run_matrix` end to end, with the runner
      injectable so the pipeline is tested without spending anything
- [x] `truecost report` rendering rows from `results/`
- [ ] The ContextMesh self-audit re-run under the new CLI and published
      — the only remaining item, and the one that costs real money

The deliverable is a working auditor and one honest verdict against its own
author's tool.

## Phase 2 — the leaderboard

Each subject lands independently. Every row ships its raw data so anyone can
reproduce it; disputes are handled in [`DISPUTES.md`](DISPUTES.md).

- [ ] `neutral/` corpus on pinned real repositories
- [ ] RTK — manifest written; largest subject on the board
- [ ] Portal shunt — already measured, needs re-running under the new CLI
- [ ] Headroom — blocked on a valid control; currently `INVALID`

## Not planned

- A hosted site. The README is the leaderboard.
- Auditing claims about latency or quality rather than cost.
- Non-Claude-Code clients. Stated as a limitation rather than fixed.
- Accepting a maintainer's own numbers in place of measuring.
