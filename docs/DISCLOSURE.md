# Disclosure policy

We notify maintainers before publishing a verdict about their tool, and publish
their response beside it.

This is not politeness. The Headroom run was **void** because its `--no-optimize`
control mode still compacted tool schemas, so both arms compressed and the
comparison measured nothing. A maintainer would have caught that in one
sentence. Publishing it first would have put a confident, wrong number in front
of people who trusted it.

## The process

1. **Measure**, following [`METHODOLOGY.md`](METHODOLOGY.md).
2. **Notify** the maintainer with the full result: raw JSON, arms, pairings,
   corpus, and the draft row.
3. **Wait 14 days** for a response.
4. **Publish** the verdict with their response beside it, unedited. If they did
   not respond, the row says so.

A maintainer response never changes a number. It can change the *method* — and
if it does, the number is remeasured and the original is recorded in
`CHANGELOG.md` as withdrawn, with the reason.

## What gets sent

- The exact claim being tested, quoted, with its source
- Arms, environment overlays, and pairing, with the rationale for the control
- The corpus, and whether it is `claim` or `neutral`
- Raw results JSON
- The draft row, including its status

Everything a maintainer needs to reproduce or refute it. If we cannot supply
that, the row is not ready to publish.

## Disputes

Open a [dispute issue](../../issues/new?template=dispute.yml). Disputes get the
same treatment as any other bug report.

**A row that cannot be defended is withdrawn.** Not softened, not annotated —
withdrawn, and recorded in the changelog.

Grounds that will get a row pulled or remeasured:

- The control does not isolate what we said it isolates
- The claim was misquoted, or `accounting` was recorded wrongly
- The corpus does not exercise the mechanism the tool is for
- The tool was misconfigured, or a required component was absent
- Delivery was assumed rather than verified

"The result is unflattering" is not grounds. "The result measures something
other than what you said it measures" always is.

## What we will not do

- Publish a verdict as a dunk. See [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md).
- Publish a number whose delivery we could not verify without labelling it
  `UNVERIFIED`.
- Compare tools that do different things and present it as a ranking.
- Quietly delete a withdrawn row. Withdrawals are published.
- Accept a maintainer's number in place of measuring it.

## If you maintain an audited tool

You are the most valuable contributor here. You know your tool's controls better
than we do, and a wrong control is the single most likely way this project
publishes something false.

Reach us before we reach you, if you like — open a
[new subject issue](../../issues/new?template=new_subject.yml) proposing your own
tool, with the control you would want used.
