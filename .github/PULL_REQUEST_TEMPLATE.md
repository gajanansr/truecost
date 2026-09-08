## What this changes

<!-- One or two sentences. -->

## Type

- [ ] New subject (a tool to audit)
- [ ] New or changed corpus
- [ ] Harness / core change
- [ ] Docs
- [ ] Bug fix

---

## If this changes a published number

- [ ] Before and after are in the commit message
- [ ] Raw JSON is committed to `results/`
- [ ] `CHANGELOG.md` records any row withdrawn or corrected, with the reason

## If this adds or changes a subject

- [ ] The claim is **quoted**, not paraphrased, with its source URL
- [ ] `accounting` reflects what the published number actually counted
- [ ] The control **isolates the mechanism** (rationale filled in)
- [ ] Control arms assert marker **absence** (`expects_marker = false`)
- [ ] The corpus has a `control` task on which the mechanism cannot fire
- [ ] Subject libraries are imported lazily and declared in `requires`

## If this adds shell

Manifests and corpora carry `setup`, `teardown`, and `verify` shell that runs on
a reviewer's machine — see [SECURITY.md](../SECURITY.md).

- [ ] No command mutates anything outside the working directory
- [ ] In particular, nothing writes to `~/.claude.json` or `~/.claude/settings.json`

## Checks

- [ ] `truecost verify` passes
- [ ] `pytest -m "not billed"` passes
- [ ] `ruff check .` passes
- [ ] No test added here spends money
