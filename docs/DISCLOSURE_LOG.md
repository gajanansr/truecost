# Disclosure log

The operational half of [`DISCLOSURE.md`](DISCLOSURE.md). Every subject whose
row involves someone else's tool appears here, with the date it was notified and
the date its window closes.

**This repository is private until the windows below have closed.** Publishing a
verdict before its maintainer has had 14 days would break the policy on the day
it was written, and that policy is the difference between an audit and a dunk.

The self-audit is exempt: ContextMesh's rows are about this project's own tool,
and there is nobody to notify.

| Subject | Row | Notified | Window closes | Response | Status |
|---|---|---|---|---|---|
| ContextMesh | RepoMap, memory | — | — | — | **self-audit, exempt** |
| Portal shunt | read delegation | *not yet sent* | — | — | blocked on notification |
| RTK | output compression | *not yet sent* | — | — | not yet measured |
| Headroom | compression (INVALID) | bug reported upstream | — | *awaiting* | `INVALID`, no number published |

## What to send

Per [`DISCLOSURE.md`](DISCLOSURE.md), a notification carries everything needed
to reproduce or refute the row:

- The claim being tested, quoted, with its source
- Arms, environment overlays, pairing, and the rationale for the control
- The corpus used, and whether it is `claim` or `neutral`
- The raw results JSON
- The draft row, including its status

If any of that cannot be supplied, the row is not ready to publish.

## Headroom is a special case

Its `--no-optimize` control still compacts tool schemas
(`anthropic.py:2782`), so the prior comparison measured nothing and is published
as `INVALID` rather than as a result. The bug was reported upstream rather than
published as a gotcha.

No number about Headroom is published, so no disclosure window applies. If a
valid control appears, it is measured from scratch and disclosed like any other.

## Going public

Before flipping this repository public:

1. Every row involving a third party is either past its window or removed.
2. Responses received are published beside their rows, unedited.
3. A row with no response says so.
4. `truecost verify` passes.
