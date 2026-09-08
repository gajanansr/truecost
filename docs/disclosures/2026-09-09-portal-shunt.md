# Disclosure draft — Portal read-shunt

**Status: NOT SENT.** Target and channel unconfirmed — see "Before sending".
Raw data: [`results/shunt-exports.json`](../../results/shunt-exports.json)

---

## The message

Subject: Measured your read-shunt's token savings — would like your review before publishing

Hello,

I maintain [truecost](https://github.com/gajanansr/truecost), a cache-aware audit
of LLM token-savings claims. I've measured the read-shunt and would like your
review before anything is published. Our policy is to notify maintainers first
and publish your response beside the verdict; you have 14 days.

**The claim tested:** "around a whopping 90%", with the eval file describing what
it measures as "Claude context tokens with vs without shunt."

**What I measured.** I rebuilt the architecture for stock Claude Code — Haiku as
the delegate rather than a Portal instance — against the FastAPI package at a
pinned SHA, using your own benchmark question #1 verbatim ("What are all the
exported items and what do they do?") against a file roughly 10× your fixture.
Sonnet parent, 3 replicates per arm, 6/6 runs verified.

```
                                    baseline    shunt      delta
parent model only (your accounting)   0.3127    0.2324     -25.7%
TOTAL, both models billed             0.3127    0.2787     -10.9%
```

The gap between those two lines is the finding. The delegate's tokens do not
appear in the published accounting, so the saving is real only while the
delegate's bill is someone else's.

**Two things I want you to check, because they are where I am most likely wrong.**

First, the delegate was invoked in **1 replicate of 3**. The hook fired in all
three — the agent did try the read — but twice it took the `offset`/`limit`
escape hatch and chunked the file instead. That escape hatch ships with the
tool. Per-replicate:

```
baseline                       0.3382, 0.3032, 0.2968
delegate skipped (chunked)     0.2060, 0.3146
delegate used                  0.3156   =  parent 0.1765 + delegate 0.1391
```

The one run that actually delegated is the one that saved nothing. If that is a
misconfiguration on my side rather than expected routing, tell me and I will
remeasure.

Second, on three other read tasks the hook fired **zero times in six runs**,
because both questions had a symbol to grep for. A shunt can only save on reads
that would have happened. If you consider those tasks out of scope for the
tool, say so and I will scope the published row accordingly.

Turns rose from 10.3 to 13.7 either way.

**What I am not claiming.** The architecture is sound, and it is the first
mechanism I have measured that points the right way — a 6,447-line file that
never enters the prompt prefix is not billed at a multiple for the rest of the
session. My finding is narrower: the ceiling on total spend is the price ratio
between the two models, not 90%, and the published figure counts one side of a
two-sided bill.

**What happens next.** The draft row reads:

```
Portal shunt   claimed -90%   measured -10.9% (total)   n=3   VERIFIED
                              -25.7% (their accounting)
```

Everything needed to reproduce or refute this is in the repository: the arms,
the pairing and its rationale, the corpus, and the raw JSON. If the control is
wrong, or the tool was misconfigured, or the corpus does not exercise what the
shunt is for — that is grounds to withdraw the row, and I would rather hear it
from you than publish a number that measures nothing. That has already happened
once here: a comparison against another tool was voided because its control
mode was silently broken.

Thanks,
Gajanan

---

## Before sending

Three things to confirm. **Do not send until all three are settled.**

1. **The target.** `subjects/portal-shunt.toml` records the repo as
   `spotify/backstage`. Confirm the plugin's actual home and the right contact
   before anything goes out — a disclosure sent to the wrong project is worse
   than none.
2. **The channel.** A GitHub issue is public, which publishes the verdict at the
   moment of notification rather than 14 days later. That may be fine for a
   measurement (it is not a vulnerability), but it is a choice, not a default.
   Private email preserves the window as written.
3. **The quote.** "around a whopping 90%" and the eval-file wording are quoted
   from the original measurement notes. Re-read them at the source before
   sending; `DISCLOSURE.md` requires the claim quoted, not paraphrased.

## Checklist from DISCLOSURE.md

- [x] The exact claim being tested, quoted, with its source
- [x] Arms, environment overlays, pairing, and the rationale for the control
- [x] The corpus, and whether it is `claim` or `neutral` — `claim`, their question verbatim
- [x] Raw results JSON — `results/shunt-exports.json`
- [x] The draft row, including its status
- [ ] Sent, with the date recorded in `DISCLOSURE_LOG.md`
