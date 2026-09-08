# Methodology

Every rule here exists because its absence produced a wrong result that was
nearly published. Nine results were rejected by these checks before they could
become claims.

## 1. Bill by cache class, never by token count

Four token classes bill at different rates against the same input price:

| Class | Multiplier |
|---|---|
| Uncached input | 1.0× |
| Cache read | **0.1×** |
| Cache write, 5-minute TTL | 1.25× |
| Cache write, 1-hour TTL | **2.0×** |

Claude Code uses the 1-hour TTL. Collapsing the two write classes into one
understates write cost by 60% — precisely the error that makes naive "tokens
saved" claims meaningless.

`input_tokens` in the usage record counts only uncached tokens, so the four
classes are additive with no double counting. The model is validated to six
decimal places against the CLI's own cost accounting on every run.

**Consequence:** a 70% reduction in token *count* and a 70% reduction in *cost*
are different claims. A tool can achieve the first while worsening the second.

## 2. Amplification: what injection actually costs

Injecting anything into a cached session converts cache reads into cache writes
for everything after the injection point. Measured here:

| Payload | Extra billed | Ratio |
|---|---|---|
| 440 | +3,965 | 9.0× |
| ~2,650 | +16,870 | 6.4× |
| ~470 | +10,916 | 23.2× |

An injected block must be worth roughly an order of magnitude more than its own
size. Position within the prompt is not the lever; amplification is.

## 3. Verify delivery, or say you could not

A comparison between "tool on" and "tool off" is meaningless if the tool never
ran. This check has rescued three runs and caught treatment leaking into a
baseline in 2 of 9 runs.

- Treatment arms declare a `delivery_marker`. Absent marker → `INVALID`.
- **Control arms assert the marker is *absent*.** This is the direction that
  catches leakage, and `truecost verify` rejects a control that expects presence.
- An arm with no observable effect is `UNVERIFIED`, never silently trusted.

**Prove delivery by effect where possible.** A block reason naming a script
lands in the transcript whether or not the agent ever ran it — that false pass
invalidated two runs. Portal's shunt is verified by the delegate's bill being
non-zero, which cannot be faked by an agent that routed around it.

## 4. Bill every model

A tool that delegates work to a second model has not saved anything until the
second model's bill is counted. Delegation subjects are billed on both sides by
default, and the report prints the tool's own accounting beside the total.

The ceiling on total spend for a delegation mechanism is the price ratio between
the two models — not the reduction in the primary model's context.

## 5. Pair against the control that isolates the mechanism

Not a shared baseline. Getting this wrong produces a number that is confidently
wrong.

| Mechanism | Control | Why |
|---|---|---|
| Hook injection | Same binary, inert | Isolates the injection, not the hook's existence |
| Proxy compression | Same proxy, passthrough | Cancels the proxy's own latency and overhead |
| Hook-based rewriting | No hook | Nothing to pass through; absence is the only control |

Comparing a proxy tool against "no proxy at all" confounds compression with the
cost of running a proxy.

## 6. Control for cache ordering

Cold-versus-warm cache ordering was measured at **8× on a trivial task** —
larger than any effect anyone is looking for. Therefore:

- One warm-up per task, discarded.
- Arm order rotated across replicates.

An A/B that runs A first every time measures the ordering.

## 7. Statistics

- Replicates paired by task; the unit of analysis is the within-task delta.
- 95% intervals from a t-distribution.
- **"No significant difference" is printed explicitly**, not converted into a
  small effect.
- Runs where either arm errored are dropped from the pair, not filled in.
- A run that gave up early looks cheap; comparing it to one that finished
  measures the giving up, so unverified runs are excluded by default.

A single run can never produce a headline.

## 8. Every corpus carries a control task

A task on which the mechanism cannot fire. Controls are the only defence against
a corpus written to produce a conclusion. They have twice returned a 0.00 turn
change, which is what a rigged corpus cannot do. `Corpus.__post_init__` refuses
to build without one.

## 9. Publish the raw data

Every row ships the JSON it came from. CI enforces it. A row without data is an
assertion.

## What this method cannot do

- Establish vendor-generality. One machine, one model, one client.
- Verify a tool whose mechanism leaves no observable trace. Those stay
  `UNVERIFIED` permanently — a limit of the method, not a mark against the tool.
- Measure quality. Only cost, turns, and task success.
- Produce large samples cheaply. Every replicate is a real, billed session.
