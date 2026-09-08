# Limitations

Stated plainly, because a benchmark that buries these is doing the thing this
project exists to criticise.

## Sample sizes are small

The clean memory result is n=6. The cross-tool run is n=12. Real, but not large.
Every replicate is a real, billed agent session, so samples are bought rather
than generated. Where an interval is wide, it is printed wide.

## One machine, one model, one client

Every measurement here is macOS, Claude Code, and the models named in
`core/costs.py`. **Nothing here is established as vendor-general.** A tool that
loses on this setup may win on another, and the reverse.

## Neutral tasks are authored in-house

The `neutral/` corpus was written by this project, which is a real bias risk.
Two guards:

- Every corpus carries a **control task** on which the mechanism cannot fire.
  These have twice returned a 0.00 turn change.
- The **`claim/` axis** reproduces each tool's own published benchmark, chosen
  by its author, not by us.

Neither guard is a proof. A tool that loses on both axes is a stronger finding
than one that loses on `neutral/` alone, and rows say which axis produced them.

## Some mechanisms cannot be verified

A tool that compresses inside a proxy may leave no transcript-visible evidence
that it ran. Those arms are permanently `UNVERIFIED`. **This is a limit of the
method, not a mark against the tool** — and a number from an unverified arm is
weaker evidence, which is why it is labelled rather than footnoted.

## Cost only, not quality

Cost, turns, and task success. A tool that halves cost while producing worse
code would look good here. Task verification greps for the *shape* of a correct
answer rather than its name, which catches the crudest version of this and not
the subtle one.

## Prices change

`core/costs.py` carries per-model rates. A published row is priced at the rates
in effect when it ran. Old rows are not repriced — that would silently rewrite
history — so compare rows within a run, not across distant ones.

## The amplification finding is prior art

It is not claimed as novel. [TokenPilot](https://arxiv.org/pdf/2606.17016)
states it as its opening premise. It was rediscovered independently here, which
validates the harness and nothing more. Searching the literature first would have
saved most of the effort spent rediscovering it — the single most useful lesson
from the work that produced this project.

## Untested ideas that would change the numbers

- **Prefix stabilisation.** The injected block changes every session as memory
  accumulates, so it can never inherit a warm cache. TokenPilot's
  canonicalisation approach was never tested here and is the most likely path to
  making injection affordable.
- **Relevance gating with real embeddings.** The apparent blocker was a 28s
  `sentence-transformers` import. Other tools do the same work in under 50ms, so
  that was an implementation choice, not a constraint.
