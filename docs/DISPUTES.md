# Disputes

This project publishes measurements about other people's work. It does that by
publishing the **data and the method** rather than asking anyone to trust a
number — every row ships its raw JSON, its arms, its pairing, and the reasoning
for its control, and anyone can re-run it.

There is no embargo and no notification window. An earlier draft of this policy
had one; it was dropped because it made the project slower without making it
more correct. What makes a measurement defensible is that it can be reproduced,
and reproduction does not require anyone's permission.

## If you maintain a tool measured here

You are the most valuable contributor to this repository. A wrong control is the
likeliest way this project publishes something false, and you know your tool's
controls better than anyone.

It has already happened once. A comparison against Headroom was **void** because
its `--no-optimize` control mode still compacted tool schemas, so both arms
compressed and the delta measured nothing. That is published as `INVALID` with
its reason rather than quietly deleted.

Start with `truecost audit <your-tool> --dry-run`. It prints the arms, the
pairing and the control's rationale without running anything. If the control is
wrong, you will see it there.

## Filing a dispute

Open a [dispute issue](../../issues/new?template=dispute.yml). It gets the same
treatment as any other bug report, and it is prioritised.

**A row that cannot be defended is withdrawn** — not softened, not annotated.
Withdrawn, and recorded in `CHANGELOG.md` with the reason.

Grounds that will get a row pulled or remeasured:

- The control does not isolate what we said it isolates
- The claim was misquoted, or `accounting` was recorded wrongly
- The corpus does not exercise the mechanism the tool is for
- The tool was misconfigured, or a required component was absent
- Delivery was assumed rather than verified
- The arithmetic or statistics are wrong

"The result is unflattering" is not grounds. "The result measures something
other than what you said it measures" always is.

## What this project will not do

- Publish a verdict as a dunk. See [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md):
  criticise measurements, never maintainers. Most overstated claims come from
  measuring the wrong thing, which is easy — this project exists because it is
  easy, and its author's own tool is the first row on the board.
- Publish a number whose delivery could not be verified without labelling it
  `UNVERIFIED`.
- Compare tools that do different things and present it as a ranking.
- Quietly delete a withdrawn row. Withdrawals are published.
- Accept a maintainer's own numbers in place of measuring.

## Responses are published

If you send a response — in an issue, or anywhere else — it is published beside
the row, unedited. Disagreement in the open is worth more than agreement
obtained privately.
