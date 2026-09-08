# truecost

**A cache-aware audit of LLM token-savings claims.**

The fastest-growing category of AI developer tool ships a headline number that
nobody can reproduce. This measures them, publishes the raw data, and says
plainly when a claim does not survive.

It starts by auditing the tool its own author wrote.

```bash
pipx install truecost
truecost subjects          # what is under audit, and what each claims
truecost audit contextmesh # measure it
truecost report            # the leaderboard
```

---

## Why claimed savings and real savings differ

Three errors recur. Each one has been measured, not asserted.

### 1. Cache amplification

Anything injected into a cached session converts prompt-cache **reads** (billed
at 0.1×) into cache **writes** (1.25× or 2.0×). The billed cost of an injected
block is a multiple of the block itself:

| Experiment | Payload injected | Extra tokens billed | Ratio |
|---|---|---|---|
| `results/position-2026-08-28.json` | 440 | +3,965 | **9.0×** |
| `results/repomap-2026-08-28.json` | ~2,650 | +16,870 | **6.4×** |
| `results/crosstool-2026-08-28.json` | ~470 | +10,916 | **23.2×** |

So a tool can cut token *count* and raise the *bill*. One independent report
found a 38.4% reduction in tool output producing a 6.8% cost **increase**,
because the compaction invalidated cache hits.

An injected block must therefore be worth roughly an order of magnitude more
than its own size. That is a property of the approach, not of any one
implementation.

### 2. One-sided billing

A tool that delegates work to a second model reports the primary model's tokens
and stops there. Rebuilding Portal's read-shunt for stock Claude Code, with
Haiku as the delegate, and billing **both** sides:

```
parent only — the number reported     0.3127 → 0.2324    −25.7%
TOTAL, both models billed             0.3127 → 0.2787    −10.9%
```

Against a claim of "around a whopping 90%". The gap between those two lines is
the whole finding.

It gets sharper. The delegate was actually invoked in **1 replicate of 3** — and
that run is the one that saved nothing:

```
baseline                       0.3127
delegate skipped (chunked)     0.2060, 0.3146
delegate used                  0.3156   ← parent 0.1765 + delegate 0.1391
```

The saving is real only while the delegate's bill is someone else's problem.

### 3. Unverified delivery

No tool in this category checks that its own treatment reached the model.
Delivery verification has rescued three runs here and rejected **nine results
before they became claims** — including an 88% "win" that was entirely cache
ordering, and two comparisons whose control arm was silently receiving the
treatment.

### And the baseline nobody subtracts

Across 241 local sessions, **prompt caching alone accounts for 85.6%** cost
reduction before any tool acts. Every number here is a delta on top of that.
Treat any "90% fewer tokens" claim measured against an uncached baseline with
suspicion — including this project's own withdrawn README, which did exactly
that on the strength of a constant supplying 99.5% of its own headline.

---

## The board

Rows appear here as they are measured. Every row links to the raw JSON it came
from; nothing is published without it.

| Subject | Claimed | Measured | 95% CI | n | Status |
|---|---|---|---|---|---|
| ContextMesh — RepoMap | −90% | **+45.6% / +74.6% / +35.9%** | see results | 3×3 | VERIFIED |
| ContextMesh — memory (curated) | −90% | −28.1% turns, cost n.s. | [−2.79, −0.21] | 6 | VERIFIED |
| ContextMesh — memory (accumulated) | −90% | **+32.0% cost** | [+0.010, +0.101] | 12 | VERIFIED |
| Portal shunt | −90% | **−10.9%** (−25.7% their accounting) | — | 3 | VERIFIED |
| RTK | −60…−90% | *not yet run* | — | — | — |
| Headroom | *unstated* | — | — | — | **INVALID** |

**Headroom is INVALID, not measured.** Its `--no-optimize` control mode still
compacts tool schemas (`anthropic.py:2782`), so both arms compressed and the
comparison measured nothing. Reported upstream. Nothing here should be read as a
measurement of Headroom. The row stays because a void result that quietly
disappears is a retracted claim nobody sees.

---

## What the statuses mean

A row must never be more confident than the evidence under it.

- **`VERIFIED`** — the treatment was confirmed to reach the model, and confirmed
  *absent* on the control.
- **`UNVERIFIED`** — the run happened, but delivery could not be confirmed. A
  tool that compresses inside a proxy may leave no transcript-visible evidence.
  The number is real and weaker, and saying so is what makes this an audit.
- **`INVALID`** — the measurement did not happen. This is a result about the
  run, not about the tool, and it is printed rather than discarded.
- **`no effect`** — a first-class outcome. A 95% interval spanning zero means the
  tool did not measurably change cost on these tasks. That is a finding.

---

## How a subject is measured

**Two axes, because either alone is attackable.**

`claim/` reproduces the tool's own published benchmark — its fixture, its
question, verbatim. This is the number its maintainer cannot call
unrepresentative, because they chose it.

`neutral/` is one versioned task set on pinned real repositories, identical
across subjects, which is the only way to compare tools to each other. It is
the more attackable axis, which is why the `claim/` number is published beside it.

**Each tool is paired against the control that isolates its own mechanism.** Not
a shared baseline. Headroom pairs against a passthrough proxy so the proxy's own
overhead cancels; RTK pairs against no-hook, because without it there is no
interception to disable. A tool compared against the wrong control produces a
number that is confidently wrong.

**Every corpus carries a control task** on which the mechanism cannot fire.
Controls are the only defence against a corpus written to produce a conclusion,
and they have earned it twice by returning a 0.00 turn change.

Full method: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

---

## Before we publish about your tool

We notify maintainers before publishing and print their response beside the
verdict. If a control arm is broken, we would rather find out from you than
publish a number that measures nothing — which is exactly what happened with
Headroom.

Full policy: [`docs/DISCLOSURE.md`](docs/DISCLOSURE.md). Disputing a published
row: open a [dispute issue](../../issues/new?template=dispute.yml); it gets the
same treatment as any other bug, and a row that cannot be defended is withdrawn.

---

## Limitations

Stated up front, because a benchmark that hides these is doing the thing this
project exists to criticise.

- **Small samples.** The clean memory result is n=6; the cross-tool run n=12.
  Real, but not large.
- **One machine, one model, one client.** Nothing here is established as
  vendor-general.
- **In-house neutral tasks.** The control tasks are the only guard against that,
  and the `claim/` axis exists because of it.
- **Not all mechanisms are verifiable.** Proxy-based tools may be permanently
  `UNVERIFIED` here. That is a limit of the method, not a mark against the tool.

More: [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

---

## Contributing

Adding a subject is a TOML file, not a code change — see
[`docs/ADDING_A_SUBJECT.md`](docs/ADDING_A_SUBJECT.md) and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

**Maintainers of audited tools are especially welcome.** You know your tool's
controls better than we do.

## Prior art

The amplification finding is not novel and is not claimed as such.
[TokenPilot](https://arxiv.org/pdf/2606.17016) states it as its opening premise
and reports prefix stabilisation moving cost from \$8.31 to \$4.35 with cache hit
rate 38.7% → 79.2%.
[ProjectDiscovery](https://projectdiscovery.io/blog/how-we-cut-llm-cost-with-prompt-caching)
documented 7% → 84%. It was rediscovered independently here, which is what
validates the harness — and searching the literature first would have saved most
of the effort spent rediscovering it.

## License

MIT
