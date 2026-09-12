# Contributing

This project publishes measurements about other people's work. That imposes a
higher bar than most repositories, and it applies to maintainers and drive-by
contributors equally.

**One rule underlies everything here: a claim must never be more confident than
the evidence under it.** Most of what follows is that rule applied.

---

## Ways to contribute

| You want to | Do this |
|---|---|
| Propose a tool to audit | [New subject issue](../../issues/new?template=new_subject.yml) |
| Dispute a published row | [Dispute issue](../../issues/new?template=dispute.yml) — maintainers especially welcome |
| Report a bug in the harness | [Bug report](../../issues/new?template=bug_report.yml) |
| Improve the method | Open an issue first. Method changes affect every published row. |

**If you maintain a tool we audit, you are the most valuable contributor here.**
You know your tool's controls better than we do. The Headroom run was voided
because its control mode was silently broken; a maintainer would have caught
that in a sentence.

---

## Adding a subject

Adding a subject is a TOML file, not a code change. If it required writing
Python, the tools we audit would be limited by how much code someone felt like
writing — and the easiest tools to audit would be the ones whose maintainers
were least likely to object.

See [`docs/ADDING_A_SUBJECT.md`](docs/ADDING_A_SUBJECT.md). The short version:

1. `subjects/<name>.toml` — the claim, its source, **what that number measures**,
   the arms, and the pairing.
2. A `claim/` corpus reproducing the tool's own published benchmark.
3. `truecost verify` must pass.

### The claim must be quoted, not paraphrased

`accounting` is the field that matters most. `parent-only` versus `total` is the
difference between Portal's −90% and the −10.9% that appeared once the delegate
was billed. If the source does not say, use `unstated` and quote it, so readers
can judge for themselves.

Never restate a claim in your own words. Quote it.

---

## Rules for anything that produces a number

These are not style preferences. Each one exists because its absence produced a
wrong result that was nearly published.

**Every published number ships its raw JSON in `results/`.** A row without its
data is an assertion. CI enforces this.

**Delivery is verified, or the row says `UNVERIFIED`.** Never silently trusted.
Publishing a comparison that quietly assumes a competitor's tool was active is
the same error this project exists to prevent, pointed at someone else.

**Control arms assert marker *absence*.** This is how treatment leaking into a
baseline gets caught — it leaked into 2 of 9 baseline runs before this check
existed. `truecost verify` rejects a control that expects its own marker present.

**Prove delivery by effect, not by substring, where you can.** A block reason
naming a script lands in the transcript whether or not the agent ever ran it.
That exact false pass invalidated two runs. Portal's shunt is verified by the
delegate's own bill being non-zero.

**Discard a warm-up per task and rotate arm order.** Cold-versus-warm cache
ordering was measured at **8×** on a trivial task — larger than any effect
anyone is looking for.

**Pair replicates by task. Report a 95% interval. Say "no significant
difference" when that is the answer.** A single run can never produce a
headline.

**Pair each tool against the control that isolates its own mechanism.** Not a
shared baseline.

**Every corpus needs a control task** on which the mechanism cannot fire. A
corpus with no such task cannot detect its own bias.

**Bill every model.** If a tool moves work to a second model, the second
model's tokens are part of the bill.

---

## Reporting a negative result about us

Findings against this project's own tooling are welcome and get published the
same as any other. The first row on the board is the author's own tool, failing.
That is deliberate: an audit whose author has never published a loss is not an
audit.

---

## Development

```bash
git clone https://github.com/gajanansr/truecost
cd truecost
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"

.venv/bin/pytest              # unit tests — no API spend
.venv/bin/truecost verify     # integrity gate, same as CI
.venv/bin/ruff check .
```

**Tests must not spend money.** Anything requiring real sessions is opt-in
behind a marker and never runs in CI. Use `truecost audit --dry-run` to inspect
a plan without executing it.

The core has **no runtime dependencies**. Pulling in numpy or scipy to compute a
paired mean would make the harness harder to audit than the tools it audits.
Keep it that way.

---

## Repository rules

Three rulesets are enforced on this repository. Each exists for a reason
specific to what this project publishes.

**`main` history is evidence** — force pushes and branch deletion are blocked,
with **no bypass for anyone, including the owner**. Published rows cite the
commits that produced them. A rewritten history means a citation that no longer
resolves, which is the same failure as deleting a result you did not like.

**`main` requires green CI** — pull requests must pass `lint`, `integrity`, and
the full six-way test matrix, and must resolve review threads. `integrity` is
the job that runs `truecost verify`, so a change that breaks the reproducibility
guarantee cannot merge. CODEOWNERS review is required, which routes anything
touching `core/`, `METHODOLOGY.md`, `DISPUTES.md`, `subjects/`, `corpus/`, or
`results/` to an explicit review — those are the paths that can change a
published number.

**Release tags are immutable** — `v*` tags cannot be deleted or moved. The
release workflow publishes to PyPI on tag push via trusted publishing, so a
moved tag would republish different code under a version someone has already
installed.

## Commit messages

Say what was measured and what it showed. `bench: a read-shunt's saving is half
accounting, and vanishes when it's used` is a good one. `fix stuff` is not.

For anything that changes a number, put the before and after in the body.

## Code of conduct

[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Note the addition specific to this
project: **criticise measurements, never maintainers.** A tool that does not do
what it claims is a finding about the tool.
