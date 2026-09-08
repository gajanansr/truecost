# Security Policy

## Reporting a vulnerability

Report privately through
[GitHub Security Advisories](../../security/advisories/new). Please do not open
a public issue for a vulnerability.

Expect an acknowledgement within 7 days.

## Scope

This project runs a coding agent, executes shell commands from task definitions,
and starts local proxies on behalf of the tools it audits. The parts most worth
scrutiny:

- **Corpus `setup` / `verify` shell.** Task definitions carry shell commands that
  run on the host. A malicious corpus in a pull request is arbitrary code
  execution against a reviewer's machine.
- **Arm `setup` / `teardown` and `command_prefix`.** Same exposure, from a
  subject manifest.
- **Generated `--settings` files.** Audits write settings passed to the agent.
  These must never mutate the user's global configuration.

### What audits will not do

An audit must not modify anything outside its own working directory. In
particular it never rewrites `~/.claude.json` or `~/.claude/settings.json`. This
is why Headroom is driven through `headroom proxy` + `ANTHROPIC_BASE_URL` rather
than `headroom wrap`, which rewrites user-scope configuration.

If you find an audit path that mutates user configuration, that is a security
bug, not a papercut.

## Reviewing pull requests

Adding a subject is a TOML file, and TOML files here carry shell. Review
`setup`, `teardown`, `verify`, and `command_prefix` in any contributed manifest
or corpus with the same care as executable code, because that is what they are.

## Credentials

Audits run against your own authenticated agent session. Never commit API keys,
transcripts, or `~/.claude` contents. Published results contain token counts and
costs — never prompt or completion text.
