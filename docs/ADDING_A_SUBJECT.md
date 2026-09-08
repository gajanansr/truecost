# Adding a subject

A subject is a tool under audit. Adding one is a TOML file plus a corpus — not a
code change.

## 1. Write `subjects/<name>.toml`

```toml
[subject]
name = "yourtool"
display = "YourTool"
repo = "https://github.com/you/yourtool"
mechanism = "compression"   # injection | compression | delegation | retrieval | other

[claim]
headline = "70% fewer tokens"
source = "https://github.com/you/yourtool#benchmarks"
accounting = "token-count"  # total | parent-only | token-count | unstated
value_pct = -70.0           # or: range_pct = [-90.0, -60.0]
quoted = "Cuts token usage by 70% on typical sessions."

[[arm]]
name = "yourtool"
requires = ["yourtool"]
delivery_marker = "YourTool"

[[arm]]
name = "off"
env = { YOURTOOL_DISABLE = "1" }
delivery_marker = "YourTool"
expects_marker = false      # a control asserts ABSENCE

[[pairing]]
treatment = "yourtool"
control = "off"
label = "YourTool (compression)"
rationale = "Same binary, inert. Isolates compression from the cost of the hook existing."
```

### `accounting` is the field that matters most

It records **what the published number counted**, and it is often the entire
finding. `parent-only` versus `total` is the difference between Portal's −90%
and the −10.9% that appeared once the delegate was billed.

| Value | Meaning |
|---|---|
| `total` | All models billed |
| `parent-only` | Primary model only; delegated work uncounted |
| `token-count` | Raw token count, cache classes not priced |
| `unstated` | The source does not say — requires a `quoted` excerpt |

**Quote the claim; never paraphrase it.**

### Choosing the control

The control must isolate the mechanism, not merely differ from the treatment.

| Mechanism | Control |
|---|---|
| Hook injection | Same binary, inert |
| Proxy compression | Same proxy, passthrough mode |
| Hook-based rewriting | No hook installed |
| Delegation | No delegation, and the delegate billed on the treatment side |

If the tool has no inert mode, say so in `rationale`. A wrong control is the
most likely way this project publishes something false.

## 2. Add a `claim/` corpus

Reproduce the tool's own published benchmark — its fixture, its question,
verbatim. This is the number its maintainer cannot call unrepresentative.

```python
# truecost/corpus/claim/yourtool.py
from truecost.corpus import Corpus, register
from truecost.core.runner import Task


class YourToolClaim:
    axis = "claim"
    requires = ()  # importable modules this corpus needs

    def build(self, workdir, settings) -> Corpus:
        ...
        return Corpus(
            tasks=tasks, reset_command=reset, root=root, axis="claim", source="https://..."
        )


register("yourtool", YourToolClaim())
```

Then import it from `truecost/corpus/__init__.py:load_builtin`.

**A corpus must include a task with `task_id="control"`** on which the mechanism
cannot fire. `Corpus.__post_init__` refuses to build without one. Without it,
the corpus cannot detect its own bias.

**Import subject libraries lazily**, inside `build`, and declare them in
`requires`. A missing dependency must skip one subject with a clear message, not
break the CLI for everyone.

**Verify the shape of the answer, not its name.** An agent can write a function
called `retry_with_backoff` that retries immediately.

## 3. Check it

```bash
truecost verify                       # integrity gate; CI runs this
truecost subjects                     # confirm the claim renders
truecost audit yourtool --dry-run     # inspect the plan, spend nothing
```

`verify` will reject:

- a pairing naming an arm that does not exist
- a control arm that expects its own delivery marker to be **present**
- a claim with `accounting = "unstated"` and no `quoted` excerpt

## 4. Before it is published

Adding a manifest does not publish a verdict. Measuring does, and measuring
triggers [`DISCLOSURE.md`](DISCLOSURE.md): the maintainer is notified with the
full result and has 14 days to respond before the row goes up.
